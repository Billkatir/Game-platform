from fastapi import APIRouter, HTTPException, Depends, status
from schemas.tictactoe import (
    CreateRoomRequest, CreateRoomResponse,
    JoinRoomRequest, JoinRoomResponse,
    GameState, MakeMoveRequest, MakeMoveResponse,
    LeaveGameRequest, LeaveGameResponse
)
from utils.auth import get_current_user  # your existing auth dependency
import uuid

router = APIRouter(prefix="/games/tictactoe", tags=["TicTacToe"])

# In-memory store for rooms (room_id -> room info)
rooms = {}

def init_board():
    return [["" for _ in range(3)] for _ in range(3)]

@router.post("/create", response_model=CreateRoomResponse)
def create_room(request: CreateRoomRequest, current_user=Depends(get_current_user)):
    room_id = str(uuid.uuid4())
    rooms[room_id] = {
        "password": request.password,
        "board": init_board(),
        "players": {"X": current_user.username, "O": None},
        "current_turn": "X",
        "status": "waiting",
        "winner": None
    }
    return CreateRoomResponse(room_id=room_id, message="Room created. Waiting for opponent.")

@router.post("/join", response_model=JoinRoomResponse)
def join_room(request: JoinRoomRequest, current_user=Depends(get_current_user)):
    room = rooms.get(request.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["password"] != request.password:
        raise HTTPException(status_code=403, detail="Incorrect password")
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Room already started or finished")
    if room["players"]["O"] is not None:
        raise HTTPException(status_code=400, detail="Room is full")
    if current_user.username == room["players"]["X"]:
        raise HTTPException(status_code=400, detail="You cannot join your own room as opponent")
    room["players"]["O"] = current_user.username
    room["status"] = "in_progress"
    game_state = GameState(
        board=room["board"],
        current_turn=room["current_turn"],
        status=room["status"],
        winner=room["winner"]
    )
    return JoinRoomResponse(message="Joined room. Game started!", game_state=game_state)

@router.get("/state/{room_id}", response_model=GameState)
def get_game_state(room_id: str, current_user=Depends(get_current_user)):
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    # Optional: Verify that current_user is part of this game
    if current_user.username not in room["players"].values():
        raise HTTPException(status_code=403, detail="You are not a player in this room")
    return GameState(
        board=room["board"],
        current_turn=room["current_turn"],
        status=room["status"],
        winner=room["winner"]
    )

def check_winner(board):
    lines = []
    # rows
    lines.extend(board)
    # columns
    lines.extend([[board[r][c] for r in range(3)] for c in range(3)])
    # diagonals
    lines.append([board[i][i] for i in range(3)])
    lines.append([board[i][2 - i] for i in range(3)])
    for line in lines:
        if line[0] and all(cell == line[0] for cell in line):
            return line[0]
    # check draw
    if all(cell != "" for row in board for cell in row):
        return "draw"
    return None

@router.post("/move", response_model=MakeMoveResponse)
def make_move(request: MakeMoveRequest, current_user=Depends(get_current_user)):
    room = rooms.get(request.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Game not in progress")
    if request.player not in ["X", "O"]:
        raise HTTPException(status_code=400, detail="Invalid player")
    if room["players"][request.player] != current_user.username:
        raise HTTPException(status_code=403, detail="Not your turn or not your game")
    if room["current_turn"] != request.player:
        raise HTTPException(status_code=400, detail="Not your turn")
    if not (0 <= request.row < 3 and 0 <= request.col < 3):
        raise HTTPException(status_code=400, detail="Invalid board position")
    if room["board"][request.row][request.col] != "":
        raise HTTPException(status_code=400, detail="Cell already taken")

    # Make move
    room["board"][request.row][request.col] = request.player

    # Check for winner
    winner = check_winner(room["board"])
    if winner:
        room["status"] = "finished"
        room["winner"] = winner
    else:
        # Switch turn
        room["current_turn"] = "O" if room["current_turn"] == "X" else "X"

    game_state = GameState(
        board=room["board"],
        current_turn=room["current_turn"],
        status=room["status"],
        winner=room["winner"]
    )
    return MakeMoveResponse(message="Move accepted", game_state=game_state)

@router.post("/leave", response_model=LeaveGameResponse)
def leave_game(request: LeaveGameRequest, current_user=Depends(get_current_user)):
    room = rooms.get(request.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if request.player not in ["X", "O"]:
        raise HTTPException(status_code=400, detail="Invalid player")
    if room["players"][request.player] != current_user.username:
        raise HTTPException(status_code=403, detail="You are not this player")

    # Remove player from room
    room["players"][request.player] = None

    # If both players left or game finished, delete room
    if (room["players"]["X"] is None and room["players"]["O"] is None) or room["status"] == "finished":
        del rooms[request.room_id]
        return LeaveGameResponse(message="Game ended and room closed")
    else:
        room["status"] = "waiting"
        return LeaveGameResponse(message=f"Player {request.player} left the game")
