from fastapi import APIRouter, Depends
from typing import List

router = APIRouter(prefix="/games", tags=["Games"])

@router.get("/", response_model=List[dict])
def list_games():
    return [
        {
            "name": "TicTacToe",
            "description": "Simple 3x3 grid game",
            "endpoint": "/games/tictactoe"
        },
        # Add more games here
    ]
