"""
SOURCE_REGISTRY  nguồn sự thật duy nhất cho capability mỗi nguồn.
Mỗi giá trị PHẢI kèm evidence (file mẫu + ngày verify) khi sửa nguyên tắc 6.

Giá trị dưới dây đã verify trực tiếp trên HTML thật (itviec_sample.html,
itviec_list.html, topcv_sample.html, topcv_list.html)  không phải giả định.
"""

SOURCE_REGISTRY = {
    "itviec": {
        "requires_browser": True,
        "has_ajax_preview": True,          # listing tr? /content?job_index=N (fragment, SAI)
                                            # detail dúng: /it-jobs/{slug}
        "has_json_data_layer": True,       # data-jobs--save-data-layer-value  verify: có th?t
        "provides_skill_tags": True,
        "skill_tag_structure": "flat",
        "salary_can_be_gated": True,       # "Sign in to view salary"
        "id_strategy": "url_slug",         # data-search--job-selection-job-slug-value
    },
    "topcv": {
        "requires_browser": True,
        "has_ajax_preview": False,
        "has_json_data_layer": False,
        "provides_skill_tags": True,       # div.required-tags  verify: dúng là skill, không ph?i benefit
        "skill_tag_structure": "grouped",  # Ki?n th?c ngành / K? nang c?n có / K? nang nên có
        "salary_can_be_gated": False,
        "id_strategy": "numeric_path",     # s? cu?i URL tru?c .html, vd 2243980
    },
}
