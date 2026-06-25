"""Dependências FastAPI: sessão DB, usuário autenticado, controle de role."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import settings

bearer = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=["HS256"])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc
    return {"id": user_id, "role": payload.get("role")}


def require_role(*roles: str):
    def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Sem permissão")
        return user
    return checker
