import json
import re
from datetime import datetime
from typing import Any, Optional

from lxml import html
from pydantic import BaseModel

from pipeline.model.raw_record import RawRecord
from pipeline.model.source_normalized import SalaryStatus, SourceNormalized, WorkMode
from pipeline.tools.date_parser import parse_vietnamese_date


class _SalaryInfo(BaseModel):
    status: SalaryStatus
    min: Optional[float] = None
    max: Optional[float] = None


def _parse_salary(text: str) -> _SalaryInfo:
    cleaned = text.strip()
    if not cleaned or cleaned == "Thoả thuận" or cleaned == "Thỏa thuận":
        return _SalaryInfo(status=SalaryStatus.NEGOTIABLE)
    match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*(?:triệu|VND|USD)",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        return _SalaryInfo(
            status=SalaryStatus.DISCLOSED,
            min=float(match.group(1).replace(",", ".")),
            max=float(match.group(2).replace(",", ".")),
        )
    match = re.search(r"Tới\s+(\d+(?:[.,]\d+)?)\s*(?:triệu|VND|USD)", cleaned, re.IGNORECASE)
    if match:
        return _SalaryInfo(
            status=SalaryStatus.DISCLOSED,
            max=float(match.group(1).replace(",", ".")),
        )
    return _SalaryInfo(status=SalaryStatus.NOT_PROVIDED)


def _map_work_mode(text: str) -> Optional[WorkMode]:
    lowered = text.strip().lower()
    if "remote" in lowered and "onsite" not in lowered and "văn phòng" not in lowered:
        return WorkMode.REMOTE
    if "hybrid" in lowered:
        return WorkMode.HYBRID
    if "onsite" in lowered or "văn phòng" in lowered or lowered == "at office":
        return WorkMode.ONSITE
    return None


def _extract_skill_groups(container) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "skills": [],
        "job_expertise": [],
        "job_domain": [],
    }
    current_label: Optional[str] = None
    for node in container.iter():
        cls = node.get("class") or ""
        text = (node.text or "").strip()
        if node.tag == "div" and "w-xl-fixed-100" in cls and text in ("Skills:", "Job Expertise:", "Job Domain:"):
            if text == "Skills:":
                current_label = "skills"
            elif text == "Job Expertise:":
                current_label = "job_expertise"
            elif text == "Job Domain:":
                current_label = "job_domain"
        elif "itag" in cls:
            if current_label:
                groups[current_label].append(node.text_content().strip())
    return groups


def _extract_json_data(tree):
    json_data_str = tree.xpath('//@data-jobs--save-data-layer-value')
    if not json_data_str:
        return {}
    try:
        return json.loads(json_data_str[0])
    except (json.JSONDecodeError, IndexError):
        return {}


def _parse_detail(raw: RawRecord) -> dict[str, Any]:
    tree = html.fromstring(raw.raw_html_detail)
    json_data = _extract_json_data(tree)

    title = json_data.get("job_title", "")
    company_name = json_data.get("job_by_company", "")
    job_by_city = json_data.get("job_by_city", "")
    locations = [loc.strip() for loc in job_by_city.split(",") if loc.strip()]

    if not title:
        title_nodes = tree.xpath('//h1')
        if title_nodes:
            title = title_nodes[0].xpath("string(.)").strip()

    if not company_name:
        company_nodes = tree.xpath(
            '//a[contains(@href, "/companies/")]//span[contains(@class, "text-rich-grey")]'
        )
        if company_nodes:
            company_name = _extract_text(company_nodes[0])

    work_mode = None
    posted_date_raw = ""
    container = tree.xpath('//div[contains(@class, "job-show-info")]')
    if container:
        spans = container[0].xpath(
            './/span[contains(@class, "normal-text") and contains(@class, "text-rich-grey")]'
        )
        for s in spans:
            text = s.text_content().strip()
            if text in ("At office", "Hybrid", "Remote"):
                work_mode = _map_work_mode(text)
            elif text.startswith("Posted"):
                posted_date_raw = re.sub(r"Posted\s*", "", text).strip()

    # [FIX] json_data trên thực tế LUÔN rỗng (data-jobs--save-data-layer-value không
    # tồn tại trong HTML thật, đã verify — xem SOURCE_REGISTRY["itviec"]["has_json_data_layer"]).
    # Trước đây locations không có fallback nào ngoài json_data -> luôn ra [] mỗi khi
    # _parse_detail() thực sự chạy, dù raw_html_detail có đầy đủ nội dung. Bổ sung fallback
    # đọc trực tiếp từ .job-show-info (cấu trúc thật: span "City, Ho Chi Minh" / "City, Ha Noi",
    # cùng khối chứa work_mode/posted_date ở trên nên tận dụng luôn container đã có).
    if not locations and container:
        city_spans = container[0].xpath('.//span[starts-with(normalize-space(.), "City,")]')
        for span in city_spans:
            text = span.text_content().strip()
            loc = re.sub(r"^City,\s*", "", text).strip()
            if loc and loc not in locations:
                locations.append(loc)

    salary_status = SalaryStatus.NOT_PROVIDED
    salary_min = None
    salary_max = None
    if json_data:
        salary_range = json_data.get("salary_range", "")
        if salary_range:
            salary_info = _parse_salary(salary_range)
            salary_status = salary_info.status
            salary_min = salary_info.min
            salary_max = salary_info.max
        else:
            salary_status = SalaryStatus.AUTH_GATED

    # [FIX] XPath cũ: //h2[contains(text(), "Job description")] chỉ khớp text node
    # TRỰC TIẾP của <h2> — nếu site bọc chữ trong <span> (rất phổ biến,
    # <h2><span>Job description</span></h2>), biểu thức này KHÔNG BAO GIỜ khớp, gây
    # description_raw="" bất kể trang có nội dung hay không, bất kể có login hay không.
    # Dùng contains(string(.), ...) để so trên toàn bộ text (kể cả text cháu), khớp
    # đúng ý định gốc ("h2 nào có chữ Job description ở bất kỳ đâu trong nó").
    description_raw = ""
    h2_nodes = tree.xpath('//h2[contains(string(.), "Job description")]')
    if h2_nodes:
        parts = []
        for sibling in h2_nodes[0].itersiblings():
            text = sibling.text_content().strip()
            if text:
                parts.append(text)
        description_raw = " ".join(parts)

    skill_groups = _extract_skill_groups(container[0]) if container else {
        "skills": [],
        "job_expertise": [],
        "job_domain": [],
    }

    json_skills: list[str] = []
    raw_skills = json_data.get("job_required_skill", "") if json_data else ""
    if raw_skills:
        json_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]

    # [FIX] Nếu json_data rỗng (case thực tế luôn xảy ra), json_skills luôn [] dù
    # trang detail có sẵn skill tag (Skills:/Job Expertise:/Job Domain: đọc được qua
    # _extract_skill_groups() ở trên). Fallback về skill_groups["skills"] khi cần,
    # để skills_raw không bị rỗng oan uổng chỉ vì thiếu JSON data layer.
    if not json_skills:
        json_skills = skill_groups["skills"]

    source_extra: dict[str, Any] = {
        "skills_raw": json_skills,
        "job_expertise_raw": skill_groups["job_expertise"],
        "job_domain_raw": skill_groups["job_domain"],
    }

    salary_text = ""
    salary_nodes = tree.xpath(
        '//span[contains(@class, "sign-in-view-salary") or contains(text(), "Sign in to view salary")]'
    )
    if not salary_nodes:
        salary_nodes = tree.xpath('//a[contains(@class, "sign-in-view-salary")]')
    if salary_nodes:
        salary_text = _extract_text(salary_nodes[0])
    if salary_status == SalaryStatus.NOT_PROVIDED and "sign in" in salary_text.lower():
        salary_status = SalaryStatus.AUTH_GATED

    return {
        "title": title,
        "company_name": company_name,
        "locations": locations,
        "description_raw": description_raw,
        "work_mode": work_mode,
        "posted_date_raw": posted_date_raw,
        "salary_status": salary_status,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "source_extra": source_extra,
    }


def _parse_listing(raw: RawRecord) -> dict[str, Any]:
    title = raw.title_listing or ""
    company_name = ""
    work_mode = None
    posted_date_raw = ""
    salary_status = SalaryStatus.NOT_PROVIDED
    locations: list[str] = []
    skills_required: list[str] = []

    if raw.raw_html_listing:
        tree = html.fromstring(raw.raw_html_listing)

        posted_nodes = tree.xpath('//span[contains(text(), "Posted")]')
        if posted_nodes:
            text = posted_nodes[0].text_content().strip()
            match = re.search(r"Posted\s*(.+)", text)
            if match:
                posted_date_raw = match.group(1).strip()

        work_mode_nodes = tree.xpath(
            '//*[contains(text(), "At office") or contains(text(), "Hybrid") or contains(text(), "Remote")]'
        )
        for wm_node in work_mode_nodes:
            wm_text = wm_node.text_content().strip()
            if wm_text in ("At office", "Hybrid", "Remote"):
                work_mode = _map_work_mode(wm_text)
                break

        itags = tree.xpath('//a[contains(@class, "itag")]')
        for it in itags:
            skills_required.append(it.text_content().strip())

        company_nodes = tree.xpath('//a[contains(@href, "/companies/")]')
        for cn in company_nodes:
            text = cn.text_content().strip()
            if text and text not in ("",):
                company_name = text
                break

        sign_in_nodes = tree.xpath(
            '//*[contains(text(), "Sign in to view salary")]'
        )
        if sign_in_nodes:
            salary_status = SalaryStatus.AUTH_GATED

        loc_nodes = tree.xpath('//*[contains(@class, "text-rich-grey")]')
        seen_locs: set[str] = set()
        for ln in loc_nodes:
            text = ln.text_content().strip()
            if text and ("-" in text or "Ha Noi" in text or "Hà Nội" in text or "Ho Chi Minh" in text or "Hồ Chí Minh" in text or "TP.HCM" in text or "Da Nang" in text or "Đà Nẵng" in text):
                for loc in text.split(","):
                    loc = loc.strip()
                    if loc and loc not in seen_locs:
                        seen_locs.add(loc)
                        locations.append(loc)

    return {
        "title": title,
        "company_name": company_name,
        "locations": locations,
        "description_raw": "",
        "work_mode": work_mode,
        "salary_status": salary_status,
        "salary_min": None,
        "salary_max": None,
        "posted_date_raw": posted_date_raw,
        "source_extra": {
            "skills_raw": skills_required,
            "job_expertise_raw": [],
            "job_domain_raw": [],
        },
    }


def _extract_text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, list):
        if not node:
            return ""
        node = node[0]
    return " ".join(node.itertext()).strip()


def parse(raw: RawRecord) -> SourceNormalized:
    # [GHI CHÚ CHẨN ĐOÁN] Nếu batch trước đó toàn bộ job ra description_raw="",
    # salary_status="auth_gated", locations vẫn có giá trị thật -> dấu hiệu raw.detail_crawled
    # đang là False (rẽ vào _parse_listing() dù crawler đã crawl detail xong) -> kiểm tra
    # merge.py / jobs_meta_detail_status.jsonl trước, KHÔNG phải bug trong file này.
    if raw.detail_crawled and raw.raw_html_detail:
        data = _parse_detail(raw)
    else:
        data = _parse_listing(raw)

    posted_date_raw = data.get("posted_date_raw", "")
    batch_date = datetime.strptime(raw.batch_date, "%Y-%m-%d").date()
    posted_date_parsed = parse_vietnamese_date(posted_date_raw, batch_date)

    if posted_date_parsed:
        data["source_extra"]["posted_date_parsed"] = posted_date_parsed.isoformat()

    return SourceNormalized(
        job_id=raw.job_id,
        source=raw.source,
        url=raw.url,
        title=data["title"],
        company_name=data["company_name"],
        locations=data["locations"],
        description_raw=data["description_raw"],
        posted_date_raw=posted_date_raw,
        salary_status=data["salary_status"],
        salary_min=data["salary_min"],
        salary_max=data["salary_max"],
        work_mode=data["work_mode"],
        listing_position=raw.listing_position,
        source_extra=data["source_extra"],
    )