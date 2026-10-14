from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.auth import valid_credentials
from app.settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/mode")
def mode() -> dict[str, bool]:
    return {"bypass": get_settings().dev_auth_bypass}


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(payload: LoginRequest, request: Request) -> Response:
    settings = get_settings()
    if not settings.dev_auth_bypass and not valid_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    request.session["username"] = settings.admin_username if settings.dev_auth_bypass else payload.username
    return Response(status_code=status.HTTP_204_NO_CONTENT)
