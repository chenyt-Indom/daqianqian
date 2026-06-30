"""认证路由 — 验证码注册、密码登录"""
import re, random, time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from passlib.context import CryptContext
from jose import JWTError, jwt

from database import get_db
from models import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "qianqiandao-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
verification_codes: dict = {}

# ===== 验证器 =====
def validate_password(p: str) -> str | None:
    if len(p) < 8: return "密码长度至少8位"
    if not re.search(r'[A-Z]', p): return "密码必须包含大写字母"
    if not re.search(r'[a-z]', p): return "密码必须包含小写字母"
    if not re.search(r'[0-9]', p): return "密码必须包含数字"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/\'`~]', p): return "密码必须包含特殊符号"
    return None

def validate_phone(p: str) -> str | None:
    if not re.match(r'^1[3-9]\d{9}$', p): return "请输入有效的11位手机号"
    return None

# ===== 请求/响应模型 =====
class SendCodeRequest(BaseModel):
    phone: str
    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        e = validate_phone(v)
        if e: raise ValueError(e)
        return v

class RegisterRequest(BaseModel):
    phone: str
    code: str
    password: str
    display_name: str
    role: str = "employee"
    @field_validator("password")
    @classmethod
    def check_pwd(cls, v):
        e = validate_password(v)
        if e: raise ValueError(e)
        return v
    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        e = validate_phone(v)
        if e: raise ValueError(e)
        return v

class LoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    display_name: str
    role: str

# ===== JWT =====
def create_access_token(data: dict) -> str:
    d = data.copy()
    d.update({"exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)})
    return jwt.encode(d, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try: return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "无效的认证令牌")

# ===== 验证码 =====
def generate_code() -> str:
    return str(random.randint(100000, 999999))

def verify_code(phone: str, code: str) -> bool:
    d = verification_codes.get(phone)
    if not d: return False
    if time.time() > d["expires_at"]:
        del verification_codes[phone]; return False
    if d["code"] != code: return False
    del verification_codes[phone]
    return True

# ===== API =====
@router.post("/send-code")
def send_code(req: SendCodeRequest):
    existing = verification_codes.get(req.phone)
    if existing and time.time() - (existing["expires_at"] - 300) < 60:
        remaining = 60 - int(time.time() - (existing["expires_at"] - 300))
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"请{remaining}秒后再试")
    code = generate_code()
    verification_codes[req.phone] = {"code": code, "expires_at": time.time() + 300}
    print(f"\n[到签签] 验证码 {req.phone}: {code}\n")
    return {"message": "验证码已发送", "expires_in": 300, "debug_code": code}

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if not verify_code(req.phone, req.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码错误或已过期")
    if db.query(User).filter(User.username == req.phone).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该手机号已注册")
    if req.role not in [r.value for r in UserRole]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无效的角色类型")
    user = User(username=req.phone, password_hash=pwd_context.hash(req.password), display_name=req.display_name, role=req.role)
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token({"sub": user.username, "user_id": user.id, "role": user.role})
    return TokenResponse(access_token=token, user_id=user.id, username=user.username, display_name=user.display_name, role=user.role)

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.phone).first()
    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "手机号或密码错误")
    token = create_access_token({"sub": user.username, "user_id": user.id, "role": user.role})
    return TokenResponse(access_token=token, user_id=user.id, username=user.username, display_name=user.display_name, role=user.role)
