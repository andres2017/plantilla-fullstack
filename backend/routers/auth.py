from fastapi import APIRouter, Depends, HTTPException, Request, Response

from core.rate_limit import rate_limiter
from core.responses import success_response
from core.security import get_current_user, set_auth_cookies, clear_auth_cookies
from models.user import UserRegister, UserLogin
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


_register_rate_limit = Depends(rate_limiter("register", max_attempts=5, window_minutes=15))


@router.post("/register", status_code=201, dependencies=[_register_rate_limit])
async def register(data: UserRegister, response: Response):
    user, access, refresh = await auth_service.register(data)
    set_auth_cookies(response, access, refresh)
    return success_response(user)


@router.post("/login")
async def login(data: UserLogin, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    user, access, refresh = await auth_service.login(data.email, data.password, ip)
    set_auth_cookies(response, access, refresh)
    return success_response(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No hay refresh token")
    access, new_refresh = await auth_service.refresh_tokens(token)
    set_auth_cookies(response, access, new_refresh)
    return success_response({"refreshed": True})


@router.post("/logout")
async def logout(request: Request, response: Response):
    await auth_service.logout(request.cookies.get("refresh_token"))
    clear_auth_cookies(response)
    return success_response({"logged_out": True})


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return success_response({"id": user["_id"], "email": user["email"],
                             "name": user["name"], "role": user["role"]})
