from datetime import datetime
from sqlmodel import SQLModel, Field


class EnvironmentData(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    time: datetime = Field(default_factory=datetime.utcnow, index=True)
    device_type: str 
    device_id: int  
    temperature: float
    humidity: float
    
class LightData(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    time: datetime = Field(default_factory=datetime.utcnow, index=True)
    device_id: int
    light: int

class WeatherData(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    time: datetime = Field(default_factory=datetime.utcnow, index=True)
    device_id: int
    is_raining: bool
    is_windy: bool