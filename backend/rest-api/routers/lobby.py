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

# --- ADD THIS CLASS DEFINITION ---
class RoomUserCountResponse(BaseModel):
    room_id: int
    user_count: int
    max_players: Optional[int] = None
    message: str = ""
# --- END ADDITION ---

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

@router.post("/heartbeat")
def heartbeat(
    current_user: User = Depends(get_current_active_user)
):
    return {"status": "ok"}


@router.get("/my_room", response_model=Optional[Room])
def get_my_room(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_postgresql_session)
):
    if current_user.room_id is None:
        return None
    room = session.exec(
        select(Room).where(Room.id == current_user.room_id).options(selectinload(Room.game), selectinload(Room.users))
    ).first()
    return room

@router.get("/user_count/{room_id}", response_model=RoomUserCountResponse)
def get_room_user_count(
    room_id: int, # This path parameter will be the room's ID
    current_user: User = Depends(get_current_active_user), # Still require authentication
    session: Session = Depends(get_postgresql_session)
):
    # Load the room and its users/game to get the counts
    # We still need selectinload for users and game to get their counts/details
    room = session.exec(
        select(Room).where(Room.id == room_id).options(selectinload(Room.game), selectinload(Room.users))
    ).first()

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found."
        )

    actual_users_in_room = len(room.users) if room.users else 0
    max_game_players = room.game.number_of_players if room.game else 0

    return RoomUserCountResponse(
        room_id=room.id,
        user_count=actual_users_in_room,
        max_players=max_game_players,
        message=f"Retrieved user count for room {room.id}."
    )

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

    # --- THE FIX IS HERE ---
    # Determine the initial board size based on the game type.
    # For Tic-Tac-Toe, it's typically 9.
    # If your Game model has a `board_size` attribute, use that:
    # initial_board_size = game.board_size
    # Otherwise, hardcode for Tic-Tac-Toe if it's the only game type or if you have a default:
    initial_board_size = 9 # Assuming Tic-Tac-Toe's 3x3 board

    new_room = Room(
        password=room_data.password,
        type_of_game_id=game.id,
        created_by_id=current_user.id,
        position=[0] * initial_board_size # <-- This is the crucial line added/modified
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

    # Only rooms where available == True
    rooms = session.exec(
        select(Room)
        .where(Room.type_of_game_id == game.id)
        .where(Room.available == True)
    ).all()

    return rooms


def update_room_availability_and_cleanup(room: Room, session: Session):
    """
    Updates room availability based on current users and game max players.
    Deletes the room if no users remain.
    """
    if room.game:
        max_players = room.game.number_of_players
        current_players = len(room.users)

        if current_players == 0:
            # Delete the room if no users are inside
            session.delete(room)
            session.commit()
            return None  # Room no longer exists
        else:
            # Update availability depending on number of players
            room.available = current_players < max_players
            session.add(room)
            session.commit()
            session.refresh(room)
            return room
    else:
        # If no game info, just leave as is
        return room

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
    else: # If room has no password, but user provided one
        if room_join_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This room does not require a password."
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

    # Signal to the frontend that the user is in another room and needs confirmation
    if current_user.room_id is not None and current_user.room_id != room.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are currently in another room. Do you want to leave your current room and join this one?"
        )

    # All checks passed, user joins the room
    current_user.room_id = room.id
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    # Refresh room to get updated users list
    session.refresh(room)

    # Update room availability or delete if empty
    updated_room = update_room_availability_and_cleanup(room, session)
    if updated_room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room was deleted due to no users."
        )

    return updated_room

# --- NEW: Endpoint to leave the current room ---
@router.post("/leave_room", response_model=User)
def leave_room(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_postgresql_session)
):
    if current_user.room_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not currently in any room to leave."
        )

    old_room_id = current_user.room_id

    current_user.room_id = None
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    old_room = session.exec(
        select(Room).where(Room.id == old_room_id).options(selectinload(Room.game), selectinload(Room.users))
    ).first()

    if old_room:
        # Update availability or delete old room if empty
        updated_room = update_room_availability_and_cleanup(old_room, session)
        if updated_room is None:
            # Room deleted, no action needed here
            pass

    return current_user

# --- NEW: Endpoint to force join a room (after frontend confirmation) ---
@router.post("/force_join_room/{room_id}", response_model=Room)
def force_join_room(
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

    # Password check (same as join_room)
    if room.password:
        if not room_join_data.password or room_join_data.password != room.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for this room."
            )
    else:
        if room_join_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This room does not require a password."
            )

    # Room capacity check (same as join_room)
    if room.game:
        max_players = room.game.number_of_players
        current_players = len(room.users)
        
        # Only check if room is full IF the user is not already in this room
        if current_user.room_id != room.id and current_players >= max_players:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Room is full. Cannot join."
            )
        elif current_user.room_id == room.id:
            # Already in this room, no action needed for leaving/joining
            return room # Return the room as user is already there
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Room's game information not available."
        )

    # --- Leave previous room (if any) and join new one ---
    if current_user.room_id is not None and current_user.room_id != room.id:
        # User was in a different room, leave old room first
        old_room_id_to_refresh = current_user.room_id
        current_user.room_id = None
        session.add(current_user)
        session.commit() # Commit leaving the old room
        session.refresh(current_user)

        # Refresh old room's data (after user has left)
        old_room_obj = session.get(Room, old_room_id_to_refresh)
        if old_room_obj:
            session.refresh(old_room_obj)
            update_room_availability_and_cleanup(old_room_obj, session)

    # Now assign user to new room
    current_user.room_id = room.id
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    session.refresh(room)

    # Update availability or delete if empty
    updated_room = update_room_availability_and_cleanup(room, session)
    if updated_room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room was deleted due to no users."
        )

    return updated_room