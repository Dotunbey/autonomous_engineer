import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routes import tasks, workspace  # Added workspace import

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    Factory function to initialize and configure the FastAPI application.
    """
    app = FastAPI(
        title="Autonomous Engineering API",
        description="API for managing the AI software engineering platform.",
        version="40.0.0",
    )

    # Configure CORS for potential frontend (UI) integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
    # Register the new workspace router so we can read files
    app.include_router(workspace.router, prefix="/api/v1/workspace", tags=["Workspace"])

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catches any unhandled exceptions and returns a standardized JSON error.
        """
        logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "details": str(exc)},
        )

    @app.get("/health", tags=["System"])
    async def health_check() -> dict:
        """
        Simple health check endpoint for load balancers and deployment probes.
        """
        return {"status": "healthy", "version": "40.0.0"}

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)