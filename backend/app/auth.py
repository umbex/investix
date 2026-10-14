import hmac

from fastapi import HTTPException, Request, status

from app.settings import get_settings


def require_session(request: Request) -> str:
    settings = get_settings()
    if settings.dev_auth_bypass:
        return settings.admin_username
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticazione richiesta")
    return username


def valid_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    return bool(settings.admin_password) and hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(password, settings.admin_password)
