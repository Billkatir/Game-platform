# models/games.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSON
from uuid import UUID

# Ensure Game is defined before Room if they are in the same file
class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    number_of_players: int  # The max capacity
    available: bool = Field(default=True)

    # New field for 3x3 board (flat list of 9 positions)
    position: List[int] = Field(
        sa_column=Column(JSON),
        default_factory=lambda: [0] * 9
    )

    rooms: List["Room"] = Relationship(back_populates="game")

class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_by_id: UUID = Field(foreign_key="user.id")
    password: Optional[str] = Field(default=None, nullable=True)
    type_of_game_id: int = Field(foreign_key="game.id")
    available: bool = Field(default=True)
    game: Optional["Game"] = Relationship(back_populates="rooms") 
    users: List["User"] = Relationship(
        back_populates="room",
        sa_relationship_kwargs={
            "foreign_keys": "User.room_id"
        }
    )
