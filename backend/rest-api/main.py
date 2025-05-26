from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from database import engine, Base
from models import user
from routers import auth, tictactoe, games
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define OAuth2 scheme with token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app.include_router(auth.router)
app.include_router(tictactoe.router)
app.include_router(games.router)

@app.get("/")
def root():
    return {"message": "Welcome to the Game Platform API"}
