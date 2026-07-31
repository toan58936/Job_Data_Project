import re
from typing import Any, Optional
from datetime import datetime 
from lxml import html
from pydantic import BaseModel

from pipeline.model.raw_record import RawRecord
from pipeline.model.source_normalized import SalaryStatus, SourceNormalized, WorkMode
from pipeline.tools.skill_extractor import canonicalize_skills_list
from pipeline.tools.date_parser import parse_vietnamese_date
# TopCV job pages không có <meta charset="utf-8">, nên lxml phải tự đoán encoding.
# Khi input là bytes (ví dụ đọc lại raw HTML từ Bronze storage), việc đoán sai encoding
# sẽ biến toàn bộ text tiếng Việt thành mojibake (VD: "Công ty" -> "CÃ´ng ty").
# Ép encoding="utf-8" tường minh để loại bỏ hoàn toàn rủi ro này, bất kể input là str hay bytes.
_HTML_PARSER = html.HTMLParser(encoding="utf-8")


def _fromstring(raw: str) -> html.HtmlElement:
    return html.fromstring(raw, parser=_HTML_PARSER)


def _has_class(class_name: str) -> str:
    """XPath predicate khớp CHÍNH XÁC 1 class token, tránh việc contains(@class, "X")
    vô tình khớp luôn các class con dùng chung tiền tố (VD: "box-job-information-detail-item"
    khớp nhầm cả "box-job-information-detail-item__title", "...__text"...), gây lặp vòng lặp
    thừa và tiềm ẩn lấy sai node khi cấu trúc trang thay đổi.
    """
    return f"contains(concat(' ', normalize-space(@class), ' '), ' {class_name} ')"


class _SalaryInfo(BaseModel):
    status: SalaryStatus
    min: Optional[float] = None
    max: Optional[float] = None


def _parse_salary(text: str) -> _SalaryInfo:
    cleaned = text.strip()
    if not cleaned or cleaned == "Thoả thuận" or cleaned == "Thỏa thuận":
        return _SalaryInfo(status=SalaryStatus.NEGOTIABLE)
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*triệu", cleaned, re.IGNORECASE)
    if match:
        return _SalaryInfo(
            status=SalaryStatus.DISCLOSED,
            min=float(match.group(1).replace(",", ".")),
            max=float(match.group(2).replace(",", ".")),
        )
    match = re.search(r"Tới\s+(\d+(?:[.,]\d+)?)\s*triệu", cleaned, re.IGNORECASE)
    if match:
        return _SalaryInfo(
            status=SalaryStatus.DISCLOSED,
            max=float(match.group(1).replace(",", ".")),
        )
    # "Trên X triệu" (chỉ có sàn lương, không có trần) — dạng này chưa được xử lý ở bản gốc.
    match = re.search(r"Trên\s+(\d+(?:[.,]\d+)?)\s*triệu", cleaned, re.IGNORECASE)
    if match:
        return _SalaryInfo(
            status=SalaryStatus.DISCLOSED,
            min=float(match.group(1).replace(",", ".")),
        )
    return _SalaryInfo(status=SalaryStatus.NOT_PROVIDED)


def _map_work_mode(text: str) -> Optional[WorkMode]:
    lowered = text.strip().lower()
    if "remote" in lowered and "onsite" not in lowered and "văn phòng" not in lowered:
        return WorkMode.REMOTE
    if "hybrid" in lowered:
        return WorkMode.HYBRID
    if "onsite" in lowered or "văn phòng" in lowered:
        return WorkMode.ONSITE
    return None


def _extract_text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, list):
        if not node:
            return ""
        node = node[0]
    return " ".join(node.itertext()).strip()


def _clean_whitespace(text: str) -> str:
    """Gom khoảng trắng/indent thừa do HTML nhiều dòng để lại, giữ nguyên xuống dòng
    giữa các bullet cho description để không dính hết thành 1 khối."""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _parse_listing_posted_date(raw_html_listing: Optional[str]) -> str:
    if not raw_html_listing:
        return ""
    try:
        tree = _fromstring(raw_html_listing)
        label = tree.xpath('//label[contains(@class, "label-update")]')
        if label:
            text = " ".join(label[0].itertext()).strip()
            text = re.sub(r"Đăng\s+", "", text).strip()
            return text
    except Exception:
        pass
    return ""


def _extract_header_list_info(tree) -> dict[str, str]:
    """Khối "Địa điểm / Kinh nghiệm / Hạn ứng tuyển" nằm ở box-header-job-list-info__item,
    HOÀN TOÀN tách biệt với box-job-information-general-info-list__item (nơi chứa Cấp bậc,
    Học vấn, Hình thức làm việc...). Bản gốc chỉ đọc general-info-list nên "Kinh nghiệm"
    và "Hạn ứng tuyển" chưa từng được crawl, dù dữ liệu có sẵn trên trang.
    """
    result: dict[str, str] = {}
    items = tree.xpath(f'//div[{_has_class("box-header-job-list-info__item")}]')
    for item in items:
        title = _extract_text(item.xpath(f'.//div[{_has_class("list-info__content__title")}]'))
        desc = _extract_text(item.xpath(f'.//div[{_has_class("list-info__content__desc")}]'))
        if not title or not desc:
            continue
        if "Kinh nghiệm" in title:
            result["experience_raw"] = desc
        elif "Hạn ứng tuyển" in title:
            result["deadline_raw"] = desc
    return result


def _parse_detail(raw: RawRecord) -> dict[str, Any]:
    tree = _fromstring(raw.raw_html_detail)

    # --- Title ---
    title = ""
    title_nodes = tree.xpath('//h1[contains(@class, "box-header-job__title")]')
    if not title_nodes:
        title_nodes = tree.xpath('//h1')
    if title_nodes:
        title = re.sub(r"\s+", " ", title_nodes[0].xpath("string(.)")).strip()

    # --- Company name ---
    company_name = ""
    company_nodes = tree.xpath('//div[contains(@class, "box-company-info__detail")]//a[contains(@class, "name")]')
    if not company_nodes:
        company_nodes = tree.xpath('//div[contains(@class, "company-name-label")]//a[contains(@class, "name")]')
    if company_nodes:
        company_name = re.sub(r"\s+", " ", company_nodes[0].text_content()).strip()

    # Fallback: tìm bất kỳ link nào chứa tên công ty
    if not company_name:
        company_nodes = tree.xpath('//a[contains(@href, "/cong-ty/")]//span')
        if company_nodes:
            company_name = re.sub(r"\s+", " ", company_nodes[0].text_content()).strip()

    # --- Locations ---
    locations: list[str] = []
    seen_locs: set[str] = set()
    address_items = tree.xpath(f'//div[{_has_class("box-job-information-address-and-time-list")}]')
    for item in address_items:
        title_text = _extract_text(
            item.xpath('.//h3[contains(@class, "box-job-information-address-and-time-list__item--title")]')
        )
        if "Địa điểm làm việc" in title_text or "Địa chỉ" in title_text:
            lis = item.xpath('.//li')
            for li in lis:
                # QUAN TRỌNG: lấy TOÀN BỘ text của <li>, không chỉ phần trong <strong>.
                # Bản gốc chỉ lấy strong[0].text_content() ("Hà Nội") và VỨT BỎ phần địa chỉ
                # chi tiết phía sau ("Tòa Rivera Park, 69 Vũ Trọng Phụng, Phường Thanh Xuân..."),
                # làm mất dữ liệu địa chỉ đầy đủ.
                text = re.sub(r"\s+", " ", li.xpath("string(.)")).strip()
                if text and text not in seen_locs:
                    seen_locs.add(text)
                    locations.append(text)

    # --- Description ---
    description_raw = ""
    requirements_raw = ""
    benefits_raw = ""
    detail_items = tree.xpath('//div[contains(@class, "box-job-information-detail-item")]')
    for item in detail_items:
        title_text = _extract_text(
            item.xpath('.//h2[contains(@class, "box-job-information-detail-item__title--title")]')
        )
        text_div = item.xpath('.//div[contains(@class, "box-job-information-detail-item__text")]')
        text_value = _clean_whitespace(_extract_text(text_div[0])) if text_div else ""
        if "Mô tả công việc" in title_text and text_value:
            description_raw = text_value
        elif "Yêu cầu ứng viên" in title_text and text_value:
            requirements_raw = text_value
        elif "Quyền lợi ứng viên" in title_text and text_value:
            benefits_raw = text_value

    # --- Work mode ---
    work_mode = None
    general_info_items = tree.xpath(f'//div[{_has_class("box-job-information-general-info-list__item")}]')
    for item in general_info_items:
        title_text = _extract_text(
            item.xpath('.//div[contains(@class, "box-job-information-general-info-list__item--content-title")]')
        )
        if "Hình thức làm việc" in title_text:
            desc = item.xpath(
                './/div[contains(@class, "box-job-information-general-info-list__item--content-desc")]'
            )
            if desc:
                work_mode = _map_work_mode(_extract_text(desc[0]))
            break

    # --- Salary ---
    salary_text = ""
    salary_nodes = tree.xpath('//span[contains(@class, "box-header-job__salary--title")]')
    if salary_nodes:
        salary_text = salary_nodes[0].text_content().strip()
    salary_info = _parse_salary(salary_text)

    # --- Kinh nghiệm / Hạn ứng tuyển (trước đây chưa được crawl) ---
    header_info = _extract_header_list_info(tree)

    # --- Skills ---
    skills_required: list[str] = []
    skills_nice_to_have: list[str] = []
    skills_industry: list[str] = []

    required_tags = tree.xpath(f'//div[{_has_class("required-tag")}]')
    for tag in required_tags:
        title_text = _extract_text(tag.xpath('.//h3[contains(@class, "required-tag__content--title")]'))
        desc_node = tag.xpath('.//div[contains(@class, "required-tag__content--desc")]')
        desc_text = _extract_text(desc_node[0]) if desc_node else ""
        if not desc_text:
            continue
        skills = [s.strip() for s in desc_text.split(",") if s.strip()]
        if "Kỹ năng cần có" in title_text:
            skills_required.extend(skills)
        elif "Kỹ năng nên có" in title_text:
            skills_nice_to_have.extend(skills)
        elif "Kiến thức ngành" in title_text:
            skills_industry.extend(skills)

    source_extra: dict[str, Any] = {
        "skills_required": canonicalize_skills_list(skills_required),
        "skills_nice_to_have": canonicalize_skills_list(skills_nice_to_have),
        "skills_industry": canonicalize_skills_list(skills_industry),
        "requirements_raw": requirements_raw,
        "benefits_raw": benefits_raw,
        **header_info,  # experience_raw, deadline_raw (chỉ có khi tìm thấy trên trang)
    }

    return {
        "title": title,
        "company_name": company_name,
        "locations": locations,
        "description_raw": description_raw,
        "work_mode": work_mode,
        "salary_status": salary_info.status,
        "salary_min": salary_info.min,
        "salary_max": salary_info.max,
        "source_extra": source_extra,
    }


def _parse_listing(raw: RawRecord) -> dict[str, Any]:
    company_name = ""
    title = raw.title_listing or ""
    posted_date_raw = _parse_listing_posted_date(raw.raw_html_listing) if raw.raw_html_listing else ""
    return {
        "title": title,
        "company_name": company_name,
        "locations": [],
        "description_raw": "",
        "work_mode": None,
        "salary_status": SalaryStatus.NOT_PROVIDED,
        "salary_min": None,
        "salary_max": None,
        "posted_date_raw": posted_date_raw,
        "source_extra": {
            "skills_required": [],
            "skills_nice_to_have": [],
            "skills_industry": [],
        },
    }


def parse(raw: RawRecord) -> SourceNormalized:
    if raw.detail_crawled and raw.raw_html_detail:
        data = _parse_detail(raw)
    else:
        data = _parse_listing(raw)

    posted_date_raw = data.pop("posted_date_raw", "")
    if not posted_date_raw and raw.raw_html_listing:
        posted_date_raw = _parse_listing_posted_date(raw.raw_html_listing)

    # Chuyển đổi sang ngày tuyệt đối
    batch_date = datetime.strptime(raw.batch_date, "%Y-%m-%d").date()
    posted_date_parsed = parse_vietnamese_date(posted_date_raw, batch_date)

    # Lưu vào source_extra
    source_extra = data["source_extra"]
    if posted_date_parsed:
        source_extra["posted_date_parsed"] = posted_date_parsed.isoformat()

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
        source_extra=source_extra,
    )
