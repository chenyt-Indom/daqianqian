"""团队路由：创建团队、加入团队、成员列表"""
import random
import string
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, Team, TeamMember
from routes.auth import verify_token

router = APIRouter(prefix="/api/teams", tags=["teams"])


def generate_invite_code(length=8):
    """生成随机邀请码"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


class CreateTeamRequest(BaseModel):
    name: str


class JoinTeamRequest(BaseModel):
    invite_code: str


class TeamResponse(BaseModel):
    id: int
    name: str
    invite_code: str
    member_count: int

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    joined_at: str

    class Config:
        from_attributes = True


@router.post("/create")
def create_team(
    req: CreateTeamRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """创建团队（需要管理员权限）"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 生成唯一邀请码
    for _ in range(10):
        code = generate_invite_code()
        if not db.query(Team).filter(Team.invite_code == code).first():
            break

    team = Team(name=req.name, invite_code=code, admin_id=user.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    # 创建者自动加入团队
    member = TeamMember(team_id=team.id, user_id=user.id)
    db.add(member)
    db.commit()

    return {
        "id": team.id,
        "name": team.name,
        "invite_code": team.invite_code,
        "admin_id": team.admin_id,
        "member_count": 1
    }


@router.post("/join")
def join_team(
    req: JoinTeamRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """通过邀请码加入团队"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    team = db.query(Team).filter(Team.invite_code == req.invite_code.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="邀请码无效，未找到对应团队")

    # 检查是否已是成员
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="你已经是该团队的成员")

    member = TeamMember(team_id=team.id, user_id=user.id)
    db.add(member)
    db.commit()

    return {"message": f"成功加入团队「{team.name}」", "team_id": team.id, "team_name": team.name}


@router.get("/my")
def get_my_teams(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """获取当前用户所在的团队列表"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    memberships = db.query(TeamMember).filter(
        TeamMember.user_id == payload["user_id"]
    ).all()

    teams = []
    for m in memberships:
        team = db.query(Team).filter(Team.id == m.team_id).first()
        member_count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
        teams.append({
            "id": team.id,
            "name": team.name,
            "invite_code": team.invite_code,
            "admin_id": team.admin_id,
            "member_count": member_count,
            "is_admin": team.admin_id == payload["user_id"]
        })

    return teams


@router.get("/{team_id}/members")
def get_team_members(
    team_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """获取团队成员列表"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    # 检查是否是团队成员
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == payload["user_id"]
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="你不是该团队的成员")

    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        result.append({
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else ""
        })

    return result
