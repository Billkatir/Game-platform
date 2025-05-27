from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str
    password: str

    @staticmethod
    def hash_password(password: str):
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str):
        return pwd_context.verify(plain_password, self.password)
