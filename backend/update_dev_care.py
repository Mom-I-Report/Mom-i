"""
update_dev_care.py — Developmental_Care 테이블 전체 업데이트

사용법:
    cd Mom-i/backend
    python update_dev_care.py

- JSON 파일 기준으로 모든 61개 항목을 upsert (덮어쓰기)
- seed_dev_care.py의 CORRECTIONS는 이미 JSON에 반영됐으므로 별도 적용 불필요
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

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)

def main():
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "docs", "mwlee", "developmental-care", "content-draft-merged.json"
    )

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    entries = data["entries"]
    print(f"JSON 로드 완료: {len(entries)}개")

    db = Session()

    try:
        updated = 0
        for e in entries:
            row = db.query(DevelopmentalCare).filter(DevelopmentalCare.id == e["id"]).first()
            if row:
                row.type                   = e["type"]
                row.age_months             = e["age_months"]
                row.age_weeks              = e.get("age_weeks")
                row.age_label              = e["age_label"]
                row.wonder_weeks_leap      = e.get("wonder_weeks_leap")
                row.is_sleep_regression    = bool(e.get("is_sleep_regression", False))
                row.dev_status             = e["dev_status"]
                row.sleep_activities       = e["sleep_activities"]
                row.vaccination            = e["vaccination"]
                row.separation_sleep_guide = e["separation_sleep_guide"]
                updated += 1
            else:
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
                updated += 1

        db.commit()
        print(f"업데이트 완료: {updated}개")

    except Exception as ex:
        db.rollback()
        print(f"오류 발생: {ex}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
