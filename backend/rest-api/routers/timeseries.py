from fastapi import APIRouter, Depends, HTTPException, Depends, Query
from sqlmodel import select, Session
from datetime import datetime
from business.database_operations import get_timescaledb_session
from models.greenhouse import EnvironmentData, LightData, WeatherData
from business.auth_operations import get_current_user
from sqlalchemy.sql import func

router = APIRouter()  # New router for time-series endpoints

# Endpoint to get the latest environment data for a given node_id
@router.get("/{node_id}/environment/latest")
def get_latest_environment_data(
    node_id: int,
    session: Session = Depends(get_timescaledb_session),
    current_user=Depends(get_current_user)
    ):
    
    latest_data = (
        session.exec(select(EnvironmentData).where(EnvironmentData.device_id == node_id)
                     .order_by(EnvironmentData.time.desc()).limit(1))
    )
    
    latest_data = latest_data.first()
    if latest_data is None:
        raise HTTPException(status_code=404, detail="No data found for the specified node_id")
    
    return {
        "temperature": latest_data.temperature,
        "humidity": latest_data.humidity
    }

@router.get("/zones-number")
def get_zone_count(
    session: Session=Depends(get_timescaledb_session),
    current_user=Depends(get_current_user),
):
    zone_count = (
        session.exec(
            select(EnvironmentData.device_id).distinct()
        )
    ).fetchall()
    
    return {"zone_count": len(zone_count)}


@router.get("/{id}/environment/{value}")
def get_environment_data_by_date(
    id: int,
    value: str,
    datetime: datetime = Query(..., description="Specific date to retrieve data."),
    session: Session=Depends(get_timescaledb_session),
    current_user=Depends(get_current_user)
):
    
    if value not in ("temperature", "humidity"):
        raise HTTPException(
            status_code = 400,
            detail = f"Invalid value '{value}'. Must be 'temperature' or 'humidity'. "
        )
        
    specific_data = session.exec(
        select(EnvironmentData)
            .where(
                EnvironmentData.device_id == id,
                func.date(EnvironmentData.time) == func.date(datetime)  # Extract the date
            )
    ).all()
    
    if not specific_data:
        raise HTTPException(
            status_code = 404,
            detail=f"No data found for device_id={id} on {datetime.date()} for {value}"
        )
        
    result = [{"time": record.time, value: getattr(record, value)} for record in specific_data]
    
    return {f"{value}_data": result}


@router.get("/weather/latest")
def get_latest_weather(
    session: Session = Depends(get_timescaledb_session),  # Database session
    current_user=Depends(get_current_user),  # Secure endpoint
):
    # Get the latest light data
    latest_light = session.exec(
        select(LightData)
            .order_by(LightData.time.desc())  # Order by latest time
            .limit(1)  # Get only the latest record
    ).first()

    # Get the latest weather data (rain and wind state)
    latest_weather = session.exec(
        select(WeatherData)
            .order_by(WeatherData.time.desc())  # Order by latest time
            .limit(1)  # Get only the latest record
    ).first()

    if not latest_light or not latest_weather:
        raise HTTPException(
            status_code=404,
            detail="No weather data available",
        )

    # Return the required information
    return {
        "light": latest_light.light,
        "is_raining": latest_weather.is_raining,
        "is_windy": latest_weather.is_windy,
    }
    