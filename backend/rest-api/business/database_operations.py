from sqlmodel import SQLModel, create_engine, Session, select
from models.user import User  
from models.games import Game, Room 
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
                # If game doesn't exist, create and add it
                new_game = Game(**game_data)
                session.add(new_game)
                session.commit() # Commit each game so it's immediately available
                session.refresh(new_game) # Refresh to get the generated ID
                print(f"Added default game: {new_game.name}")
            else:
                print(f"Game '{existing_game.name}' already exists. Skipping.")
    print("Default games check/population completed.")

def get_postgresql_session():
    with Session(postgresql_engine) as session:
        yield session