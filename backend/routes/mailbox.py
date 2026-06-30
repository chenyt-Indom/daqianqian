"""信箱路由"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User, Team, TeamMember, Mailbox
from routes.auth import verify_token

router = APIRouter(prefix="/api/mailbox", tags=["mailbox"])

@router.get("/list")
def list_msgs(authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    msgs = db.query(Mailbox).filter(Mailbox.receiver_id == user_id).order_by(Mailbox.created_at.desc()).all()
    return [{"id": m.id, "team_id": m.team_id, "sender_name": (db.query(User).filter(User.id == m.sender_id).first().display_name if db.query(User).filter(User.id == m.sender_id).first() else ""), "msg_type": m.msg_type, "title": m.title, "content": m.content, "is_read": m.is_read, "created_at": m.created_at.isoformat()} for m in msgs]

@router.get("/unread")
def unread_cnt(authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    return {"unread": db.query(Mailbox).filter(Mailbox.receiver_id == user_id, Mailbox.is_read == "False").count()}

@router.post("/read")
def read_msg(msg_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    m = db.query(Mailbox).filter(Mailbox.id == msg_id, Mailbox.receiver_id == user_id).first()
    if not m: raise HTTPException(404, "消息不存在")
    m.is_read = "True"; db.commit()
    return {"message": "已读"}

@router.post("/read-all")
def read_all(authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    db.query(Mailbox).filter(Mailbox.receiver_id == user_id, Mailbox.is_read == "False").update({"is_read": "True"})
    db.commit()
    return {"message": "已全部标记已读"}

@router.post("/delete")
def del_msg(msg_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    m = db.query(Mailbox).filter(Mailbox.id == msg_id, Mailbox.receiver_id == user_id).first()
    if not m: raise HTTPException(404, "消息不存在")
    db.delete(m); db.commit()
    return {"message": "已删除"}

class SendReportReq(BaseModel):
    team_id: int; title: str; content: str

@router.post("/report")
def send_report(req: SendReportReq, authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    team = db.query(Team).filter(Team.id == req.team_id).first()
    if not team: raise HTTPException(404, "团队不存在")
    db.add(Mailbox(team_id=req.team_id, sender_id=user_id, receiver_id=team.admin_id, msg_type="report", title=req.title, content=req.content, is_read="False", created_at=datetime.utcnow()))
    db.commit()
    return {"message": "报告已发送"}

class AnnounceReq(BaseModel):
    team_id: int; title: str; content: str

@router.post("/announcement")
def send_announce(req: AnnounceReq, authorization: str = Header(None), db: Session = Depends(get_db)):
    payload = verify_token(authorization.split(" ")[1])
    team = db.query(Team).filter(Team.id == req.team_id).first()
    if not team or team.admin_id != payload["user_id"]: raise HTTPException(403, "仅管理员")
    members = db.query(TeamMember).filter(TeamMember.team_id == req.team_id, TeamMember.user_id != payload["user_id"]).all()
    for m in members:
        db.add(Mailbox(team_id=req.team_id, sender_id=payload["user_id"], receiver_id=m.user_id, msg_type="announcement", title=req.title, content=req.content, is_read="False", created_at=datetime.utcnow()))
    db.commit()
    return {"message": f"公告已发送给 {len(members)} 位成员"}
