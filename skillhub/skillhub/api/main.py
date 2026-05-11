from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

    @app.get("/.well-known/skillhub.json")
    def well_known(request: Request) -> JSONResponse:
        base = str(request.base_url).rstrip("/")
        return JSONResponse(
            {
                "service": "skillhub",
                "version": "0.1.0",
                "spec": "skillhub/v0",
                "base_url": base,
                "auth": {
                    "schemes": ["bearer"],
                    "bearer": {
                        "header": "Authorization",
                        "prefix": "Bearer ",
                        "obtain": f"{base}/connect",
                    },
                },
                "scopes": ["read", "install", "submit"],
                "endpoints": {
                    "whoami": f"{base}/api/whoami",
                    "connector_me": f"{base}/api/connectors/me",
                    "list_entries": f"{base}/api/entries",
                    "get_entry": f"{base}/api/entries/{{namespace}}/{{name}}",
                    "get_payload": f"{base}/api/entries/{{namespace}}/{{name}}/payload",
                    "submit_entry": f"{base}/api/entries",
                    "namespaces": f"{base}/api/namespaces",
                },
                "kinds": ["skill", "mcp_server"],
                "manifest_schema": "skillhub/v0",
            }
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("skillhub.api.main:app", host="0.0.0.0", port=8765, reload=False)


if __name__ == "__main__":
    run()
