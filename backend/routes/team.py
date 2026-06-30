"""团队路由"""
import random, string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, Team, TeamMember, JoinRequest, Mailbox
from routes.auth import verify_token

router = APIRouter(prefix="/api/team", tags=["team"])

def _gen_code(length=8) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@router.get("/list")
def team_list(authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    memberships = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()
    teams_data = []
    for m in memberships:
        t = db.query(Team).filter(Team.id == m.team_id).first()
        if t:
            teams_data.append({
                "id": t.id, "name": t.name, "invite_code": t.invite_code,
                "admin_invite_code": t.admin_invite_code,
                "is_admin": t.admin_id == user_id, "member_count": db.query(TeamMember).filter(TeamMember.team_id == t.id).count()
            })
    return teams_data

class CreateTeamRequest(BaseModel):
    name: str

@router.post("/create")
def create_team(req: CreateTeamRequest, authorization: str = Header(None), db: Session = Depends(get_db)):
    payload = verify_token(authorization.split(" ")[1])
    user_id = payload["user_id"]
    team = Team(name=req.name, invite_code=_gen_code(6), admin_invite_code=_gen_code(8), admin_id=user_id)
    db.add(team); db.commit(); db.refresh(team)
    db.add(TeamMember(team_id=team.id, user_id=user_id, join_type="admin"))
    db.commit()
    return {"id": team.id, "name": team.name, "invite_code": team.invite_code, "admin_invite_code": team.admin_invite_code}

class JoinRequest(BaseModel):
    invite_code: str

@router.post("/join")
def join_team(req: JoinRequest, authorization: str = Header(None), db: Session = Depends(get_db)):
    payload = verify_token(authorization.split(" ")[1])
    user_id = payload["user_id"]
    # 先检查管理员邀请码
    team = db.query(Team).filter(Team.admin_invite_code == req.invite_code).first()
    if team:
        return _direct_join(db, team, user_id)
    # 普通邀请码
    team = db.query(Team).filter(Team.invite_code == req.invite_code).first()
    if not team:
        raise HTTPException(400, "邀请码无效")
    return _direct_join(db, team, user_id)

def _direct_join(db, team, user_id):
    existing = db.query(TeamMember).filter(TeamMember.team_id == team.id, TeamMember.user_id == user_id).first()
    if existing:
        raise HTTPException(400, "已是团队成员")
    db.add(TeamMember(team_id=team.id, user_id=user_id, join_type="admin"))
    db.commit()
    return {"message": "成功加入团队", "team_id": team.id, "team_name": team.name}

@router.get("/members")
def team_members(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    verify_token(authorization.split(" ")[1])
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    return [{"user_id": m.user_id, "display_name": db.query(User).filter(User.id == m.user_id).first().display_name, "username": db.query(User).filter(User.id == m.user_id).first().username, "role": db.query(User).filter(User.id == m.user_id).first().role, "join_type": m.join_type} for m in members]

@router.get("/pending-requests")
def pending_requests(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    verify_token(authorization.split(" ")[1])
    return db.query(JoinRequest).filter(JoinRequest.team_id == team_id, JoinRequest.status == "pending").all()

@router.post("/approve-join")
def approve_join(team_id: int, user_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    verify_token(authorization.split(" ")[1])
    req = db.query(JoinRequest).filter(JoinRequest.team_id == team_id, JoinRequest.user_id == user_id, JoinRequest.status == "pending").first()
    if not req:
        raise HTTPException(404, "申请不存在")
    req.status = "approved"
    db.add(TeamMember(team_id=team_id, user_id=user_id, join_type="code"))
    db.commit()
    return {"message": "已批准加入"}
