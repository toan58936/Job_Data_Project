import re
from typing import Any, Optional
from datetime import datetime 
from lxml import html

from pipeline.model.raw_record import RawRecord
from pipeline.model.source_normalized import SalaryStatus, SourceNormalized, WorkMode
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


def _get_salary_status(text: str) -> SalaryStatus:
    """
    Chỉ phân loại trạng thái lương, KHÔNG bóc tách con số ở bước này.
    Việc bóc tách và quy đổi tỷ giá sẽ do shared_salary_convert.py đảm nhiệm.
    """
    cleaned = text.strip().lower()
    if not cleaned:
        return SalaryStatus.NOT_PROVIDED
    if cleaned in ("thoả thuận", "thỏa thuận", "thương lượng", "negotiable"):
        return SalaryStatus.NEGOTIABLE
    return SalaryStatus.DISCLOSED


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


def _extract_label_value_pairs(tree, item_class: str, label_class: str, value_class: str) -> dict[str, str]:
    """[MỚI] Đọc cặp label/value dạng "Nhãn: Giá trị" theo 1 class item bọc ngoài —
    dùng chung cho 2 cấu trúc khác nhau trên trang /brand/ (general-information-data
    và basic-information-item), tránh viết lặp lại logic duyệt y hệt 2 lần."""
    result: dict[str, str] = {}
    items = tree.xpath(f'//div[{_has_class(item_class)}]')
    for item in items:
        label_node = item.xpath(f'.//div[{_has_class(label_class)}]')
        value_node = item.xpath(f'.//div[{_has_class(value_class)}]')
        if label_node and value_node:
            label_text = _extract_text(label_node[0])
            result[label_text] = _extract_text(value_node[0])
    return result


def _extract_brand_page_boxes(tree) -> dict[str, str]:
    """[MỚI] Template /brand/ (VD www.topcv.vn/brand/{slug}/tuyen-dung/...) dùng
    class hoàn toàn khác /viec-lam/ cho khối Mô tả/Yêu cầu/Quyền lợi/Địa điểm —
    đã verify trên HTML thật job 2237041 (FPT Software): premium-job-description__box,
    title qua h2.premium-job-description__box--title, nội dung qua
    .premium-job-description__box--content. Lưu ý benefit ở đây ghi "Quyền lợi được
    hưởng" (khác "Quyền lợi ứng viên" của /viec-lam/) nên phải check riêng."""
    result: dict[str, str] = {}
    boxes = tree.xpath(f'//div[{_has_class("premium-job-description__box")}]')
    for box in boxes:
        title_node = box.xpath(f'.//*[{_has_class("premium-job-description__box--title")}]')
        title_text = _extract_text(title_node[0]) if title_node else ""
        content_node = box.xpath(f'.//*[{_has_class("premium-job-description__box--content")}]')
        content_text = _clean_whitespace(_extract_text(content_node[0])) if content_node else ""

        if "Mô tả công việc" in title_text and content_text:
            result["description_raw"] = content_text
        elif "Yêu cầu ứng viên" in title_text and content_text:
            result["requirements_raw"] = content_text
        elif "Quyền lợi" in title_text and content_text:
            result["benefits_raw"] = content_text
        elif "Địa điểm làm việc" in title_text:
            # Nội dung địa điểm không nằm trong node "--content" như các box khác, mà
            # là các <div> con trực tiếp -- lấy toàn bộ text() của box, trừ title.
            # HTML gốc có ký tự "-" bullet thô ngay đầu mỗi dòng (vd "- Hồ Chí Minh: ...")
            # -- dọn đi để nhất quán với locations của /viec-lam/ (không có bullet).
            loc_divs = box.xpath('./div/div')
            locs = [re.sub(r'^[-\s]+', '', _extract_text(d)) for d in loc_divs if _extract_text(d)]
            locs = [l for l in locs if l]
            if locs:
                result["locations"] = locs
    return result


def _extract_brand_page_skill_tags(tree) -> list[str]:
    """[MỚI] Trang /brand/ không có cấu trúc "Kỹ năng cần có/nên có" (div.required-tag)
    như /viec-lam/ -- chỉ có nhóm tag "Chuyên môn:" (VD "Chuyên môn Data Engineer",
    "IT - Phần mềm"), mang tính CHUYÊN NGÀNH hơn là kỹ năng kỹ thuật cụ thể. Map vào
    skills_industry_raw (không phải skills_required_raw) vì gần nghĩa "Kiến thức ngành"
    nhất trong 3 field hiện có của topcv -- kỹ năng kỹ thuật thật (Python, Pyspark...)
    chỉ nằm trong requirements_raw dạng văn xuôi, sẽ được Giai đoạn 2 (text-mining) bắt
    qua union tag+text, không cần ép vào đây."""
    groups = tree.xpath(f'//div[{_has_class("job-tags__group")}]')
    for group in groups:
        name_node = group.xpath(f'.//div[{_has_class("job-tags__group-name")}]')
        name_text = _extract_text(name_node[0]) if name_node else ""
        if "Chuyên môn" in name_text:
            tags = group.xpath('.//a[contains(@class, "search-from-tag")]')
            tag_texts = [_extract_text(t) for t in tags if _extract_text(t)]
            if tag_texts:
                return tag_texts
    return []


def _parse_detail(raw: RawRecord) -> dict[str, Any]:
    tree = _fromstring(raw.raw_html_detail)

    # --- Title ---
    title = ""
    title_nodes = tree.xpath('//h1[contains(@class, "box-header-job__title")]')
    if not title_nodes:
        # SỬA: trang "brand" của TopCV (VD /brand/fptsoftwareacademy/tuyen-dung/...,
        # trang tuyển dụng riêng của 1 công ty) dùng template khác hẳn trang /viec-lam/
        # thường — không có h1.box-header-job__title, tiêu đề tin nằm ở <h4 class="title-job">.
        title_nodes = tree.xpath('//h4[contains(@class, "title-job")]')
    if not title_nodes:
        # Fallback cuối cùng: lấy <h1> bất kỳ — NHƯNG loại trừ h1 nằm trong
        # <a class="company-content__name"> (đây chính là tên CÔNG TY trên trang brand,
        # không phải tên tin — nếu không loại trừ, title sẽ bị gán nhầm = tên công ty).
        title_nodes = tree.xpath(
            '//h1[not(ancestor::a[contains(@class, "company-content__name")])]'
        )
    if title_nodes:
        title = re.sub(r"\s+", " ", title_nodes[0].xpath("string(.)")).strip()

    # --- Company name ---
    company_name = ""
    company_nodes = tree.xpath('//div[contains(@class, "box-company-info__detail")]//a[contains(@class, "name")]')
    if not company_nodes:
        company_nodes = tree.xpath('//div[contains(@class, "company-name-label")]//a[contains(@class, "name")]')
    if not company_nodes:
        # SỬA: trang brand — tên công ty nằm trong <a class="company-content__name">,
        # bọc 1 <h1> (chính cái h1 dễ bị nhầm ở trên). Đây mới là nơi ĐÚNG để lấy company_name.
        company_nodes = tree.xpath('//a[contains(@class, "company-content__name")]')
    if company_nodes:
        company_name = re.sub(r"\s+", " ", company_nodes[0].text_content()).strip()

    # Fallback: tìm bất kỳ link nào chứa tên công ty
    if not company_name:
        company_nodes = tree.xpath('//a[contains(@href, "/cong-ty/")]//span')
        if company_nodes:
            company_name = re.sub(r"\s+", " ", company_nodes[0].text_content()).strip()
    if not company_name:
        # SỬA: fallback thêm cho link dạng /brand/{slug} có class "company" (thấy ở khối
        # "same company" job cards) — dùng làm phao cứu cuối nếu 2 cách trên đều trượt.
        company_nodes = tree.xpath('//a[contains(@href, "/brand/") and contains(@class, "company")]')
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

    # [MỚI] Fallback duy nhất cho toàn bộ description/requirements/benefits/locations
    # của template /brand/ — chỉ chạy khi selector /viec-lam/ ở trên không bắt được gì,
    # đã verify bằng HTML thật (job 2237041, FPT Software): cả 4 field này đều rỗng
    # trên trang /brand/ trước khi có fallback này.
    brand_boxes = _extract_brand_page_boxes(tree)
    if not description_raw and brand_boxes.get("description_raw"):
        description_raw = brand_boxes["description_raw"]
    if not requirements_raw and brand_boxes.get("requirements_raw"):
        requirements_raw = brand_boxes["requirements_raw"]
    if not benefits_raw and brand_boxes.get("benefits_raw"):
        benefits_raw = brand_boxes["benefits_raw"]
    if not locations and brand_boxes.get("locations"):
        for loc in brand_boxes["locations"]:
            if loc not in seen_locs:
                seen_locs.add(loc)
                locations.append(loc)

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

    # [MỚI] Fallback lương + hình thức làm việc + kinh nghiệm cho template /brand/ —
    # cấu trúc thật (job 2237041): div.basic-information-item chứa cặp
    # "Mức lương"/"Địa điểm"/"Kinh nghiệm", div.general-information-data chứa
    # "Hình thức làm việc"/"Cấp bậc"... Class "box-header-job__salary--title" hoàn toàn
    # không tồn tại trên trang /brand/ (đã grep xác nhận), nên salary_text luôn rỗng
    # nếu không có nhánh này.
    basic_info = _extract_label_value_pairs(
        tree, "basic-information-item", "basic-information-item__data--label", "basic-information-item__data--value"
    )
    general_info = _extract_label_value_pairs(
        tree, "general-information-data", "general-information-data__label", "general-information-data__value"
    )
    if not salary_text and basic_info.get("Mức lương"):
        salary_text = basic_info["Mức lương"]
    if work_mode is None and general_info.get("Hình thức làm việc"):
        work_mode = _map_work_mode(general_info["Hình thức làm việc"])

    # Chỉ lấy status, không parse số ở đây nữa
    salary_status = _get_salary_status(salary_text)

    # --- Kinh nghiệm / Hạn ứng tuyển ---
    header_info = _extract_header_list_info(tree)
    if "experience_raw" not in header_info and basic_info.get("Kinh nghiệm"):
        header_info["experience_raw"] = basic_info["Kinh nghiệm"]
    if "deadline_raw" not in header_info:
        deadline_nodes = tree.xpath('//*[contains(@class, "job-detail__info--deadline-date")]')
        if deadline_nodes:
            deadline_text = _extract_text(deadline_nodes[0])
            if deadline_text:
                header_info["deadline_raw"] = deadline_text

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

    # [MỚI] Template /brand/ không có div.required-tag -- chỉ có nhóm tag "Chuyên môn:"
    # (vd "Chuyên môn Data Engineer", "IT - Phần mềm"), gần nghĩa "Kiến thức ngành" hơn
    # là "Kỹ năng cần có" nên map vào skills_industry_raw, KHÔNG map vào skills_required_raw
    # để tránh trộn lẫn 2 loại thông tin khác bản chất (chuyên ngành công việc vs kỹ năng
    # kỹ thuật cụ thể). Kỹ năng kỹ thuật thật (Python, Pyspark...) vẫn có trong
    # requirements_raw dạng văn xuôi, Giai đoạn 2 (text-mining) sẽ tự bắt qua union.
    if not skills_required and not skills_nice_to_have and not skills_industry:
        brand_industry_tags = _extract_brand_page_skill_tags(tree)
        if brand_industry_tags:
            skills_industry = brand_industry_tags

    source_extra: dict[str, Any] = {
        "salary_raw": salary_text,  # Đẩy text gốc sang đây cho Bước 4
        "skills_required_raw": skills_required,
        "skills_nice_to_have_raw": skills_nice_to_have,
        "skills_industry_raw": skills_industry,
        "requirements_raw": requirements_raw,
        "benefits_raw": benefits_raw,
        **header_info,  
    }

    return {
        "title": title,
        "company_name": company_name,
        "locations": locations,
        "description_raw": description_raw,
        "work_mode": work_mode,
        "salary_status": salary_status,
        "salary_min": None, # Reset về None để Pipeline xử lý
        "salary_max": None, # Reset về None để Pipeline xử lý
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
            "salary_raw": "",
            "skills_required_raw": [],
            "skills_nice_to_have_raw": [],
            "skills_industry_raw": [],
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