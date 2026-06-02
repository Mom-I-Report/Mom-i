"""
seed_dev_care.py — Developmental_Care 테이블 초기 데이터 삽입

사용법:
    cd Mom-i/backend
    python seed_dev_care.py

- 이미 데이터가 있으면 건너뜀 (멱등 실행 가능)
- 검수 수정 사항을 인라인으로 적용한 후 삽입
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.domain.report.entity import DevelopmentalCare
from app.infrastructure.database.session import Base

# ── DB 연결 ──
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)

# ── 검수 수정 목록 ──
# key: 항목 id, value: 수정할 필드와 값
CORRECTIONS = {
    10: {
        "sleep_activities_2": "취침 전 화이트노이즈 사용: 도약 중 자극에 민감해진 신경계를 안정시켜 입면 시간을 단축"
    },
    28: {
        "separation_sleep_guide": "꾸준한 루틴 유지가 이 진전을 이어가는 핵심입니다."
    },
    34: {
        "dev_status_prefix": ("12개월 첫 번째 생일이에요! 이 시기 아기는", "생후 12개월에 접어든 아기는")
    },
    46: {
        "dev_status_prefix": ("어휘가 50~100개 수준으로 늘고", "표현 어휘가 100개 이상으로 늘고")
    },
    49: {
        "dev_status_prefix": ("만 2세! 두", "생후 24개월. 두")
    },
    55: {
        "dev_status_prefix": ("어휘가 50개 이상이고", "표현 어휘가 300개 이상이고")
    },
    61: {
        "dev_status_prefix": ("만 3세! 이 시기 아이는", "생후 36개월. 이 시기 아이는"),
        "sep_guide_suffix": (
            "잘 자라준 아이와 함께 이 여정을 달려온 부모님, 정말 잘하셨어요!",
            "수면 독립이 완전히 자리잡은 시기입니다."
        )
    },
}


def apply_corrections(entry: dict) -> dict:
    e = dict(entry)
    eid = e["id"]
    if eid not in CORRECTIONS:
        return e

    c = CORRECTIONS[eid]

    if "sleep_activities_2" in c:
        acts = list(e["sleep_activities"])
        acts[2] = c["sleep_activities_2"]
        e["sleep_activities"] = acts

    if "separation_sleep_guide" in c:
        e["separation_sleep_guide"] = c["separation_sleep_guide"]

    if "dev_status_prefix" in c:
        old, new = c["dev_status_prefix"]
        e["dev_status"] = e["dev_status"].replace(old, new, 1)

    if "sep_guide_suffix" in c:
        old, new = c["sep_guide_suffix"]
        e["separation_sleep_guide"] = e["separation_sleep_guide"].replace(old, new, 1)

    return e


def main():
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "docs", "mwlee", "developmental-care", "content-draft-merged.json"
    )

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    entries = data["entries"]
    print(f"JSON 로드 완료: {len(entries)}개")

    Base.metadata.create_all(bind=engine)
    db = Session()

    try:
        existing_count = db.query(DevelopmentalCare).count()
        if existing_count > 0:
            print(f"이미 {existing_count}개 항목이 존재합니다. 삽입을 건너뜁니다.")
            print("강제 재삽입이 필요하면 테이블을 먼저 비워주세요: DELETE FROM Developmental_Care;")
            return

        inserted = 0
        for raw in entries:
            e = apply_corrections(raw)
            row = DevelopmentalCare(
                id                     = e["id"],
                type                   = e["type"],
                age_months             = e["age_months"],
                age_weeks              = e.get("age_weeks"),
                age_label              = e["age_label"],
                wonder_weeks_leap      = e.get("wonder_weeks_leap"),
                is_sleep_regression    = bool(e.get("is_sleep_regression", False)),
                dev_status             = e["dev_status"],
                sleep_activities       = e["sleep_activities"],
                vaccination            = e["vaccination"],
                separation_sleep_guide = e["separation_sleep_guide"],
            )
            db.add(row)
            inserted += 1

        db.commit()
        print(f"삽입 완료: {inserted}개")

    except Exception as ex:
        db.rollback()
        print(f"오류 발생: {ex}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
