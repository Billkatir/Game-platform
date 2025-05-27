from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from models.games import Game, Room
from models.user import User
from business.database_operations import get_postgresql_session
# --- NEW IMPORTS ---
from business.auth_operations import get_current_user # Import your authentication dependency
from uuid import UUID # Still needed for User.id type
from pydantic import BaseModel
# --- END NEW IMPORTS ---

router = APIRouter()

class RoomCreate(BaseModel):
    password: str

# --- UPDATED get_current_active_user function ---
# This now uses your authentication logic to get the user from the token.
async def get_current_active_user(
    username: str = Depends(get_current_user), # Get username from the token
    session: Session = Depends(get_postgresql_session) # Get DB session
) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user
# --- END UPDATED FUNCTION ---

@router.get("/available_games", response_model=list[Game])
def get_available_games(session: Session = Depends(get_postgresql_session)):
    statement = select(Game).where(Game.available == True)
    games = session.exec(statement).all()
    return games

@router.post("/create_room/{game_name}", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(
    game_name: str,
    room_data: RoomCreate,
    current_user: User = Depends(get_current_active_user), # This will now work correctly
    session: Session = Depends(get_postgresql_session)
):
    game = session.exec(select(Game).where(Game.name == game_name)).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game '{game_name}' not found."
        )

    new_room = Room(
        password=room_data.password,
        type_of_game_id=game.id,
        created_by_id=current_user.id
    )

    session.add(new_room)
    session.commit()
    session.refresh(new_room)

    return new_room