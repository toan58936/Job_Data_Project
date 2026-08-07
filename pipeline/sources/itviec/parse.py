import json
import re
from datetime import datetime
from typing import Any, Optional

from lxml import html

from pipeline.model.raw_record import RawRecord
from pipeline.model.source_normalized import SalaryStatus, SourceNormalized, WorkMode
from pipeline.tools.date_parser import parse_vietnamese_date


def _map_work_mode(text: str) -> Optional[WorkMode]:
    lowered = text.strip().lower()
    if "remote" in lowered and "onsite" not in lowered and "văn phòng" not in lowered:
        return WorkMode.REMOTE
    if "hybrid" in lowered:
        return WorkMode.HYBRID
    if "onsite" in lowered or "văn phòng" in lowered or lowered == "at office":
        return WorkMode.ONSITE
    return None


def _extract_json_data(tree):
    json_data_str = tree.xpath('//@data-jobs--save-data-layer-value')
    if not json_data_str:
        return {}
    try:
        return json.loads(json_data_str[0])
    except (json.JSONDecodeError, IndexError):
        return {}




def _split_description_sections(text: str) -> dict[str, str]:
    """Tach description ITviec thanh cac sections."""
    result = {
        "description_raw": "",
        "requirements_raw": "",
        "benefits_raw": "",
    }
    if not text:
        return result

    normalized = " ".join(text.split())

    benefits_pos = -1
    for marker in [
        "Why You'll Love Working Here",
        "Top 3 Reasons To Join Us",
        "Quyền lợi",
    ]:
        pos = normalized.find(marker)
        if pos != -1:
            if benefits_pos == -1 or pos > benefits_pos:
                benefits_pos = pos

    req_pos = -1
    for marker in [
        "Your Skills and Experience",
        "Requirements",
        "Yêu cầu bắt buộc",
        "Yêu cầu",
        "Ưu tiên các ứng viên",
    ]:
        pos = normalized.find(marker)
        if pos != -1:
            if req_pos == -1 or pos < req_pos:
                req_pos = pos

    if benefits_pos != -1:
        result["benefits_raw"] = normalized[benefits_pos:].strip()
        normalized = normalized[:benefits_pos].strip()

    if req_pos != -1:
        result["requirements_raw"] = normalized[req_pos:].strip()
        normalized = normalized[:req_pos].strip()

    result["description_raw"] = normalized.strip()
    return result


def _extract_experience(text: str) -> str:
    """Trich xuat kinh nghiem (nam) tu text."""
    if not text:
        return ""
    matches = re.findall(r'(\d+)\+?\s*(?:năm|years?)', text, re.IGNORECASE)
    if matches:
        return ", ".join(f"{m}+ năm" for m in matches)
    return ""


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

    if not locations and container:
        city_spans = container[0].xpath('.//span[starts-with(normalize-space(.), "City,")]')
        for span in city_spans:
            text = span.text_content().strip()
            loc = re.sub(r"^City,\s*", "", text).strip()
            if loc and loc not in locations:
                locations.append(loc)

    # --- Xử lý lương (Không bóc số ở đây, chỉ gom text thô cho Bước 4) ---
    salary_status = SalaryStatus.NOT_PROVIDED
    salary_text = ""

    if json_data:
        salary_text = (json_data.get("salary_range") or "").strip()

    if not salary_text:
        salary_nodes = []
        if container:
            salary_nodes = container[0].xpath(
                './/span[contains(@class, "sign-in-view-salary") or contains(text(), "Sign in to view salary")] | .//a[contains(@class, "sign-in-view-salary")]'
            )

        if not salary_nodes:
            salary_nodes = tree.xpath(
                '//span[contains(@class, "sign-in-view-salary") or contains(text(), "Sign in to view salary")] | //a[contains(@class, "sign-in-view-salary")]'
            )

        if salary_nodes:
            salary_text = _extract_text(salary_nodes[0])

        if not salary_text and container:
            salary_range_nodes = container[0].xpath('.//div[contains(@class, "salary")]//span | .//span[contains(@class, "salary")]')
            if salary_range_nodes:
                salary_text = _extract_text(salary_range_nodes[0])

    cleaned_salary = salary_text.strip().lower()
    if not cleaned_salary:
        salary_status = SalaryStatus.NOT_PROVIDED
    elif "sign in" in cleaned_salary or "đăng nhập" in cleaned_salary:
        salary_status = SalaryStatus.AUTH_GATED
    elif not re.search(r"\d", cleaned_salary):
        salary_status = SalaryStatus.NEGOTIABLE
    else:
        salary_status = SalaryStatus.DISCLOSED

    # Extract sections from paragraph divs (mỗi section là <div class="paragraph"> chứa <h2>)
    description_raw = ""
    requirements_raw = ""
    benefits_raw = ""

    section_divs = tree.xpath('//div[contains(@class, "paragraph")]')
    for div in section_divs:
        h2_nodes = div.xpath('.//h2')
        if not h2_nodes:
            continue
        h2_text = h2_nodes[0].text_content().strip()
        div_text = div.text_content().strip()

        if "Job description" in h2_text:
            description_raw = div_text
        elif "Your skills and experience" in h2_text or "Requirements" in h2_text:
            requirements_raw = div_text
        elif "Why you'll love working here" in h2_text or "Top 3 reasons" in h2_text:
            benefits_raw = div_text

    # Fallback: dùng JSON-LD description nếu HTML không có
    if not description_raw and json_data:
        description_raw = json_data.get("description", "")

    # Fallback benefits: nếu không có "Why you'll love", lấy "Top 3 reasons" làm benefits
    if not benefits_raw:
        for div in section_divs:
            h2_nodes = div.xpath('.//h2')
            if h2_nodes and "Top 3 reasons" in h2_nodes[0].text_content().strip():
                benefits_raw = div.text_content().strip()
                break

    # Extract experience from requirements or description
    experience_raw = _extract_experience(requirements_raw or description_raw)

    # Extract deadline from JSON-LD validThrough
    deadline_raw = (json_data.get("validThrough") or "").strip() if json_data else ""

    source_extra: dict[str, Any] = {
        "salary_raw": salary_text,
        "requirements_raw": requirements_raw,
        "benefits_raw": benefits_raw,
        "experience_raw": experience_raw,
        "deadline_raw": deadline_raw,
    }

    return {
        "title": title,
        "company_name": company_name,
        "locations": locations,
        "description_raw": description_raw,
        "work_mode": work_mode,
        "posted_date_raw": posted_date_raw,
        "salary_status": salary_status,
        "salary_min": None,
        "salary_max": None,
        "source_extra": source_extra,
    }


def _parse_listing(raw: RawRecord) -> dict[str, Any]:
    title = raw.title_listing or ""
    company_name = ""
    work_mode = None
    posted_date_raw = ""
    salary_status = SalaryStatus.NOT_PROVIDED
    locations: list[str] = []

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



        company_nodes = tree.xpath('//a[contains(@href, "/companies/")]')
        for cn in company_nodes:
            text = cn.text_content().strip()
            if text:
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
            "salary_raw": "",
            "requirements_raw": "",
            "benefits_raw": "",
            "experience_raw": "",
            "deadline_raw": "",
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
    if raw.detail_crawled and raw.raw_html_detail:
        data = _parse_detail(raw)
    else:
        data = _parse_listing(raw)

    posted_date_raw = data.get("posted_date_raw", "")
    batch_date = datetime.strptime(raw.batch_date, "%Y-%m-%d").date()
    # [FIX P2] allow_future=False: chặn parse nhầm "Hạn ứng tuyển" (deadline, luôn
    # ở tương lai) thành ngày đăng — tránh ghi posted_date trong tương lai (audit #9).
    posted_date_parsed = parse_vietnamese_date(posted_date_raw, batch_date, allow_future=False)

    if posted_date_parsed:
        data["source_extra"]["posted_date_parsed"] = posted_date_parsed.isoformat()

    return SourceNormalized(
        job_id=raw.job_id,
        source=raw.source,
        batch_date=raw.batch_date,
        url=raw.url,
        title=data["title"],
        company_name=data["company_name"],
        locations=data["locations"],
        description_raw=data["description_raw"],
        posted_date_raw=posted_date_raw,
        posted_date=posted_date_parsed,
        salary_status=data["salary_status"],
        salary_min=data["salary_min"],
        salary_max=data["salary_max"],
        work_mode=data["work_mode"],
        listing_position=raw.listing_position,
        source_extra=data["source_extra"],
    )