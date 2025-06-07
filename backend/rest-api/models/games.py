# models/games.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import ARRAY, INTEGER
from uuid import UUID

class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    number_of_players: int
    available: bool = Field(default=True)

    # The 'position' is removed from Game as it belongs to the Room instance
    # position: List[int] = Field(
    #     sa_column=Column(ARRAY(INTEGER)),
    #     default_factory=lambda: [0] * 9
    # )

    rooms: List["Room"] = Relationship(back_populates="game")

class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_by_id: UUID = Field(foreign_key="user.id")
    password: Optional[str] = Field(default=None, nullable=True)
    type_of_game_id: int = Field(foreign_key="game.id")
    available: bool = Field(default=True)

    # The board position for THIS specific game instance (room)
    position: List[int] = Field( # <--- NEW LOCATION FOR POSITION
        sa_column=Column(ARRAY(INTEGER)),
        default_factory=lambda: [0] * 9 # Initial state for a new room
    )

    game: Optional["Game"] = Relationship(back_populates="rooms")
    users: List["User"] = Relationship(
        back_populates="room",
        sa_relationship_kwargs={
            "foreign_keys": "User.room_id"
        }
    )