"""数据库模型定义"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum as SAEnum
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    display_name = Column(String(50), nullable=False)
    role = Column(String(10), default=UserRole.employee.value)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    checkins = relationship("Checkin", back_populates="user")
    memberships = relationship("TeamMember", back_populates="user")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    invite_code = Column(String(10), unique=True, index=True, nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("TeamMember", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="memberships")


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    checkin_date = Column(Date, default=date.today, nullable=False)
    checkin_time = Column(DateTime, nullable=True)
    checkout_time = Column(DateTime, nullable=True)
    status = Column(String(10), default=CheckinStatus.normal.value)

    user = relationship("User", back_populates="checkins")
