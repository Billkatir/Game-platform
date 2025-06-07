# business/database_operations.py (UPDATED AND CORRECTED)
from sqlmodel import SQLModel, create_engine, Session, select
from models.user import User  # Make sure these imports are correct
from models.games import Game, Room # Make sure these imports are correct

POSTGRESQL_DATABASE_URL = "postgresql://admin:admin@postgres:5432/game_platform"

postgresql_engine = create_engine(POSTGRESQL_DATABASE_URL, echo=True) 

DEFAULT_GAMES_DATA = [
    {"name": "Tic Tac Toe", "number_of_players": 2, "available": True},
    {"name": "Chess", "number_of_players": 2, "available": True},
]

def create_postgresql_tables():
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(postgresql_engine)
    print("Database tables check completed.")

    print("Checking for and adding default games...")
    with Session(postgresql_engine) as session:
        for game_data in DEFAULT_GAMES_DATA:
            existing_game = session.exec(
                select(Game).where(Game.name == game_data["name"])
            ).first()

            if not existing_game:
                new_game = Game(**game_data)
                session.add(new_game)
                session.commit()
                session.refresh(new_game)
                print(f"Added default game: {new_game.name}")
            else:
                print(f"Game '{existing_game.name}' already exists. Skipping.")
    print("Default games check/population completed.")

# THIS IS THE CRITICAL CHANGE FOR WEB SOCKETS
def get_postgresql_session():
    session = Session(postgresql_engine) # Create the session
    try:
        yield session # Yield it to the FastAPI endpoint
    finally:
        # This 'finally' block ensures the session is closed
        # ONLY when the WebSocket connection is terminated.
        session.close()