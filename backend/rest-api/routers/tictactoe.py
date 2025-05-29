from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
from sqlmodel import select
from models.games import Game
from business.database_operations import get_postgresql_session

router = APIRouter()

active_connections: Dict[int, List[WebSocket]] = {}  # game_id -> list of sockets
turn_tracker: Dict[int, int] = {}  # game_id -> current turn (0 or 1)
game_status: Dict[int, Optional[str]] = {}  # game_id -> "ongoing", "win", "tie", or "draw_offer"

# track which player offered a draw, None if no offer active
draw_offered_by: Dict[int, Optional[int]] = {}


def check_winner(board: List[int]) -> Optional[int]:
    win_positions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # cols
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]
    for positions in win_positions:
        p0, p1, p2 = positions
        if board[p0] != 0 and board[p0] == board[p1] == board[p2]:
            return board[p0]
    return None


def board_full(board: List[int]) -> bool:
    return all(pos != 0 for pos in board)


@router.websocket("/ws/game/{game_id}")
async def game_ws(websocket: WebSocket, game_id: int):
    await websocket.accept()

    if game_id not in active_connections:
        active_connections[game_id] = []
        turn_tracker[game_id] = 0  # Player 0 starts
        game_status[game_id] = "ongoing"
        draw_offered_by[game_id] = None

    if len(active_connections[game_id]) >= 2:
        await websocket.send_json({"error": "Room full."})
        await websocket.close()
        return

    active_connections[game_id].append(websocket)
    player_index = active_connections[game_id].index(websocket)
    await websocket.send_json({"message": f"Connected as player {player_index}"})

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            with get_postgresql_session() as session:
                game = session.exec(select(Game).where(Game.id == game_id)).first()
                if not game:
                    await websocket.send_json({"error": "Invalid game ID."})
                    continue

                status = game_status.get(game_id, "ongoing")

                if action == "get_turn":
                    await websocket.send_json({"turn": turn_tracker[game_id]})

                elif action == "get_board":
                    await websocket.send_json({"board": game.position})

                elif action == "make_move":
                    if status != "ongoing":
                        await websocket.send_json({"error": "Game already ended."})
                        continue

                    pos = data.get("position")
                    if not isinstance(pos, int) or pos < 0 or pos >= len(game.position):
                        await websocket.send_json({"error": "Invalid position."})
                        continue

                    if game.position[pos] != 0:
                        await websocket.send_json({"error": "Position already taken."})
                        continue

                    if turn_tracker[game_id] != player_index:
                        await websocket.send_json({"error": "Not your turn."})
                        continue

                    # Update board position: 1 for player 0, 2 for player 1
                    game.position[pos] = player_index + 1
                    session.add(game)
                    session.commit()

                    # Reset any draw offer when move is made
                    draw_offered_by[game_id] = None

                    winner = check_winner(game.position)
                    if winner is not None:
                        game_status[game_id] = "win"
                        for conn in active_connections[game_id]:
                            await conn.send_json({
                                "action": "game_over",
                                "result": "win",
                                "winner": winner,
                                "board": game.position
                            })
                        continue

                    if board_full(game.position):
                        game_status[game_id] = "tie"
                        for conn in active_connections[game_id]:
                            await conn.send_json({
                                "action": "game_over",
                                "result": "tie",
                                "board": game.position
                            })
                        continue

                    # Broadcast updated board
                    for conn in active_connections[game_id]:
                        await conn.send_json({
                            "action": "update",
                            "board": game.position,
                            "last_move_by": player_index
                        })

                    # Switch turn
                    turn_tracker[game_id] = 1 - turn_tracker[game_id]

                elif action == "offer_draw":
                    if status != "ongoing":
                        await websocket.send_json({"error": "Cannot offer draw, game ended."})
                        continue

                    if draw_offered_by[game_id] is not None:
                        await websocket.send_json({"error": "A draw offer is already pending."})
                        continue

                    draw_offered_by[game_id] = player_index
                    other_player = 1 - player_index
                    if len(active_connections[game_id]) > other_player:
                        await active_connections[game_id][other_player].send_json({
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
                        # Draw accepted: end game as tie by agreement
                        game_status[game_id] = "tie"
                        for conn in active_connections[game_id]:
                            await conn.send_json({
                                "action": "game_over",
                                "result": "draw_agreed",
                                "board": game.position
                            })
                    else:
                        # Draw declined, notify offering player
                        offerer = draw_offered_by[game_id]
                        if len(active_connections[game_id]) > offerer:
                            await active_connections[game_id][offerer].send_json({
                                "action": "draw_declined",
                                "from_player": player_index
                            })
                        await websocket.send_json({"message": "Draw declined."})

                    draw_offered_by[game_id] = None

                elif action == "leave_room":
                    # Notify the other player
                    other_player = 1 - player_index
                    if len(active_connections[game_id]) > other_player:
                        await active_connections[game_id][other_player].send_json({
                            "action": "player_left",
                            "player": player_index
                        })

                    # Remove this websocket and close it
                    active_connections[game_id].remove(websocket)
                    await websocket.close()
                    # If no players left, cleanup
                    if not active_connections[game_id]:
                        active_connections.pop(game_id, None)
                        turn_tracker.pop(game_id, None)
                        game_status.pop(game_id, None)
                        draw_offered_by.pop(game_id, None)
                    return

                elif action == "play_again":
                    if status not in ("win", "tie", "draw_agreed"):
                        await websocket.send_json({"error": "Game not finished yet."})
                        continue

                    # Reset the game board in DB
                    game.position = [0] * len(game.position)
                    session.add(game)
                    session.commit()

                    # Reset game status and turn tracker
                    game_status[game_id] = "ongoing"
                    turn_tracker[game_id] = 0
                    draw_offered_by[game_id] = None

                    # Notify all players about the new game start
                    for conn in active_connections[game_id]:
                        await conn.send_json({
                            "action": "game_restart",
                            "board": game.position,
                            "message": "Game restarted, Player 0 starts."
                        })

                else:
                    await websocket.send_json({"error": "Unknown action."})

    except WebSocketDisconnect:
        active_connections[game_id].remove(websocket)
        if not active_connections[game_id]:
            active_connections.pop(game_id, None)
            turn_tracker.pop(game_id, None)
            game_status.pop(game_id, None)
            draw_offered_by.pop(game_id, None)
