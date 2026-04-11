from sqlalchemy import Column, Integer, String, Date, Float, DateTime, ForeignKey, Enum
from app.infrastructure.database.session import Base


class User(Base):
    __tablename__ = "Users"

    user_id    = Column(Integer, primary_key=True, autoincrement=True)
    email      = Column(String(100), nullable=False, unique=True)
    baby_name  = Column(String(50),  nullable=False)
    baby_birth = Column(Date,        nullable=False)
    baby_gender= Column(Enum("M", "F"), nullable=False)
    ser_no     = Column(String(50),  nullable=False, unique=True)
    created_at = Column(DateTime)


class DailySleepLog(Base):
    __tablename__ = "Daily_Sleep_Logs"

    sleep_id     = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("Users.user_id", ondelete="CASCADE"))
    day_gs       = Column(String(20))   # 실제 수면 시간 (예: "9h30m")
    day_pr       = Column(String(20))   # 뒤척임 시간   (예: "18m")
    measured_date= Column(Date, nullable=False)


class EnvironmentLog(Base):
    __tablename__ = "Environment_Logs"

    env_id       = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("Users.user_id", ondelete="CASCADE"))
    temp_avg     = Column(Float)
    temp_max     = Column(Float)
    temp_min     = Column(Float)
    db_max       = Column(Integer)
    measured_date= Column(Date, nullable=False)


class EventLog(Base):
    __tablename__ = "Event_Logs"

    event_id  = Column(Integer, primary_key=True, autoincrement=True)
    user_id   = Column(Integer, ForeignKey("Users.user_id", ondelete="CASCADE"))
    event_type= Column(String(20))   # "Crying", "Leave" 등
    event_time= Column(DateTime)
