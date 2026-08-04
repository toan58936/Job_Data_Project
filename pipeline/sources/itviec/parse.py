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

    # [FIX] Ưu tiên đọc "salary_range" từ JSON data layer (data-jobs--save-data-layer-value)
    # TRƯỚC KHI dò HTML node theo class. Đây là cùng 1 cơ chế đang chạy đúng cho
    # title/company_name/locations ở trên -- đáng tin hơn dò class CSS (class có thể đổi
    # theo layout, nhưng data layer là dữ liệu JS render dùng nội bộ, ổn định hơn).
    # Đã verify trên HTML thật (2 job CIC): field này tồn tại, có giá trị "You'll love it"
    # -- placeholder marketing của chính ITviec khi nhà tuyển dụng không muốn tiết lộ số,
    # KHÔNG phải dấu hiệu site đổi giao diện hay bị đăng xuất (trang không hề có chữ
    # "Sign in to view salary" ở case này). Bản trước bỏ sót nhánh đọc json_data này khi
    # refactor "gom text thô cho Bước 4", khiến mọi job dùng kiểu placeholder này bị ghi
    # nhận sai thành NOT_PROVIDED dù trang có hiển thị thông tin (dù không phải số).
    if json_data:
        salary_text = (json_data.get("salary_range") or "").strip()

    # 1. Fallback: dò trong phạm vi container (tránh quét nhầm sang Similar Jobs bên dưới)
    #    -- chỉ chạy khi JSON data layer không có/rỗng.
    if not salary_text:
        salary_nodes = []
        if container:
            salary_nodes = container[0].xpath(
                './/span[contains(@class, "sign-in-view-salary") or contains(text(), "Sign in to view salary")] | .//a[contains(@class, "sign-in-view-salary")]'
            )

        # Fallback an toàn trên toàn tree nếu container không bắt được
        if not salary_nodes:
            salary_nodes = tree.xpath(
                '//span[contains(@class, "sign-in-view-salary") or contains(text(), "Sign in to view salary")] | //a[contains(@class, "sign-in-view-salary")]'
            )

        if salary_nodes:
            salary_text = _extract_text(salary_nodes[0])

        # 2. Nếu vẫn không thấy, thử tìm các thẻ hiển thị lương thông thường
        if not salary_text and container:
            salary_range_nodes = container[0].xpath('.//div[contains(@class, "salary")]//span | .//span[contains(@class, "salary")]')
            if salary_range_nodes:
                salary_text = _extract_text(salary_range_nodes[0])

    # 3. Phân loại trạng thái lương
    cleaned_salary = salary_text.strip().lower()
    if not cleaned_salary:
        salary_status = SalaryStatus.NOT_PROVIDED
    elif "sign in" in cleaned_salary or "đăng nhập" in cleaned_salary:
        salary_status = SalaryStatus.AUTH_GATED
    elif not re.search(r"\d", cleaned_salary):
        # [FIX] Trước đây chỉ nhận diện negotiable qua danh sách cứng
        # ("thoả thuận", "thỏa thuận", "negotiable") -- bỏ sót mọi câu copy khác
        # ITviec có thể dùng (đã thấy thật: "You'll love it"). Đổi sang tiêu chí
        # tổng quát: chuỗi KHÔNG chứa chữ số thì chắc chắn không phải 1 mức lương cụ
        # thể, bất kể nó viết gì -- tự động chịu được khi ITviec đổi câu copy trong
        # tương lai mà không cần sửa code mỗi lần.
        salary_status = SalaryStatus.NEGOTIABLE
    else:
        # Có chuỗi văn bản lương cụ thể chứa số (VD: "1000 - 2000 USD")
        salary_status = SalaryStatus.DISCLOSED

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

    if not json_skills:
        json_skills = skill_groups["skills"]

    source_extra: dict[str, Any] = {
        "salary_raw": salary_text,  # Đẩy chuỗi lương thô sang cho Bước 4 tính toán
        "skills_raw": json_skills,
        "job_expertise_raw": skill_groups["job_expertise"],
        "job_domain_raw": skill_groups["job_domain"],
    }

    return {
        "title": title,
        "company_name": company_name,
        "locations": locations,
        "description_raw": description_raw,
        "work_mode": work_mode,
        "posted_date_raw": posted_date_raw,
        "salary_status": salary_status,
        "salary_min": None,  # Reset để Bước 4 lo
        "salary_max": None,  # Reset để Bước 4 lo
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