from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, lobby
from business.database_operations import create_postgresql_tables
import os

app = FastAPI(
    title="Game Platform Application API",
    description="This is the backend service of our Game Platform Application",
    version="0.0.1",
    swagger_ui=True,
)

# Set CORS policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins. You can specify a list of allowed origins.
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


#  --- THIS IS THE CRITICAL CHANGE ---
#  This decorator tells FastAPI to run the 'on_startup' function
#  *after* the application has initialized, but *before* it starts
#  accepting incoming requests. This ensures your tables exist.
@app.on_event("startup")
def on_startup():
    print("FastAPI startup event triggered: Calling create_postgresql_tables()...")
    create_postgresql_tables()  # This will now run at the correct time
    print("Database tables creation check completed during startup.")


#  --- END CRITICAL CHANGE ---

# Correctly reference the frontend directory
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

app.include_router(auth.router)
app.include_router(lobby.router)