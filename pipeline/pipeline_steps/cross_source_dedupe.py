"""
cross_source_dedupe.py — Bước 6: Khử trùng lặp chéo nguồn (Cross-Source Deduplication).
Chạy trên toàn bộ mảng JobPosting của một batch để gom các job được đăng
trên nhiều nền tảng (vd: ITviec và TopCV) về một bản ghi duy nhất.
"""
import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import List

from pipeline.model.job_posting import JobPosting


def _normalize_company_name(name: str) -> str:
    """Làm sạch tên công ty để phục vụ việc gom nhóm (bỏ các hậu tố pháp lý)."""
    if not name:
        return ""
    n = name.lower()
    terms_to_remove = [
        r"công ty", r"tnhh", r"cổ phần", r"cp", r"jsc", r"llc",
        r"tập đoàn", r"group", r"chi nhánh", r"việt nam", r"vietnam", r"vn"
    ]
    for term in terms_to_remove:
        n = re.sub(rf"\b{term}\b", "", n)
    n = re.sub(r"[^\w\s]", "", n)
    return re.sub(r"\s+", " ", n).strip()


def _title_similarity(t1: str, t2: str) -> float:
    """Tính tỷ lệ giống nhau giữa 2 tiêu đề công việc (0.0 đến 1.0)."""
    return SequenceMatcher(None, t1.lower(), t2.lower()).ratio()


def _locations_overlap(loc1: List[str], loc2: List[str]) -> bool:
    """Kiểm tra 2 job có giao thoa về địa điểm làm việc hay không."""
    if not loc1 or not loc2:
        return True  # Nếu 1 bên không ghi địa điểm, ngầm định có thể trùng
    return len(set(loc1).intersection(set(loc2))) > 0


def _merge_records(master: JobPosting, duplicate: JobPosting) -> JobPosting:
    """Hợp nhất dữ liệu: Master nuốt trọn Skills/Locations của Duplicate."""
    # Gộp tập kỹ năng (Loại bỏ trùng lặp bằng set)
    master.job_skills = list(set(master.job_skills + duplicate.job_skills))
    master.job_expertise = list(set(master.job_expertise + duplicate.job_expertise))
    master.job_domains = list(set(master.job_domains + duplicate.job_domains))

    # Gộp địa điểm
    master.locations = list(set(master.locations + duplicate.locations))

    # Lưu vết nguồn gốc (Audit Trail)
    merged_sources = master.source_extra.get("merged_sources", [master.source])
    if duplicate.source not in merged_sources:
        merged_sources.append(duplicate.source)
    master.source_extra["merged_sources"] = merged_sources

    merged_ids = master.source_extra.get("merged_job_ids", [master.job_id])
    if duplicate.job_id not in merged_ids:
        merged_ids.append(duplicate.job_id)
    master.source_extra["merged_job_ids"] = merged_ids

    return master


def deduplicate(records: List[JobPosting], similarity_threshold: float = 0.8) -> List[JobPosting]:
    """
    Điểm vào chính: Nhận danh sách JobPosting, trả về danh sách đã khử trùng lặp.
    """
    # 1. Gom nhóm theo tên công ty
    company_groups = defaultdict(list)
    for r in records:
        norm_name = _normalize_company_name(r.company_name)
        company_groups[norm_name].append(r)

    deduped_records = []

    # 2. Xử lý trùng lặp trong nội bộ từng công ty
    for comp_name, group in company_groups.items():
        if not comp_name or len(group) == 1:
            deduped_records.extend(group)
            continue

        merged_indices = set()
        for i in range(len(group)):
            if i in merged_indices:
                continue
            master = group[i]

            for j in range(i + 1, len(group)):
                if j in merged_indices:
                    continue
                candidate = group[j]

                # Nếu tiêu đề giống nhau >= 80% VÀ có chung địa điểm
                if _title_similarity(master.title, candidate.title) >= similarity_threshold:
                    if _locations_overlap(master.locations, candidate.locations):
                        # Bầu Master: Job nào mô tả chi tiết hơn sẽ làm gốc
                        if len(candidate.description_raw) > len(master.description_raw):
                            master, candidate = candidate, master
                        
                        master = _merge_records(master, candidate)
                        merged_indices.add(j)

            deduped_records.append(master)

    return deduped_records