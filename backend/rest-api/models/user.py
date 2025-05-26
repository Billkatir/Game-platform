from sqlalchemy import Column, Integer, String, JSON, Enum
from database import Base
import enum
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class RoomStatus(str, enum.Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    finished = "finished"

class TicTacToeRoom(Base):
    __tablename__ = "tictactoe_rooms"

    room_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    password = Column(String, nullable=False)
    board = Column(JSON, nullable=False)  # stores 3x3 board state
    players = Column(JSON, nullable=False)  # {"X": username or None, "O": username or None}
    current_turn = Column(String(1), nullable=False, default="X")
    status = Column(Enum(RoomStatus), nullable=False, default=RoomStatus.waiting)
    winner = Column(String(10), nullable=True)  # "X", "O", "draw" or None
