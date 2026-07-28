import re
from typing import Any, Optional

from lxml import html
from pydantic import BaseModel

from pipeline.model.raw_record import RawRecord
from pipeline.model.source_normalized import SalaryStatus, SourceNormalized, WorkMode
from pipeline.tools.skill_extractor import canonicalize_skills_list


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


def _parse_listing_posted_date(raw_html_listing: Optional[str]) -> str:
    if not raw_html_listing:
        return ""
    try:
        tree = html.fromstring(raw_html_listing)
        label = tree.xpath('//label[contains(@class, "label-update")]')
        if label:
            text = " ".join(label[0].itertext()).strip()
            text = re.sub(r"Đăng\s+", "", text).strip()
            return text
    except Exception:
        pass
    return ""


def _parse_detail(raw: RawRecord) -> dict[str, Any]:
    tree = html.fromstring(raw.raw_html_detail)

    title = ""
    title_nodes = tree.xpath('//h1[contains(@class, "box-header-job__title")]')
    if title_nodes:
        title = title_nodes[0].xpath("string(.)").strip()

    company_name = ""
    company_nodes = tree.xpath('//div[contains(@class, "box-company-info__detail")]//a[contains(@class, "name")]')
    if company_nodes:
        company_name = company_nodes[0].text_content().strip()
    if not company_name:
        company_nodes = tree.xpath('//div[contains(@class, "company-name-label")]//a[contains(@class, "name")]')
        if company_nodes:
            company_name = company_nodes[0].text_content().strip()

    locations: list[str] = []
    seen_locs: set[str] = set()
    address_items = tree.xpath('//div[contains(@class, "box-job-information-address-and-time-list")]')
    for item in address_items:
        title_text = _extract_text(item.xpath('.//h3[contains(@class, "box-job-information-address-and-time-list__item--title")]'))
        if "Địa điểm làm việc" in title_text:
            lis = item.xpath('.//li')
            for li in lis:
                strong = li.xpath(".//strong")
                if strong:
                    loc = strong[0].text_content().strip().rstrip(":")
                    if loc and loc not in seen_locs:
                        seen_locs.add(loc)
                        locations.append(loc)

    description_raw = ""
    detail_items = tree.xpath('//div[contains(@class, "box-job-information-detail-item")]')
    for item in detail_items:
        title_text = _extract_text(item.xpath('.//h2[contains(@class, "box-job-information-detail-item__title--title")]'))
        if "Mô tả công việc" in title_text:
            text_div = item.xpath('.//div[contains(@class, "box-job-information-detail-item__text")]')
            if text_div:
                description_raw = _extract_text(text_div[0])
            break

    work_mode = None
    general_info_items = tree.xpath('//div[contains(@class, "box-job-information-general-info-list__item")]')
    for item in general_info_items:
        title_text = _extract_text(item.xpath('.//div[contains(@class, "box-job-information-general-info-list__item--content-title")]'))
        if "Hình thức làm việc" in title_text:
            desc = item.xpath('.//div[contains(@class, "box-job-information-general-info-list__item--content-desc")]')
            if desc:
                work_mode = _map_work_mode(_extract_text(desc[0]))
            break

    salary_text = ""
    salary_nodes = tree.xpath('//span[contains(@class, "box-header-job__salary--title")]')
    if salary_nodes:
        salary_text = salary_nodes[0].text_content().strip()
    salary_info = _parse_salary(salary_text)

    skills_required: list[str] = []
    skills_nice_to_have: list[str] = []
    skills_industry: list[str] = []
    required_tags = tree.xpath('//div[contains(@class, "required-tags")]//div[contains(@class, "required-tag")]')
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


def _parse_listing_posted_date(raw_html_listing: Optional[str]) -> str:
    if not raw_html_listing:
        return ""
    try:
        tree = html.fromstring(raw_html_listing)
        label = tree.xpath('//label[contains(@class, "label-update")]')
        if label:
            text = " ".join(label[0].itertext()).strip()
            text = re.sub(r"(?:Đăng\s+)?", "", text).strip()
            return text
    except Exception:
        pass
    return ""


def parse(raw: RawRecord) -> SourceNormalized:
    if raw.detail_crawled and raw.raw_html_detail:
        data = _parse_detail(raw)
    else:
        data = _parse_listing(raw)

    posted_date_raw = data.pop("posted_date_raw", "")
    if not posted_date_raw and raw.raw_html_listing:
        posted_date_raw = _parse_listing_posted_date(raw.raw_html_listing)

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
