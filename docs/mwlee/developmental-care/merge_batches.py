"""
발달 케어 콘텐츠 5개 배치 파일을 단일 JSON으로 병합.
실행: python merge_batches.py
출력: content-draft-merged.json (DB 삽입용)
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

BATCH_FILES = [
    "batch1_weeks16-26.json",
    "batch2_weeks27-39.json",
    "batch3_weeks40-52.json",
    "batch4_months13-24.json",
    "batch5_months25-36.json",
]

entries = []
for fname in BATCH_FILES:
    with open(HERE / fname, encoding="utf-8") as f:
        entries.extend(json.load(f))

output = {
    "version": "1.0",
    "generated_date": "2026-05-28",
    "status": "초안 — mwlee 검수 필요",
    "total_entries": len(entries),
    "schema": {
        "weekly": "생후 16주(4개월) ~ 52주(12개월), 37개 항목",
        "monthly": "생후 13개월 ~ 36개월, 24개 항목",
    },
    "fields": {
        "id": "순번",
        "type": "weekly | monthly",
        "age_months": "월령 (숫자)",
        "age_weeks": "주령 (주차별 항목만, monthly는 null)",
        "age_label": "표시용 라벨",
        "wonder_weeks_leap": "원더윅스 도약 번호 (null if none)",
        "is_sleep_regression": "수면 퇴행 시기 여부",
        "dev_status": "발달 상태 설명",
        "sleep_activities": "수면 도움 추천 활동 3가지 (list)",
        "vaccination": "예방접종 안내",
        "separation_sleep_guide": "분리수면 안내",
    },
    "entries": entries,
}

out_path = HERE / "content-draft-merged.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"완료: {len(entries)}개 항목 → {out_path}")
