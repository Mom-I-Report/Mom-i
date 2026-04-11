from sqlalchemy import Column, Integer, String, Date, Text, Boolean, DateTime, ForeignKey
from app.infrastructure.database.session import Base


class GeneratedReport(Base):
    __tablename__ = "Generated_Reports"

    report_id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id           = Column(Integer, ForeignKey("Users.user_id", ondelete="CASCADE"))
    ai_kick_comment   = Column(Text)
    report_url        = Column(String(255))
    measured_week_start = Column(Date)
    is_deleted        = Column(Boolean, default=False)
    created_at        = Column(DateTime)
