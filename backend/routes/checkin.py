"""签到路由：签到、签退、考勤记录"""
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, Team, TeamMember, Checkin, CheckinStatus
from routes.auth import verify_token

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


class CheckinResponse(BaseModel):
    id: int
    user_id: int
    checkin_date: str
    checkin_time: str | None
    checkout_time: str | None
    status: str


@router.post("/in")
def checkin_in(
    team_id: int = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """每日签到"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    if team_id is None:
        raise HTTPException(status_code=400, detail="请提供团队ID")

    # 检查今日是否已签到
    today = date.today()
    existing = db.query(Checkin).filter(
        Checkin.user_id == payload["user_id"],
        Checkin.team_id == team_id,
        Checkin.checkin_date == today
    ).first()

    if existing and existing.checkin_time:
        raise HTTPException(status_code=400, detail="今日已签到，请勿重复签到")

    now = datetime.now()
    # 判断是否迟到：9:00 之后算迟到
    status = CheckinStatus.late.value if now.hour >= 9 else CheckinStatus.normal.value

    if existing:
        # 已有记录（可能是之前签退过），更新签到时间
        existing.checkin_time = now
        existing.status = status
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "user_id": existing.user_id,
            "checkin_date": str(existing.checkin_date),
            "checkin_time": existing.checkin_time.isoformat(),
            "checkout_time": existing.checkout_time.isoformat() if existing.checkout_time else None,
            "status": existing.status,
            "message": f"签到成功！{'⚠️ 已迟到' if status == 'late' else '✅ 准时签到'}"
        }

    checkin = Checkin(
        user_id=payload["user_id"],
        team_id=team_id,
        checkin_date=today,
        checkin_time=now,
        status=status
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    return {
        "id": checkin.id,
        "user_id": checkin.user_id,
        "checkin_date": str(checkin.checkin_date),
        "checkin_time": checkin.checkin_time.isoformat(),
        "checkout_time": None,
        "status": checkin.status,
        "message": f"签到成功！{'⚠️ 已迟到' if status == 'late' else '✅ 准时签到'}"
    }


@router.post("/out")
def checkin_out(
    team_id: int = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """每日签退"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    if team_id is None:
        raise HTTPException(status_code=400, detail="请提供团队ID")

    today = date.today()
    checkin = db.query(Checkin).filter(
        Checkin.user_id == payload["user_id"],
        Checkin.team_id == team_id,
        Checkin.checkin_date == today
    ).first()

    if not checkin or not checkin.checkin_time:
        raise HTTPException(status_code=400, detail="请先完成签到")

    if checkin.checkout_time:
        raise HTTPException(status_code=400, detail="今日已签退，请勿重复签退")

    now = datetime.now()
    # 判断是否早退：18:00 之前算早退
    if now.hour < 18:
        checkin.status = CheckinStatus.early.value if checkin.status == "normal" else checkin.status

    checkin.checkout_time = now
    db.commit()
    db.refresh(checkin)

    return {
        "id": checkin.id,
        "user_id": checkin.user_id,
        "checkin_date": str(checkin.checkin_date),
        "checkin_time": checkin.checkin_time.isoformat(),
        "checkout_time": checkin.checkout_time.isoformat(),
        "status": checkin.status,
        "message": f"签退成功！{'⚠️ 早退' if checkin.status == 'early' else '✅ 下班愉快'}"
    }


@router.get("/today")
def get_today_status(
    team_id: int = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """获取今日签到状态"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    if team_id is None:
        raise HTTPException(status_code=400, detail="请提供团队ID")

    today = date.today()
    checkin = db.query(Checkin).filter(
        Checkin.user_id == payload["user_id"],
        Checkin.team_id == team_id,
        Checkin.checkin_date == today
    ).first()

    if not checkin:
        return {
            "checked_in": False,
            "checked_out": False,
            "checkin_time": None,
            "checkout_time": None,
            "status": "absent"
        }

    return {
        "checked_in": checkin.checkin_time is not None,
        "checked_out": checkin.checkout_time is not None,
        "checkin_time": checkin.checkin_time.isoformat() if checkin.checkin_time else None,
        "checkout_time": checkin.checkout_time.isoformat() if checkin.checkout_time else None,
        "status": checkin.status
    }


@router.get("/records")
def get_my_records(
    team_id: int = None,
    year: int = None,
    month: int = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """获取个人考勤记录"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    query = db.query(Checkin).filter(Checkin.user_id == payload["user_id"])
    if team_id:
        query = query.filter(Checkin.team_id == team_id)

    records = query.order_by(Checkin.checkin_date.desc()).all()

    # 按年月过滤
    result = []
    for r in records:
        if year and r.checkin_date.year != year:
            continue
        if month and r.checkin_date.month != month:
            continue
        result.append({
            "id": r.id,
            "checkin_date": str(r.checkin_date),
            "checkin_time": r.checkin_time.isoformat() if r.checkin_time else None,
            "checkout_time": r.checkout_time.isoformat() if r.checkout_time else None,
            "status": r.status
        })

    return result


@router.get("/team-records")
def get_team_records(
    team_id: int = None,
    date_filter: str = None,  # YYYY-MM-DD
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """获取团队考勤记录（管理员/团队成员）"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    if team_id is None:
        raise HTTPException(status_code=400, detail="请提供团队ID")

    # 检查是否是团队成员
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == payload["user_id"]
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="你不是该团队的成员")

    query = db.query(Checkin).filter(Checkin.team_id == team_id)

    if date_filter:
        try:
            d = date.fromisoformat(date_filter)
            query = query.filter(Checkin.checkin_date == d)
        except ValueError:
            pass

    records = query.order_by(Checkin.checkin_date.desc()).all()
    result = []
    for r in records:
        user = db.query(User).filter(User.id == r.user_id).first()
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "display_name": user.display_name if user else "未知",
            "checkin_date": str(r.checkin_date),
            "checkin_time": r.checkin_time.isoformat() if r.checkin_time else None,
            "checkout_time": r.checkout_time.isoformat() if r.checkout_time else None,
            "status": r.status
        })

    return result


@router.get("/stats")
def get_stats(
    team_id: int = None,
    month: str = None,  # YYYY-MM
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """获取考勤统计数据"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ")[1]
    payload = verify_token(token)

    if team_id is None:
        raise HTTPException(status_code=400, detail="请提供团队ID")

    if month is None:
        now = datetime.now()
        month = f"{now.year}-{now.month:02d}"

    try:
        y, m = month.split("-")
        y, m = int(y), int(m)
    except ValueError:
        raise HTTPException(status_code=400, detail="月份格式错误，请使用 YYYY-MM")

    records = db.query(Checkin).filter(
        Checkin.user_id == payload["user_id"],
        Checkin.team_id == team_id
    ).all()

    total = 0
    normal = 0
    late = 0
    early = 0
    absent = 0

    for r in records:
        if r.checkin_date.year == y and r.checkin_date.month == m:
            total += 1
            if r.status == "normal":
                normal += 1
            elif r.status == "late":
                late += 1
            elif r.status == "early":
                early += 1
            elif r.status == "absent":
                absent += 1

    return {
        "month": month,
        "total_days": total,
        "normal": normal,
        "late": late,
        "early": early,
        "absent": absent
    }
