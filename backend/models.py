"""数据库模型定义"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
import enum
from database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    employee = "employee"


class CheckinStatus(str, enum.Enum):
    normal = "normal"
    late = "late"
    early = "early"
    absent = "absent"
    late_pm = "late_pm"
    early_am = "early_am"
    early_pm = "early_pm"
    overdue_am = "overdue_am"  # 上午签退超时（>13:00）


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    display_name = Column(String(50), nullable=False)
    role = Column(String(10), default=UserRole.employee.value)
    created_at = Column(DateTime, default=datetime.utcnow)

    checkins = relationship("Checkin", back_populates="user")
    memberships = relationship("TeamMember", back_populates="user")
    sent_messages = relationship("Mailbox", back_populates="sender", foreign_keys="Mailbox.sender_id")
    received_messages = relationship("Mailbox", back_populates="receiver", foreign_keys="Mailbox.receiver_id")


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    invite_code = Column(String(10), unique=True, index=True, nullable=False)
    admin_invite_code = Column(String(10), unique=True, index=True, nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("TeamMember", back_populates="team")
    scores = relationship("UserScore", back_populates="team")
    score_records = relationship("ScoreRecord", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    join_type = Column(String(20), default="code")
    joined_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="memberships")


class JoinRequest(Base):
    __tablename__ = "join_requests"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class Mailbox(Base):
    __tablename__ = "mailbox"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    msg_type = Column(String(20), default="personal")
    title = Column(String(200), nullable=False)
    content = Column(String(2000), nullable=False)
    is_read = Column(String(20), default="False")
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    receiver = relationship("User", back_populates="received_messages", foreign_keys=[receiver_id])


class ScoreRecord(Base):
    __tablename__ = "score_records"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score_change = Column(Integer, nullable=False)
    reason = Column(String(200), nullable=True)
    score_after = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="score_records")


class UserScore(Base):
    __tablename__ = "user_scores"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Integer, default=60)
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uix_team_user_score"),)
    team = relationship("Team", back_populates="scores")


class Checkin(Base):
    __tablename__ = "checkins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    checkin_date = Column(Date, default=date.today, nullable=False)
    am_checkin_time = Column(DateTime, nullable=True)
    am_checkout_time = Column(DateTime, nullable=True)
    am_status = Column(String(10), default=CheckinStatus.normal.value)
    pm_checkin_time = Column(DateTime, nullable=True)
    pm_checkout_time = Column(DateTime, nullable=True)
    pm_status = Column(String(10), default=CheckinStatus.normal.value)
    user = relationship("User", back_populates="checkins")
