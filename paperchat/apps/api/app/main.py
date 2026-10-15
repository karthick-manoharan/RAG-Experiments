"""FastAPI entry point with provider-independent application construction."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chat.router import router
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    application = FastAPI(title=settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    application.include_router(router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
