from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router
from app.api.v1.nl_agents import router as nl_agents_router
from app.api.v1.run import router as run_router
from app.api.v1.tools import router as tools_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # TODO: add startup actions (e.g., connect to database)
    yield
    # TODO: add shutdown actions (e.g., disconnect from database)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="Kgents (Agent-as-a-Service) Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # update with specific origins in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(agents_router, prefix="/agents", tags=["agents"])
    app.include_router(tools_router, prefix="/tools", tags=["tools"])
    app.include_router(nl_agents_router, prefix="/nl-agents", tags=["nl_agents"])
    app.include_router(run_router, prefix="/run", tags=["run"])

    @app.get("/", tags=["root"])
    async def root() -> dict:
        """Root endpoint returning a welcome message."""
        return {"message": "Welcome to the Kgents (Agent-as-a-Service) Platform"}

    return app


app = create_app()
