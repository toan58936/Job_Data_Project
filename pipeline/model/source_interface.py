"""
SourceAdapter -- contract bat buoc moi nguon phai implement.

[Don gian hoa so voi thiet ke ban dau] Ban thiet ke truoc day co ca extract() lan
parse() trong contract nay. Sau khi viet pipeline_steps/merge.py thuc te, extract()
khong con can thiet o tang nay nua -- merge.py da doc jobs_meta_listing.jsonl +
jobs_meta_detail_status.jsonl + file .html mot cach HOAN TOAN source-agnostic (khong
biet gi ve itviec/topcv cu the), cho ra RawRecord chung cho moi nguon. Nen "extract"
thuc chat da la buoc dung chung, khong phai dac thu tung nguon -- khong can khai bao
trong SourceAdapter.

Vi vay contract chi con dung 1 method:
"""
from typing import Protocol

from pipeline.model.raw_record import RawRecord
from pipeline.model.source_normalized import SourceNormalized


class SourceAdapter(Protocol):
    def parse(self, raw: RawRecord) -> SourceNormalized:
        """Nhan 1 RawRecord (da merge xong tu crawler output), tra ve SourceNormalized.
        KHONG duoc raise loi neu thieu field extension (source_extra) -- chi raise loi
        neu thieu field CORE bat buoc (title, company_name, url...).
        Neu raw.detail_crawled=False, parse() van phai chay duoc voi du lieu tu listing
        thoi (mo ta co the rong, salary_status=NOT_PROVIDED)."""
        ...