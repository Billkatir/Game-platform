from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from business.auth_operations import create_access_token
from models.user import User
from sqlmodel import Field, Session, select
from business.database_operations import get_postgresql_session
from pydantic import BaseModel
from datetime import timedelta


router = APIRouter()

# Schema for user creation
class CreateUserRequest(BaseModel):
    username: str
    password: str

# Endpoint for creating a user
@router.post("/register")
def create_user(request: CreateUserRequest, session: Session = Depends(get_postgresql_session)):
    existing_user = session.exec(select(User).where(User.username == request.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=request.username,
        password=User.hash_password(request.password),
    )
    session.add(new_user)
    session.commit()

    return {"message": "User created successfully", "user_id": str(new_user.id)}

# Schema for login 
class LoginRequest(BaseModel):
    username: str
    password: str
    
# Endpoint for user login
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_postgresql_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}