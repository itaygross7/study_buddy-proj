from .app_factory import create_app
import uvicorn
from .config.settings import settings

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=settings.LOG_LEVEL.lower())
