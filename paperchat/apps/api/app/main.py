"""FastAPI entry point."""

from fastapi import FastAPI

from app.chat.router import router
from app.settings import Settings

app = FastAPI(title=Settings().app_name)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
