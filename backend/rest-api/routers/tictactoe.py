from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from schemas.tictactoe import (
    CreateRoomRequest, CreateRoomResponse,
    JoinRoomRequest, JoinRoomResponse,
    GameState,
    MakeMoveRequest, # We'll modify this to use row/col
    MakeMoveResponse,
    # LeaveGameRequest, # Not used in this context
    # LeaveGameResponse
)
from datetime import datetime
from utils.auth import get_current_user
import uuid
import json
import os
from threading import Lock
from typing import Dict, List, Optional, Literal

router = APIRouter(prefix="/games/tictactoe", tags=["TicTacToe"])

ROOMS_FILE = "tictactoe_rooms.json"
lock = Lock()

# In-memory storage for simplicity, but persist to file for restarts
rooms = {}

# Keep init_board as 2D array as per schema
def init_board() -> List[List[Optional[Literal["X", "O", ""]]]]:
    return [["" for _ in range(3)] for _ in range(3)]

def load_rooms():
    global rooms
    if os.path.exists(ROOMS_FILE):
        with open(ROOMS_FILE, "r") as f:
            try:
                loaded_rooms = json.load(f)
                # No flattening needed here, assume saved format matches 2D schema
                rooms.update(loaded_rooms)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {ROOMS_FILE}. Starting with empty rooms.")
                rooms = {}
    return rooms

def save_rooms():
    with open(ROOMS_FILE, "w") as f:
        json.dump(rooms, f)

# Load rooms once at startup
load_rooms()

# Check winner for 2D board
def check_winner(board: List[List[Optional[Literal["X", "O", ""]]]]) -> Optional[Literal["X", "O", "draw"]]:
    # Check rows
    for row in board:
        if row[0] and all(cell == row[0] for cell in row):
            return row[0]
    # Check columns
    for col_idx in range(3):
        if board[0][col_idx] and all(board[row_idx][col_idx] == board[0][col_idx] for row_idx in range(3)):
            return board[0][col_idx]
    # Check main diagonal
    if board[0][0] and all(board[i][i] == board[0][0] for i in range(3)):
        return board[0][0]
    # Check anti-diagonal
    if board[0][2] and all(board[i][2-i] == board[0][2] for i in range(3)):
        return board[0][2]
    
    # Check for draw
    if all(cell != "" for row in board for cell in row):
        return "draw"
    
    return None


@router.post("/create", response_model=CreateRoomResponse)
def create_room(request: CreateRoomRequest, current_user=Depends(get_current_user)):
    room_id = str(uuid.uuid4())
    room_data = {
        "password": request.password,
        "board": init_board(), # 2D board
        "players": {"X": current_user.username, "O": None},
        "current_turn": "X", # X always starts
        "status": "waiting", # Game is waiting for Player O
        "winner": None
    }
    with lock:
        rooms[room_id] = room_data
        save_rooms()
    return CreateRoomResponse(room_id=room_id, message="Room created. Waiting for opponent.")

@router.post("/join", response_model=JoinRoomResponse)
def join_room(request: JoinRoomRequest, current_user=Depends(get_current_user)):
    with lock:
        room = rooms.get(request.room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        if room["password"] != request.password:
            raise HTTPException(status_code=403, detail="Incorrect password")
        
        # Prevent joining if the user is already player X and tries to join as O, or vice versa
        if room["players"]["X"] == current_user.username and room["players"]["O"] is None:
            # Player X rejoining their own waiting room. Allow.
            pass
        elif room["players"]["O"] == current_user.username and room["status"] == "active":
            # Player O rejoining an active room. Allow.
            pass
        elif room["players"]["O"] is not None and room["players"]["O"] != current_user.username:
            raise HTTPException(status_code=400, detail="Room is full")
        elif room["players"]["X"] == current_user.username and room["players"]["O"] is not None:
             raise HTTPException(status_code=400, detail="You are already Player X in this room.")
        elif room["status"] == "finished":
            raise HTTPException(status_code=400, detail="Game is already finished.")


        # Assign player 'O' if slot is empty
        if room["players"]["O"] is None:
            room["players"]["O"] = current_user.username
            room["status"] = "active" # Game is now active as both players are here!
        
        save_rooms()

    return JoinRoomResponse(message="Joined room. Game started!", game_state=GameState(
        board=room["board"],
        current_turn=room["current_turn"],
        status=room["status"], # Will now be "active" for Player O joining
        winner=room["winner"]
    ))

# Modified: HTTP POST endpoint for making a move, now accepting row and col
# routers/tictactoe.py (Inside your make_move function)

@router.post("/restart", response_model=CreateRoomResponse) # Changed response_model
def restart_game(current_user=Depends(get_current_user)):   # Removed room_id query parameter
    """
    Creates a new game room and returns its ID.
    The user calling this endpoint will be Player X in the new room.
    This new room will be created without a password (or an empty string password).
    """
    new_room_id = str(uuid.uuid4())
    room_data = {
        "password": "",  # New room created via restart has no password or an empty one.
                         # Adjust if your CreateRoomRequest allows optional passwords and you prefer None.
        "board": init_board(),
        "players": {"X": current_user.username, "O": None}, # Caller is Player X
        "current_turn": "X",  # X always starts
        "status": "waiting",  # Game is waiting for Player O
        "winner": None
    }
    with lock:
        rooms[new_room_id] = room_data
        save_rooms()
    
    # Returning the ID of the NEW room, similar to the /create endpoint's response
    return CreateRoomResponse(room_id=new_room_id, message="New game room created. Waiting for opponent.")



@router.post("/make_move", response_model=MakeMoveResponse)
def make_move(request: MakeMoveRequest, current_user=Depends(get_current_user)):
    i = 0
    with lock:
        room = rooms.get(request.room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        player_symbol = request.player

        if not player_symbol:
            raise HTTPException(status_code=403, detail="You are not a player in this room.")
        
        if player_symbol != request.player:
            raise HTTPException(status_code=400, detail="Mismatched player symbol in request.")

        if room["status"] != "active":
            raise HTTPException(status_code=400, detail=f"Game is not active. Current status: {room['status']}")
        if room["current_turn"] != player_symbol:
            raise HTTPException(status_code=400, detail="Not your turn")
        
        # Validate row and col (0-2 for 2D array)
        if not (0 <= request.row < 3 and 0 <= request.col < 3):
            raise HTTPException(status_code=400, detail="Invalid move position (row/col out of bounds).")
        
        if room["board"][request.row][request.col] != "":
            raise HTTPException(status_code=400, detail="Cell already filled")

        # Make the move
        room["board"][request.row][request.col] = player_symbol
        
        winner = check_winner(room["board"])
        if winner:
            room["status"] = "finished"
            room["winner"] = winner
        else:
            # Switch turn
            room["current_turn"] = "O" if player_symbol == "X" else "X"
        
        save_rooms() # Save state after every move

    return MakeMoveResponse(message="Move successful", game_state=GameState(
        board=room["board"],
        current_turn=room["current_turn"],
        status=room["status"],
        winner=room["winner"]
    ))


@router.get("/game_state", response_model=GameState)
def get_game_state(room_id: str = Query(...)):
    with lock:
        room = rooms.get(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        return GameState(
            board=room["board"],
            current_turn=room["current_turn"],
            status=room["status"],
            winner=room["winner"]
        )

# Removed WebSocket endpoint to avoid confusion/unused code given the HTTP polling approach.
# If you want to use WebSockets for real-time updates, the frontend would need to be rewritten
# to use a WebSocket connection instead of polling and HTTP POST for moves.
# @router.websocket("/ws/{room_id}")
# async def websocket_endpoint(websocket: WebSocket, room_id: str):
#    pass # ... (WebSocket implementation)