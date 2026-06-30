"""调试路由"""
import time
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User, Team, TeamMember, Checkin
from routes.auth import verify_token

router = APIRouter(prefix="/api/debug", tags=["debug"])
_time_offset = 0.0

def get_debug_time(): return datetime.now() + timedelta(seconds=_time_offset)

class AddMemberReq(BaseModel):
    team_id: int
    phone: str
    display_name: str
    role: str = "employee"

@router.post("/add-member")
def add_member(req: AddMemberReq, authorization: str = Header(None), db: Session = Depends(get_db)):
    payload = verify_token(authorization.split(" ")[1])
    team = db.query(Team).filter(Team.id == req.team_id).first()
    if not team or team.admin_id != payload["user_id"]:
        raise HTTPException(403, "仅管理员可操作")
    user = db.query(User).filter(User.username == req.phone).first()
    if not user:
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user = User(username=req.phone, password_hash=pwd.hash("debug_" + str(int(time.time()))), display_name=req.display_name, role=req.role)
        db.add(user); db.commit(); db.refresh(user)
    if db.query(TeamMember).filter(TeamMember.team_id == req.team_id, TeamMember.user_id == user.id).first():
        raise HTTPException(400, "已是团队成员")
    db.add(TeamMember(team_id=req.team_id, user_id=user.id, join_type="admin"))
    db.commit()
    return {"message": f"已添加成员 {user.display_name}"}

class SetTimeReq(BaseModel):
    offset_seconds: float

@router.post("/set-time")
def set_time(req: SetTimeReq):
    global _time_offset; _time_offset = req.offset_seconds
    return {"message": "调试时间已设置", "debug_time": get_debug_time().isoformat()}

@router.get("/time")
def get_time(): return {"offset": _time_offset, "real": datetime.now().isoformat(), "debug": get_debug_time().isoformat()}

@router.post("/reset-time")
def reset_time(): global _time_offset; _time_offset = 0; return {"message": "已重置"}

@router.post("/reset-checkin")
def reset_checkin(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    verify_token(authorization.split(" ")[1])
    n = db.query(Checkin).filter(Checkin.team_id == team_id, Checkin.checkin_date == date.today()).delete()
    db.commit()
    return {"message": f"已清空 {n} 条今日签到记录"}
