from fastapi import Depends, FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.imports import router as imports_router
from app.api.operations import router as operations_router
from app.api.portfolio import router as portfolio_router
from app.api.performance import router as performance_router
from app.auth import require_session
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    application.add_middleware(SessionMiddleware, secret_key=settings.session_secret, https_only=False)
    application.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    application.include_router(auth_router)
    application.include_router(imports_router)
    application.include_router(operations_router)
    application.include_router(portfolio_router)
    application.include_router(performance_router)

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application

app = create_app()
