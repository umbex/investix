from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.auth import valid_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(payload: LoginRequest, request: Request) -> Response:
    if not valid_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide")
    request.session["username"] = payload.username
    return Response(status_code=status.HTTP_204_NO_CONTENT)
