from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, lobby # Assuming 'lobby' is where your game/room routers are
from business.database_operations import create_postgresql_tables
import os

# Import get_swagger_ui_html for custom docs_url
from fastapi.openapi.docs import get_swagger_ui_html


app = FastAPI(
    title="Game Platform Application API",
    description="This is the backend service of our Game Platform Application",
    version="0.0.1",
    # Disable default docs_url and redoc_url so we can provide a custom one
    docs_url=None,
    redoc_url=None,
)

# Set CORS policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    print("FastAPI startup event triggered: Calling create_postgresql_tables()...")
    create_postgresql_tables()
    print("Database tables creation check completed during startup.")


# Custom docs_url to enable persistence for the "Authorize" button
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_ui_parameters={
            "persistAuthorization": True,  # This tells Swagger UI to save the token in localStorage
        },
    )

# Required if you're using OAuth2 (even just for Bearer token handling in Swagger UI)
@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_html(openapi_url=app.openapi_url, title=app.title)


# Correctly reference the frontend directory
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

app.include_router(auth.router)
app.include_router(lobby.router)
