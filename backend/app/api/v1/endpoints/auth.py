from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud import user as crud_user
from app.core import security
from app.core.rate_limit import limiter
from app.schemas import token as schema_token
from app.schemas import user as schema_user
from app.api import deps

router = APIRouter()

@router.post("/token", response_model=schema_token.Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    username = str(form_data.username or "").strip()
    user = await crud_user.authenticate(db, username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(
        data={"sub": user.login, "role": user.role.value, "user_id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schema_user.UserOut)
async def get_me(
    current_user=Depends(deps.get_current_active_user),
):
    return current_user
