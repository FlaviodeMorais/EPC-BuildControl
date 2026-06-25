"""Autenticação JWT."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from jose import jwt
from pydantic import BaseModel
from ...database import get_db
from ...config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


def _make_token(user_id: int, role: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp},
                      settings.secret_key, algorithm="HS256")


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    import hashlib
    row = db.execute(
        text("SELECT id, password_hash, role FROM users WHERE email = :e AND is_active = true"),
        {"e": body.email}
    ).mappings().first()
    if not row:
        raise HTTPException(401, "Credenciais inválidas")
    pw_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if pw_hash != row["password_hash"]:
        raise HTTPException(401, "Credenciais inválidas")
    return {"access_token": _make_token(row["id"], row["role"]), "token_type": "bearer"}


@router.post("/register-first-admin")
def register_first_admin(body: LoginRequest, db: Session = Depends(get_db)):
    """Cria o primeiro admin — só funciona se não houver usuários."""
    import hashlib
    count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
    if count > 0:
        raise HTTPException(403, "Já existem usuários cadastrados")
    pw_hash = hashlib.sha256(body.password.encode()).hexdigest()
    db.execute(text("""
        INSERT INTO users (email, full_name, password_hash, role)
        VALUES (:e, 'Admin', :pw, 'ADMIN')
    """), {"e": body.email, "pw": pw_hash})
    db.commit()
    return {"message": "Admin criado com sucesso"}
