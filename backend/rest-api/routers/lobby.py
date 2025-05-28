from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from models.games import Game, Room
from models.user import User
from business.database_operations import get_postgresql_session
from business.auth_operations import get_current_user
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List


router = APIRouter()

class RoomCreate(BaseModel):
    password: Optional[str] = None

class RoomJoin(BaseModel):
    password: Optional[str] = None

async def get_current_active_user(
    username: str = Depends(get_current_user),
    session: Session = Depends(get_postgresql_session)
) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user

@router.get("/available_games", response_model=List[Game])
def get_available_games(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_postgresql_session)
):
    statement = select(Game).where(Game.available == True)
    games = session.exec(statement).all()
    return games

@router.post("/create_room/{game_name}", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(
    game_name: str,
    room_data: RoomCreate,
    current_user: User = Depends(get_current_active_user),
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

@router.get("/available_rooms/{game_name}", response_model=List[Room])
def get_available_rooms(
    game_name: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_postgresql_session)
):
    game = session.exec(select(Game).where(Game.name == game_name)).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game '{game_name}' not found."
        )

    rooms = session.exec(select(Room).where(Room.type_of_game_id == game.id)).all()
    return rooms

@router.post("/join_room/{room_id}", response_model=Room)
def join_room(
    room_id: int,
    room_join_data: RoomJoin,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_postgresql_session)
):
    statement = (
        select(Room)
        .where(Room.id == room_id)
        .options(selectinload(Room.game), selectinload(Room.users))
    )
    room = session.exec(statement).first()

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found."
        )

    if room.password:
        if not room_join_data.password or room_join_data.password != room.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for this room."
            )
    if room.game:
        max_players = room.game.number_of_players
        current_players = len(room.users)

        if current_players >= max_players:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room is full. Cannot join."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Room's game information not available."
        )

    if current_user.room_id == room.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already in this room."
        )

    current_user.room_id = room.id
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    session.refresh(room)

    return room