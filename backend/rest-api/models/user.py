# models/user.py
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from passlib.context import CryptContext
from typing import Optional

# DO NOT import Room here to avoid circular import.
# The Relationship will use a string reference for "Room".

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str
    password: str

    room_id: Optional[int] = Field(default=None, foreign_key="room.id")
    # Corrected Relationship for 'room'
    # Specify which foreign key column on the 'User' model links back to 'Room'.
    room: Optional["Room"] = Relationship(
        back_populates="users",
        sa_relationship_kwargs={
            "foreign_keys": "User.room_id" # This explicitly tells SQLA to use User.room_id for this relationship
        }
    )

    @staticmethod
    def hash_password(password: str):
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str):
        return pwd_context.verify(plain_password, self.password)