"""
SOURCE_REGISTRY  ngu?n s? th?t duy nh?t cho capability t?ng ngu?n.
M?i giá tr? PH?I kèm evidence (file m?u + ngày verify) khi s?a  nguyên t?c 6.

Giá tr? du?i dây da verify tr?c ti?p trên HTML th?t (itviec_sample.html,
itviec_list.html, topcv_sample.html, topcv_list.html)  không ph?i gi? d?nh.
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
