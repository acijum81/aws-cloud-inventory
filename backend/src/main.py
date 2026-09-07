from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from presentation.api.routes.catalog import router as catalog_router
from presentation.api.routes.comparison import router as comparison_router
from presentation.api.routes.health import router as health_router
from presentation.api.routes.inventory import router as inventory_router
from presentation.api.routes.resources import router as resources_router

app = FastAPI(title="AWS Cloud Inventory", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
app.include_router(resources_router)
app.include_router(inventory_router)
app.include_router(comparison_router)
app.include_router(catalog_router)
