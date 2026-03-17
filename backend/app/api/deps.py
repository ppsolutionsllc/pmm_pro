from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud import user as crud_user
from app.core import security

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    payload = security.decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login: str = payload.get("sub")
    user = await crud_user.get_user_by_login(db, login)
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")
    return user

async def get_current_active_user(current_user=Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_role(role: str):
    async def _role_checker(current_user=Depends(get_current_active_user)):
        if current_user.role.value != role:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
    return _role_checker


def require_any_role(roles: list[str]):
    async def _checker(current_user=Depends(get_current_active_user)):
        if current_user.role.value not in roles:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
    return _checker
