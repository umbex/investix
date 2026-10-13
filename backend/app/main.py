from fastapi import Depends, FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api.auth import router as auth_router
from app.auth import require_session
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    application.add_middleware(SessionMiddleware, secret_key=settings.session_secret, https_only=False)
    application.include_router(auth_router)

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/api/portfolio")
    def portfolio(_: str = Depends(require_session)) -> dict[str, str]:
        return {"status": "placeholder"}

    return application

app = create_app()
