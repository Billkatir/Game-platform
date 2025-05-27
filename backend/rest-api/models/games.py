from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from models.user import User
from uuid import UUID

class Game(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    number_of_players: int
    available: bool = Field(default=True)

class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_by_id: UUID = Field(foreign_key="user.id")
    password: str
    type_of_game_id: int = Field(foreign_key="game.id")