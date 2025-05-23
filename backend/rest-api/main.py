from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from database import engine, Base
from models import user
from routers import auth
from routers import tictactoe 

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Define OAuth2 scheme with token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app.include_router(auth.router)
app.include_router(tictactoe.router)  # <----- add this

@app.get("/")
def root():
    return {"message": "Welcome to the Game Platform API"}
