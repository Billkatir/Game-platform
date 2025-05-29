from sqlmodel import SQLModel, Field
from datetime import time

class GreenhouseSettings(SQLModel, table=True):
    id: int = Field(primary_key=True)
    node_id: int 
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