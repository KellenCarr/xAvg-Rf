from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from skillhub.api.routes_registry import router as api_router
from skillhub.api.routes_web import router as web_router


def create_app() -> FastAPI:
    app = FastAPI(title="SkillHub", version="0.1.0")
    static_dir = Path(__file__).resolve().parent.parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(api_router)
    app.include_router(web_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("skillhub.api.main:app", host="0.0.0.0", port=8765, reload=False)


if __name__ == "__main__":
    run()
