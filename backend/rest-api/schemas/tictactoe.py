from pydantic import BaseModel
from typing import List, Optional, Literal

class CreateRoomRequest(BaseModel):
    password: str

class CreateRoomResponse(BaseModel):
    room_id: str
    message: str

class JoinRoomRequest(BaseModel):
    room_id: str
    password: str

class GameState(BaseModel):
    board: List[List[Optional[Literal["X", "O", ""]]]]  # 3x3 matrix
    current_turn: Literal["X", "O"]
    status: Literal["waiting", "in_progress", "finished"]
    winner: Optional[Literal["X", "O", "draw", None]] = None

class JoinRoomResponse(BaseModel):
    message: str
    game_state: GameState

class GetGameStateResponse(GameState):
    pass  # same fields as GameState

class MakeMoveRequest(BaseModel):
    room_id: str
    player: Literal["X", "O"]
    row: int
    col: int

class MakeMoveResponse(BaseModel):
    message: str
    game_state: GameState

class LeaveGameRequest(BaseModel):
    room_id: str
    player: Literal["X", "O"]

class LeaveGameResponse(BaseModel):
    message: str
