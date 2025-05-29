from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select, Session
from business.database_operations import get_postgresql_session
from models.settings import GreenhouseSettings  # Ensure import of the model
from business.auth_operations import get_current_user  # Authentication check
from pydantic import BaseModel
from datetime import time

router = APIRouter()

# Define the Pydantic model to represent response data, excluding sensitive fields like `id` and `node_id`
class GreenhouseSettingsResponse(BaseModel):
    upper_temperature: float
    lower_temperature: float
    upper_humidity_windows: int
    window_open_step: int
    window_sleep_step: int
    humidity_windows_sleep_step: int
    humidity_windows_cycle_await: int
    windows_total_closing: int
    windows_open_rain: int
    curtains_open_humidity: int
    humidity_curtains_sleep_step: int
    humidity_curtains_cycle_await: int
    upper_humidity_curtains: int
    curtains_total_closing: int
    curtains_open_after_closing: int
    upper_light: int
    lower_light: int
    main_heat_start_temp: float
    main_heat_stop_temp: float
    main_heat_max_time: int
    main_heat_pause_time: int
    main_heat_humidity_start: float
    main_heat_humidity_stop: float
    main_heat_humidity_max_time: int
    main_heat_humidity_pause_time: int
    secondary_heat_start_temp: float
    secondary_heat_stop_temp: float
    secondary_heat_max_time: int
    secondary_heat_pause_time: int
    secondary_heat_humidity_start: float
    secondary_heat_humidity_stop: float
    secondary_heat_humidity_max_time: int
    secondary_heat_humidity_pause_time: int
    day_start: time  
    night_start: time
    window_manual_operation: int
    curtains_manual_operation: int
    main_heating_manual_operation: int
    secondary_heating_manual_operation: int

# Define the Pydantic model for creating new settings (excluding `id` and `node_id`)
class GreenhouseSettingsCreate(BaseModel):
    upper_temperature: float
    lower_temperature: float
    upper_humidity_windows: int
    window_open_step: int
    window_sleep_step: int
    humidity_windows_sleep_step: int
    humidity_windows_cycle_await: int
    windows_total_closing: int
    windows_open_rain: int
    curtains_open_humidity: int
    humidity_curtains_sleep_step: int
    humidity_curtains_cycle_await: int
    upper_humidity_curtains: int
    curtains_total_closing: int
    curtains_open_after_closing: int
    upper_light: int
    lower_light: int
    main_heat_start_temp: float
    main_heat_stop_temp: float
    main_heat_max_time: int
    main_heat_pause_time: int
    main_heat_humidity_start: float
    main_heat_humidity_stop: float
    main_heat_humidity_max_time: int
    main_heat_humidity_pause_time: int
    secondary_heat_start_temp: float
    secondary_heat_stop_temp: float
    secondary_heat_max_time: int
    secondary_heat_pause_time: int
    secondary_heat_humidity_start: float
    secondary_heat_humidity_stop: float
    secondary_heat_humidity_max_time: int
    secondary_heat_humidity_pause_time: int
    day_start: time  
    night_start: time
    window_manual_operation: int
    curtains_manual_operation: int
    main_heating_manual_operation: int
    secondary_heating_manual_operation: int

# Endpoint to get the latest settings for a given node
@router.get("/{node_id}/settings/latest", response_model=GreenhouseSettingsResponse)
def get_latest_settings(
    node_id: int,
    session=Depends(get_postgresql_session),
    current_user=Depends(get_current_user),  # Secure endpoint with authentication
):
    # Query to get the latest settings for the specific node
    latest_settings = session.exec(
        select(GreenhouseSettings)
            .where(GreenhouseSettings.node_id == node_id)
            .order_by(GreenhouseSettings.id.desc())  
    ).first()

    if not latest_settings:
        raise HTTPException(
            status_code=404,
            detail=f"No settings found for node_id={node_id}",
        )

     # Convert `datetime.time` to `str` before returning the response
    response_data = GreenhouseSettingsResponse(
        **{
            k: (str(v) if isinstance(v, time) else v)  # Convert `time` to `str`
            for k, v in latest_settings.dict().items()
        }
    )

    return response_data

# Endpoint to set new settings for a specific node
@router.post("/{node_id}/settings", response_model=GreenhouseSettingsResponse)
def set_settings(
    node_id: int,
    new_settings: GreenhouseSettingsCreate,
    session=Depends(get_postgresql_session),
    current_user=Depends(get_current_user),
):
    # Create a new record with the appropriate node_id
    settings = GreenhouseSettings(
        node_id=node_id,
        **new_settings.dict(exclude_unset=True),
    )

    # Insert into the database
    session.add(settings)
    session.commit()
    session.refresh(settings)

    # Convert time fields to strings in the response
    response_data = {
        k: (str(v) if isinstance(v, time) else v)
        for k, v in settings.dict().items()
    }

    # Return the created settings as a response with converted time fields
    return GreenhouseSettingsResponse(**response_data)