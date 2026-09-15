import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from presentation.api.routes.catalog import router as catalog_router
from presentation.api.routes.comparison import router as comparison_router
from presentation.api.routes.health import router as health_router
from presentation.api.routes.inventory import router as inventory_router
from presentation.api.routes.resources import router as resources_router

def _cors_origins() -> list[str]:
    origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    return [origin.strip() for origin in origins if origin.strip()]


docs_enabled = os.getenv("EXPOSE_API_DOCS", "false").lower() == "true"
app = FastAPI(
    title="AWS Cloud Inventory",
    version="1.0.0",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                body_size = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
            if body_size > 65_536:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response
app.include_router(health_router)
app.include_router(resources_router)
app.include_router(inventory_router)
app.include_router(comparison_router)
app.include_router(catalog_router)
