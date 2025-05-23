from fastapi import FastAPI
from database import engine, Base
from models import user
from routers import auth

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Game Platform API"}

