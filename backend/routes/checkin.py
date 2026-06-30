"""签到路由 — 含完整量化分计算"""
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel

from database import get_db
from models import User, Team, TeamMember, Checkin, CheckinStatus, UserScore, ScoreRecord
from routes.auth import verify_token

router = APIRouter(prefix="/api/checkin", tags=["checkin"])

# ===== 时间常量 =====
MAX_SCORE = 60               # 量化分上限
INITIAL_SCORE = 60           # 初始分数
AM_OPEN_H, AM_OPEN_M = 6, 0     # 上午开始 6:00
AM_CLOSE_H, AM_CLOSE_M = 12, 30 # 上午签到截止 12:30
AM_CHECKOUT_LATEST_H = 13       # 上午签退最晚 13:00
PM_OPEN_H, PM_OPEN_M = 13, 0    # 下午开始 13:00
PM_CLOSE_H, PM_CLOSE_M = 19, 0  # 下午结束 19:00
CLOSED_H = 6                    # 0:00-6:00 关闭

# ===== 量化分工具 =====
def _get_score(db: Session, team_id: int, user_id: int) -> int:
    s = db.query(UserScore).filter(and_(UserScore.team_id == team_id, UserScore.user_id == user_id)).first()
    return s.score if s else INITIAL_SCORE

def _set_score(db: Session, team_id: int, user_id: int, user_score: int):
    s = db.query(UserScore).filter(and_(UserScore.team_id == team_id, UserScore.user_id == user_id)).first()
    if not s:
        s = UserScore(team_id=team_id, user_id=user_id, score=user_score)
        db.add(s)
    else:
        s.score = user_score

def _add_score(db: Session, team_id: int, user_id: int, operator_id: int, change: int, reason: str):
    """加减量化分，返回新分数和实际变动值"""
    if change == 0: return _get_score(db, team_id, user_id)
    current = _get_score(db, team_id, user_id)
    new_score = current + change
    if new_score > MAX_SCORE: new_score = MAX_SCORE
    if new_score < 0: new_score = 0
    actual_change = new_score - current
    if actual_change == 0: return current
    _set_score(db, team_id, user_id, new_score)
    db.add(ScoreRecord(team_id=team_id, user_id=user_id, operator_id=operator_id, score_change=actual_change, reason=reason, score_after=new_score, created_at=datetime.utcnow()))
    db.commit()
    return new_score

# ===== 签到分数计算 =====
def _calc_checkin_score(t: datetime, base_hour: int) -> int:
    """上午签到 base=8，下午签到 base=14"""
    mins = t.hour * 60 + t.minute
    base = base_hour * 60
    diff = mins - base  # 正值=迟到，负值=早到
    if base_hour == 8:  # 上午：早到加分，迟到扣分
        if diff <= -31: return 3
        elif diff <= -11: return 2
        elif diff <= -1: return 1
        elif diff <= 0: return 0
        elif diff <= 10: return -1
        elif diff <= 30: return -3
        else: return -5
    else:  # 下午：只有迟到扣分
        if diff <= 0: return 0
        elif diff <= 10: return -1
        elif diff <= 30: return -3
        else: return -5

def _calc_checkout_score(t: datetime, base_hour: int) -> int:
    """签退：早退扣分"""
    mins = t.hour * 60 + t.minute
    base = base_hour * 60
    diff = base - mins  # 正值=早退
    if diff <= 0: return 0
    elif diff <= 30: return -2
    else: return -5

def _is_closed() -> bool:
    """0:00-6:00 关闭"""
    return datetime.now().hour < CLOSED_H

def _can_am_checkin() -> bool:
    if _is_closed(): return False
    now = datetime.now()
    t = now.hour * 60 + now.minute
    return AM_OPEN_H * 60 + AM_OPEN_M <= t <= AM_CLOSE_H * 60 + AM_CLOSE_M

def _can_pm_checkin() -> bool:
    if _is_closed(): return False
    now = datetime.now()
    t = now.hour * 60 + now.minute
    return PM_OPEN_H * 60 + PM_OPEN_M <= t <= PM_CLOSE_H * 60 + PM_CLOSE_M

def _can_am_checkout() -> bool:
    if _is_closed(): return False
    now = datetime.now()
    t = now.hour * 60 + now.minute
    return AM_OPEN_H * 60 + AM_OPEN_M <= t <= AM_CHECKOUT_LATEST_H * 60

def _can_pm_checkout() -> bool:
    if _is_closed(): return False
    now = datetime.now()
    t = now.hour * 60 + now.minute
    return PM_OPEN_H * 60 + PM_OPEN_M <= t <= PM_CLOSE_H * 60 + PM_CLOSE_M

def _get_today_record(db: Session, user_id: int, team_id: int):
    return db.query(Checkin).filter(and_(Checkin.user_id == user_id, Checkin.team_id == team_id, Checkin.checkin_date == date.today())).first()

# ===== API =====
class DailyRecord(BaseModel):
    checkin_date: str
    am: dict | None = None
    pm: dict | None = None
    display_name: str = ""

@router.post("/am-in")
def do_am_checkin(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未提供认证令牌")
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    if not _can_am_checkin():
        raise HTTPException(400, "当前不在上午签到时间范围内（6:00-12:30）")
    rec = _get_today_record(db, user_id, team_id)
    if not rec:
        rec = Checkin(user_id=user_id, team_id=team_id, checkin_date=date.today())
        db.add(rec); db.commit(); db.refresh(rec)
    if rec.am_checkin_time:
        raise HTTPException(400, "今日已签上午到")
    now = datetime.now()
    rec.am_checkin_time = now
    if now.hour * 60 + now.minute > 8 * 60:
        rec.am_status = CheckinStatus.late.value
    else:
        rec.am_status = CheckinStatus.normal.value
    db.commit()
    sc = _calc_checkin_score(now, 8)
    reason = f"上午签到 {'提前' + str(abs(sc)) + '分钟' if sc > 0 else '迟到' + str(abs(sc)) + '分钟'}"
    _add_score(db, team_id, user_id, user_id, sc, reason)
    return {"message": "上午签到成功", "time": now.isoformat(), "score_change": sc}

@router.post("/am-out")
def do_am_checkout(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未提供认证令牌")
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    if not _can_am_checkout():
        raise HTTPException(400, "当前不在签退时间范围内")
    rec = _get_today_record(db, user_id, team_id)
    if not rec or not rec.am_checkin_time:
        raise HTTPException(400, "请先完成上午签到")
    if rec.am_checkout_time:
        raise HTTPException(400, "今日已签上午退")
    now = datetime.now()
    rec.am_checkout_time = now
    sc = 0
    # 超时检查：>13:00
    if now.hour >= AM_CHECKOUT_LATEST_H:
        rec.am_status = CheckinStatus.overdue_am.value
        sc = -1
        reason = "上午签退超时（>13:00），扣1分"
    else:
        sc = _calc_checkout_score(now, 12)
        reason = f"上午签退 {'早退' + str(abs(sc)) + '分钟' if sc < 0 else '正常'}"
    db.commit()
    _add_score(db, team_id, user_id, user_id, sc, reason)
    return {"message": "上午签退成功", "time": now.isoformat(), "score_change": sc}

@router.post("/pm-in")
def do_pm_checkin(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未提供认证令牌")
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    if not _can_pm_checkin():
        raise HTTPException(400, "当前不在下午签到时间范围内（13:00-19:00）")
    rec = _get_today_record(db, user_id, team_id)
    if not rec:
        rec = Checkin(user_id=user_id, team_id=team_id, checkin_date=date.today())
        db.add(rec); db.commit(); db.refresh(rec)
    if rec.pm_checkin_time:
        raise HTTPException(400, "今日已签下午到")
    now = datetime.now()
    rec.pm_checkin_time = now
    if now.hour * 60 + now.minute > 14 * 60:
        rec.pm_status = CheckinStatus.late_pm.value
    else:
        rec.pm_status = CheckinStatus.normal.value
    db.commit()
    sc = _calc_checkin_score(now, 14)
    reason = f"下午签到 {'迟到' + str(abs(sc)) + '分钟' if sc < 0 else '准时'}"
    _add_score(db, team_id, user_id, user_id, sc, reason)
    return {"message": "下午签到成功", "time": now.isoformat(), "score_change": sc}

@router.post("/pm-out")
def do_pm_checkout(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未提供认证令牌")
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    if not _can_pm_checkout():
        raise HTTPException(400, "当前不在签退时间范围内")
    rec = _get_today_record(db, user_id, team_id)
    if not rec or not rec.pm_checkin_time:
        raise HTTPException(400, "请先完成下午签到")
    if rec.pm_checkout_time:
        raise HTTPException(400, "今日已签下午退")
    now = datetime.now()
    rec.pm_checkout_time = now
    db.commit()
    sc = _calc_checkout_score(now, 18)
    reason = f"下午签退 {'早退' + str(abs(sc)) + '分钟' if sc < 0 else '正常'}"
    _add_score(db, team_id, user_id, user_id, sc, reason)
    return {"message": "下午签退成功", "time": now.isoformat(), "score_change": sc}

@router.get("/status")
def checkin_status(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未提供认证令牌")
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    rec = _get_today_record(db, user_id, team_id)
    return {
        "can_am_in": _can_am_checkin() and (not rec or not rec.am_checkin_time),
        "can_am_out": _can_am_checkout() and bool(rec and rec.am_checkin_time and not rec.am_checkout_time),
        "can_pm_in": _can_pm_checkin() and (not rec or not rec.pm_checkin_time),
        "can_pm_out": _can_pm_checkout() and bool(rec and rec.pm_checkin_time and not rec.pm_checkout_time),
        "is_closed": _is_closed(),
        "today": date.today().isoformat(),
        "record": {
            "am_in": rec.am_checkin_time.isoformat() if rec and rec.am_checkin_time else None,
            "am_out": rec.am_checkout_time.isoformat() if rec and rec.am_checkout_time else None,
            "am_status": rec.am_status if rec else "absent",
            "pm_in": rec.pm_checkin_time.isoformat() if rec and rec.pm_checkin_time else None,
            "pm_out": rec.pm_checkout_time.isoformat() if rec and rec.pm_checkout_time else None,
            "pm_status": rec.pm_status if rec else "absent",
        } if rec else None
    }

@router.get("/today")
def team_today(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    verify_token(authorization.split(" ")[1])
    records = db.query(Checkin).filter(and_(Checkin.team_id == team_id, Checkin.checkin_date == date.today())).all()
    result = []
    for r in records:
        u = db.query(User).filter(User.id == r.user_id).first()
        result.append({
            "checkin_date": r.checkin_date.isoformat(),
            "display_name": u.display_name if u else "",
            "am": {"time_in": r.am_checkin_time.isoformat() if r.am_checkin_time else None, "time_out": r.am_checkout_time.isoformat() if r.am_checkout_time else None, "status": r.am_status},
            "pm": {"time_in": r.pm_checkin_time.isoformat() if r.pm_checkin_time else None, "time_out": r.pm_checkout_time.isoformat() if r.pm_checkout_time else None, "status": r.pm_status},
        })
    return result

@router.get("/my-records")
def my_records(team_id: int, month: str = None, authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    query = db.query(Checkin).filter(and_(Checkin.user_id == user_id, Checkin.team_id == team_id))
    if month:
        query = query.filter(Checkin.checkin_date.like(f"{month}%"))
    records = query.order_by(Checkin.checkin_date.desc()).all()
    return [{
        "checkin_date": r.checkin_date.isoformat(),
        "am": {"time_in": r.am_checkin_time.isoformat() if r.am_checkin_time else None, "time_out": r.am_checkout_time.isoformat() if r.am_checkout_time else None, "status": r.am_status},
        "pm": {"time_in": r.pm_checkin_time.isoformat() if r.pm_checkin_time else None, "time_out": r.pm_checkout_time.isoformat() if r.pm_checkout_time else None, "status": r.pm_status},
    } for r in records]

# ===== 量化分 API =====
@router.get("/scores")
def team_scores(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    verify_token(authorization.split(" ")[1])
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        sc = _get_score(db, team_id, m.user_id)
        result.append({"user_id": m.user_id, "display_name": u.display_name if u else "", "score": sc})
    result.sort(key=lambda x: x["score"], reverse=True)
    return result

@router.get("/my-score")
def my_score(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    user_id = verify_token(authorization.split(" ")[1])["user_id"]
    return {"score": _get_score(db, team_id, user_id)}

@router.get("/score-records")
def score_records(team_id: int, authorization: str = Header(None), db: Session = Depends(get_db)):
    verify_token(authorization.split(" ")[1])
    records = db.query(ScoreRecord).filter(ScoreRecord.team_id == team_id).order_by(ScoreRecord.created_at.desc()).all()
    result = []
    for r in records:
        u = db.query(User).filter(User.id == r.user_id).first()
        result.append({"user_id": r.user_id, "display_name": u.display_name if u else "", "score_change": r.score_change, "reason": r.reason, "score_after": r.score_after, "created_at": r.created_at.isoformat()})
    return result

class ManualScoreRequest(BaseModel):
    team_id: int
    user_id: int
    score_change: int
    reason: str = "管理员操作"

@router.post("/manual-score")
def manual_score(req: ManualScoreRequest, authorization: str = Header(None), db: Session = Depends(get_db)):
    payload = verify_token(authorization.split(" ")[1])
    if payload["role"] != "admin":
        raise HTTPException(403, "仅管理员可操作")
    new_score = _add_score(db, req.team_id, req.user_id, payload["user_id"], req.score_change, req.reason)
    return {"message": "操作成功", "new_score": new_score}
