from fastapi import FastAPI
from .config.settings import settings
from .api import routes_summary, routes_flashcards, routes_assess, routes_homework
from .web.routes import router as web_router

def create_app():
    """
    Application factory to create and configure the FastAPI application.
    """
    app = FastAPI(title=settings.APP_NAME)

    # Include API routers
    app.include_router(routes_summary.router, prefix="/api/v1", tags=["summary"])
    app.include_router(routes_flashcards.router, prefix="/api/v1", tags=["flashcards"])
    app.include_router(routes_assess.router, prefix="/api/v1", tags=["assess"])
    app.include_router(routes_homework.router, prefix="/api/v1", tags=["homework"])

    # Include web router for serving HTML pages
    app.include_router(web_router)

    return app
