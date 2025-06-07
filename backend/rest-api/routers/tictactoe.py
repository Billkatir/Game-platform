from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, List, Optional
from sqlmodel import select, Session, Field, Column, SQLModel # Ensure SQLModel is imported
from sqlalchemy.dialects.postgresql import ARRAY, INTEGER # For ARRAY type
from business.database_operations import get_postgresql_session
from pydantic import BaseModel
from uuid import UUID # Assuming User.id is UUID

# IMPORTANT: You MUST ensure your Game and Room models are imported from models/games.py
# Do NOT define them here if they are already in models/games.py.
# If they are only defined here, then ensure models/games.py does NOT define them.
# The `models.games` import is preferred.
from models.games import Game, Room # <--- Make sure these are the correct models with `position` in Room

router = APIRouter()

# Global state dictionaries for real-time WebSocket connections (not for persistent board state)
active_connections: Dict[int, List[WebSocket]] = {}
turn_tracker: Dict[int, int] = {}
game_status: Dict[int, Optional[str]] = {}
draw_offered_by: Dict[int, Optional[int]] = {}

def check_winner(board: List[int]) -> Optional[int]:
    win_positions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    for positions in win_positions:
        p0, p1, p2 = positions
        if board[p0] != 0 and board[p0] == board[p1] == board[p2]:
            return board[p0]
    return None

def board_full(board: List[int]) -> bool:
    return all(pos != 0 for pos in board)

class MakeMoveRequest(BaseModel):
    position: int
    player_index: int

@router.post("/room/{room_id}/make_move")
def post_move(
    room_id: int,
    move_data: MakeMoveRequest,
    session: Session = Depends(get_postgresql_session)
):
    # 1. Retrieve the absolute latest board state from the database.
    room = session.exec(select(Room).where(Room.id == room_id)).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")

    # Input validation based on the CURRENT board from DB
    if not (0 <= move_data.position < len(room.position)):
        raise HTTPException(status_code=400, detail="Invalid move position.")

    if room.position[move_data.position] != 0:
        raise HTTPException(status_code=400, detail="Position already taken.")

    if move_data.player_index not in [0, 1]:
        raise HTTPException(status_code=400, detail="Invalid player index. Must be 0 or 1.")

    # 2. Apply the new move to this freshly retrieved board.
    # IMPORTANT: Create a NEW list to ensure SQLModel detects the change.
    updated_board = list(room.position) # Make a copy of the *current* board
    updated_board[move_data.position] = move_data.player_index + 1
    room.position = updated_board # Assign the *new list* back

    # 3. Save the entirely new board state back to the database.
    try:
        session.add(room)
        session.commit()
        session.refresh(room) # Refresh to ensure `room` object holds latest DB state
        return {"message": "Move successfully recorded.", "new_board": list(room.position)}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record move: {e}")

@router.websocket("/ws/game/{game_id}")
async def game_ws(
    websocket: WebSocket,
    game_id: int,
    session: Session = Depends(get_postgresql_session)
):
    await websocket.accept()

    # Initial load of room and game configuration
    room = session.exec(select(Room).where(Room.id == game_id)).first()
    if not room:
        await websocket.send_json({"error": "Invalid room ID. Please provide a valid room ID."})
        await websocket.close(code=1008, reason="Invalid Room ID")
        return

    game = session.exec(select(Game).where(Game.id == room.type_of_game_id)).first()
    if not game:
        await websocket.send_json({"error": "Game configuration not found for this room."})
        await websocket.close(code=1008, reason="Game config missing for room")
        return

    # Ensure the board in the database is correctly initialized *if it's empty/malformed*
    expected_board_size = getattr(game, 'board_size', 9) # Assuming board_size on Game model or default to 9
    if not room.position or len(room.position) != expected_board_size:
        room.position = [0] * expected_board_size
        session.add(room)
        session.commit()
        session.refresh(room)

    # Initialize in-memory game state for THIS WebSocket session if not already done
    if game_id not in active_connections:
        active_connections[game_id] = []
        turn_tracker[game_id] = 0
        game_status[game_id] = "ongoing"
        draw_offered_by[game_id] = None

    if len(active_connections[game_id]) >= game.number_of_players:
        await websocket.send_json({"error": "Room full."})
        await websocket.close(code=1008, reason="Room full")
        return

    active_connections[game_id].append(websocket)
    player_index = active_connections[game_id].index(websocket)

    await websocket.send_json({"message": f"Connected as player {player_index}"})

    # Send initial game state (which includes the board *from the DB*) to the new player
    await websocket.send_json({
        "action": "initial_state",
        "board": list(room.position), # <--- Initial board loaded from DB
        "turn": turn_tracker[game_id],
        "status": game_status[game_id],
        "player_index": player_index
    })

    if len(active_connections[game_id]) == game.number_of_players:
        for conn in active_connections[game_id]:
            await conn.send_json({
                "action": "game_ready",
                "message": "Both players connected. Game can start!",
                "current_board": list(room.position), # <--- Board from DB
                "current_turn": turn_tracker[game_id]
            })

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            current_game_status = game_status.get(game_id, "ongoing")

            if action == "get_turn":
                await websocket.send_json({"turn": turn_tracker[game_id]})

            elif action == "get_board":
                # When asked for board, ALWAYS get it freshly from the DB
                room = session.exec(select(Room).where(Room.id == game_id)).first()
                if room:
                    await websocket.send_json({"board": list(room.position)})
                else:
                    await websocket.send_json({"error": "Room not found for board request."})


            elif action == "make_move":
                if current_game_status != "ongoing":
                    await websocket.send_json({"error": "Game already ended."})
                    continue

                pos = data.get("position")
                # 1. Retrieve the absolute latest board state from the database.
                # Important: Re-fetch the room to get the absolute latest state
                # especially if multiple clients are making moves
                session.refresh(room) # Refresh the current `room` object to get latest DB state

                # Input validation based on the CURRENT board from DB
                if not isinstance(pos, int) or pos < 0 or pos >= len(room.position):
                    await websocket.send_json({"error": "Invalid position."})
                    continue

                if room.position[pos] != 0:
                    await websocket.send_json({"error": "Position already taken."})
                    continue

                if turn_tracker[game_id] != player_index:
                    await websocket.send_json({"error": "Not your turn."})
                    continue

                # 2. Apply the new move to this freshly retrieved board.
                # IMPORTANT: Create a NEW list to ensure SQLModel detects the change.
                updated_board = list(room.position) # Make a copy of the *current* board
                updated_board[pos] = player_index + 1
                room.position = updated_board # Assign the *new list* back

                # 3. Save the entirely new board state back to the database.
                try:
                    session.add(room)
                    session.commit()
                    session.refresh(room) # Refresh to ensure `room` object holds latest DB state
                except Exception as e:
                    session.rollback()
                    await websocket.send_json({"error": f"Failed to record move: {e}"})
                    continue # Do not proceed with broadcasting if save failed

                draw_offered_by[game_id] = None

                winner = check_winner(room.position)

                next_turn_for_broadcast = turn_tracker[game_id]
                if not winner and not board_full(room.position):
                    next_turn_for_broadcast = 1 - turn_tracker[game_id]

                turn_tracker[game_id] = next_turn_for_broadcast

                # 4. Broadcast this complete, updated board to all clients.
                for conn in active_connections[game_id]:
                    await conn.send_json({
                        "action": "update",
                        "board": list(room.position), # <--- Send the fully updated board from DB
                        "last_move_by": player_index,
                        "current_turn": turn_tracker[game_id]
                    })

                if winner:
                    game_status[game_id] = "win"
                    for conn in active_connections[game_id]:
                        await conn.send_json({
                            "action": "game_over",
                            "result": f"Player {winner-1} wins!",
                            "board": list(room.position)
                        })
                elif board_full(room.position):
                    game_status[game_id] = "tie"
                    for conn in active_connections[game_id]:
                        await conn.send_json({
                            "action": "game_over",
                            "result": "It's a draw!",
                            "board": list(room.position)
                        })

            elif action == "offer_draw":
                if current_game_status != "ongoing":
                    await websocket.send_json({"error": "Cannot offer draw, game ended."})
                    continue

                if draw_offered_by[game_id] is not None:
                    await websocket.send_json({"error": "A draw offer is already pending."})
                    continue

                draw_offered_by[game_id] = player_index
                other_player_index = 1 - player_index
                if len(active_connections[game_id]) > other_player_index:
                    await active_connections[game_id][other_player_index].send_json({
                        "action": "draw_offer",
                        "from_player": player_index
                    })
                await websocket.send_json({"message": "Draw offer sent."})

            elif action == "respond_draw":
                if draw_offered_by[game_id] is None:
                    await websocket.send_json({"error": "No draw offer to respond to."})
                    continue

                if player_index == draw_offered_by[game_id]:
                    await websocket.send_json({"error": "You cannot respond to your own draw offer."})
                    continue

                accept = data.get("accept", False)
                if accept:
                    # 1. Retrieve the absolute latest board state from the database. (Already have `room`)
                    # 2. Apply the new "move" (reset board) to this freshly retrieved board.
                    room.position = [0] * len(room.position) # New list assigned
                    # 3. Save the entirely new board state back to the database.
                    session.add(room)
                    session.commit()
                    session.refresh(room)

                    game_status[game_id] = "draw_agreed"
                    for conn in active_connections[game_id]:
                        await conn.send_json({
                            "action": "game_over",
                            "result": "draw_agreed",
                            "board": list(room.position)
                        })
                else:
                    offerer = draw_offered_by[game_id]
                    if len(active_connections[game_id]) > offerer:
                        await active_connections[game_id][offerer].send_json({
                            "action": "draw_declined",
                            "from_player": player_index
                        })
                    await websocket.send_json({"message": "Draw declined."})

                draw_offered_by[game_id] = None

            elif action == "leave_room":
                other_player_index = 1 - player_index
                if len(active_connections[game_id]) > other_player_index and active_connections[game_id][other_player_index] != websocket:
                    await active_connections[game_id][other_player_index].send_json({
                        "action": "player_left",
                        "player": player_index,
                        "message": f"Player {player_index} has left the room. Game ended."
                    })
                    game_status[game_id] = "player_left"

                if websocket in active_connections.get(game_id, []):
                    active_connections[game_id].remove(websocket)
                await websocket.close(code=1000, reason="Player left room")

                if not active_connections[game_id]:
                    active_connections.pop(game_id, None)
                    turn_tracker.pop(game_id, None)
                    game_status.pop(game_id, None)
                    draw_offered_by.pop(game_id, None)
                return

            elif action == "play_again":
                if current_game_status not in ("win", "tie", "draw_agreed", "player_left", "player_disconnected"):
                    await websocket.send_json({"error": "Game not finished yet."})
                    continue

                # 1. Retrieve the absolute latest board state from the database. (Already have `room`)
                # 2. Apply the new "move" (reset board) to this freshly retrieved board.
                room.position = [0] * len(room.position) # New list assigned
                # 3. Save the entirely new board state back to the database.
                session.add(room)
                session.commit()
                session.refresh(room)

                game_status[game_id] = "ongoing"
                turn_tracker[game_id] = 0
                draw_offered_by[game_id] = None

                # 4. Broadcast this complete, updated board to all clients.
                for conn in active_connections[game_id]:
                    await conn.send_json({
                        "action": "game_restart",
                        "board": list(room.position),
                        "message": "Game restarted, Player 0 starts."
                    })

            else:
                await websocket.send_json({"error": "Unknown action."})

    except WebSocketDisconnect:
        if websocket in active_connections.get(game_id, []):
            active_connections[game_id].remove(websocket)

            if len(active_connections[game_id]) > 0:
                remaining_player_conn = active_connections[game_id][0]
                await remaining_player_conn.send_json({
                    "action": "player_left",
                    "player": player_index,
                    "message": f"Player {player_index} has disconnected unexpectedly. Game ended."
                })
                game_status[game_id] = "player_disconnected"

            if not active_connections[game_id]:
                active_connections.pop(game_id, None)
                turn_tracker.pop(game_id, None)
                game_status.pop(game_id, None)
                draw_offered_by.pop(game_id, None)