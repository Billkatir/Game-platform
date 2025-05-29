import asyncio
import threading
import json
import os  # Add this import for file operations
import time
import collections
import statistics
from settings import GreenhouseSettings
from sqlmodel import select, Session
from database_operations import get_postgresql_session

class Node:
    def __init__(self, node_id, node_name, client):
        self.id = node_id
        self.settings = self.load_settings()
        self.client = client
        print(self.settings)
        self.name = node_name
        self.thread = threading.Thread(target=self.run_node_thread)
        self.thread.start()
        # Environment Attributes
        self.temperature = None
        self.humidity = None
        self.light = None
        self.wind = False
        self.rain = False
        self.cold_flag = False
        self.cold_main_heat = False
        self.cold_secondary_heat = False
        self.hum_main_heat = False
        self.hum_secondary_heat = False
        self.percentage = 100
        self.percentagecurtains = 99
        # curtains Usage Variables
        self.day = True
        # Task references for window operations
        self.window_open_task_1 = None
        self.window_open_task_2 = None
        self.window_open_task_3 = None
        self.window_close_task_1 = None
        self.window_close_task_2 = None
        self.window_close_task_3 = None
        self.main_heating_start_task_1 = None
        self.secondary_heating_start_task_1 = None
        self.main_heating_start_task_2 = None
        self.secondary_heating_start_task_2 = None
        self.curtains_open_task_1 = None
        self.curtains_pause_task = None
        self.curtains_close_task_1 = None
        self.curtains_close_task_2 = None
        self.curtains_close_task_3 = None
        # Attributes for publish the new state
        self.window_state = 2
        self.curtain_state = 2
        self.main_heat_state = 1
        self.secondary_heat_state = 1
        self.latest_windows = 2
        self.latest_curtains = 2
        self.latest_main_heat = 0
        self.latest_secondary_heat = 0
        self.latest_main_heat_op = 0
        self.latest_secondary_heat_op = 0
        self.latest_windows_op = 0
        self.latest_curtains_op = 0
        self.window_size = 5  # Hardcoded window size
        self.temperature_readings = collections.deque(maxlen=self.window_size)
        self.humidity_readings = collections.deque(maxlen=self.window_size)
        self.light_readings = collections.deque(maxlen=self.window_size)
        print (time.time())
        print("started node")

    async def run_node_async(self):
        while True:
            
            # self.check_change()
            self.settings = self.load_settings()
            if self.settings.window_manual_operation == 0:
                if not self.wind:
                    if not self.rain:
                        if not self.cold(self.cold_flag):
                            asyncio.create_task(self.open_window_1())  # Start the task without waiting
                        else:
                            asyncio.create_task(self.close_window_2())
                            if self.humidity_high():
                                asyncio.create_task(self.open_window_2())
                    else:
                        asyncio.create_task(self.close_window_3())
                        if not self.cold(self.cold_flag):
                            asyncio.create_task(self.open_window_3())
                        else :
                            asyncio.create_task(self.close_window_2())
                        if self.humidity_high():
                            asyncio.create_task(self.open_window_2())
                else:
                    asyncio.create_task(self.close_window_1())
            else:
                self.percentage = 50

            # curtains operations
            if self.settings.curtains_manual_operation == 0:
                if self.is_day(self.settings):
                    if self.light_position(self.settings) == 1:
                        asyncio.create_task(self.open_curtains_1())
                    elif self.light_position(self.settings) == 2:
                        asyncio.create_task(self.pause_curtains_1())
                    elif self.light_position(self.settings) == 3:
                        asyncio.create_task(self.close_curtains_1())
                else:
                    asyncio.create_task(self.close_curtains_2())
                    if self.humidity_high_2():
                        asyncio.create_task(self.close_curtains_3())
            else:
                self.percentagecurtains = 50
            ########
            if self.settings.main_heating_manual_operation == 0:
                if self.is_cold_heating(self.settings.main_heat_start_temp):
                    if self.main_heating_start_task_2:
                        self.main_heating_start_task_2.cancel()
                    asyncio.create_task(self.open_main_heating_1())
                else:
                    if self.main_heating_start_task_1:
                        self.main_heating_start_task_1.cancel()
                        self.main_heat_state = 1
                if self.is_humidity_heating(self.settings.main_heat_humidity_start):
                    asyncio.create_task(self.open_main_heating_2())
                else:
                    if self.main_heating_start_task_2:
                        self.main_heating_start_task_2.cancel()
                        self.main_heat_state = 1
            else :
                self.cold_main_heat = False
                self.hum_main_heat = False
                if self.main_heating_start_task_1:
                    self.main_heating_start_task_1.cancel()
                if self.main_heating_start_task_2:
                    self.main_heating_start_task_2.cancel()
            ############
            if self.settings.secondary_heating_manual_operation == 0:
                if self.is_cold_heating2(self.settings.secondary_heat_start_temp):
                    if self.secondary_heating_start_task_2:
                        self.secondary_heating_start_task_2.cancel()
                    asyncio.create_task(self.open_secondary_heating_1())
                else:
                    if self.secondary_heating_start_task_1:
                        self.secondary_heating_start_task_1.cancel()
                        self.secondary_heat_state = 1
                if self.is_humidity_heating2(self.settings.secondary_heat_humidity_start):
                    asyncio.create_task(self.open_secondary_heating_2())
                else:
                    if self.secondary_heating_start_task_2:
                        self.secondary_heating_start_task_2.cancel()
                        self.secondary_heat_state = 1
            
            else :
                self.cold_secondary_heat = False
                self.hum_secondary_heat = False
                if self.secondary_heating_start_task_1:
                    self.secondary_heating_start_task_1.cancel()
                if self.secondary_heating_start_task_2:
                    self.secondary_heating_start_task_2.cancel()
            
            if self.check_for_publish():
                data = {
                    'node_Id': str(self.id),  # Ensure node_Id is a string
                    'windows_state': str(self.window_state),  # Convert to string
                    'curtains_state': str(self.curtain_state)  # Convert to string
                }
                if self.settings.window_manual_operation != 0:
                    data['windows_state'] = str(self.settings.window_manual_operation)  # Ensure this is a string
                # Convert curtains_manual_operation to string if it's not zero
                if self.settings.curtains_manual_operation != 0:
                    data['curtains_state'] = str(self.settings.curtains_manual_operation)  # Ensure this is a string
                json_payload = json.dumps(data)  # Convert the dictionary to a JSON string
                self.publish_control_("/greenhouse/greenHub/v1/1/control", json_payload)  # Publish the JSON string
                
            await asyncio.sleep(0.5)  # Small sleep to prevent high CPU usage
            
            if self.check_for_publish2():
                data = {
                    'node_Id': str(self.id),  # Ensure node_Id is a string
                    'main_heating_state': str(self.main_heat_state),  # Convert to string
                    'secondary_heating_state': str(self.secondary_heat_state)  # Convert to string
                }
                if self.settings.main_heating_manual_operation != 0:
                    data['main_heating_state'] = str(self.settings.main_heating_manual_operation)  # Ensure this is a string
                # Convert curtains_manual_operation to string if it's not zero
                if self.settings.secondary_heating_manual_operation != 0:
                    data['secondary_heating_state'] = str(self.settings.secondary_heating_manual_operation)  # Ensure this is a string
                json_payload = json.dumps(data)
                self.publish_control_("/greenhouse/greenHub/v1/1/control_heating", json_payload)  # Publish the JSON string

    async def open_window_1(self):
        check = self.check_windows_operations()
        if 2 not in check and 3 not in check and 4 not in check and 5 not in check and 6 not in check:
            if (not self.window_open_task_1 or self.window_open_task_1.done()):
                self.window_open_task_1 = asyncio.create_task(self.perform_window_1_open())
                return await self.window_open_task_1

    async def perform_window_1_open(self):
        print("open windows /warm")
        self.percentage = 100
        self.window_state = 3
        await asyncio.sleep(self.settings.window_open_step)
        self.window_state = 2
        await asyncio.sleep(self.settings.window_sleep_step)
        return 100


    async def open_window_2(self):
        check = self.check_windows_operations()
        if 1 not in check and 3 not in check and 4 not in check and 5 not in check and 6 not in check:
            if (not self.window_open_task_2 or self.window_open_task_2.done()) and self.percentage == 0:
                self.window_open_task_2 = asyncio.create_task(self.perform_window_2_open())
                return await self.window_open_task_2

    async def perform_window_2_open(self):
        print("open windows /humidity/cold")
        self.percentage = 14
        self.window_state = 3
        await asyncio.sleep(self.settings.windows_open_rain)
        self.window_state = 2
        await asyncio.sleep(self.settings.humidity_windows_sleep_step)
        self.window_state = 1
        await asyncio.sleep(self.settings.windows_open_rain+10)
        self.window_state = 2
        await asyncio.sleep(self.settings.humidity_windows_sleep_step)
        self.percentage = 0
        return 0

    async def open_window_3(self):
        check = self.check_windows_operations()
        if 2 not in check and 1 not in check and 4 not in check and 5 not in check and 6 not in check:
            if (not self.window_open_task_3 or self.window_open_task_3.done()) and self.percentage == 0:
                self.window_open_task_3 = asyncio.create_task(self.perform_window_3_open())
                return await self.window_open_task_3

    async def perform_window_3_open(self):
        print("open windows /rain/warm")
        self.percentage = 15
        temp = self.percentage
        self.window_state = 3
        await asyncio.sleep(self.settings.windows_open_rain)
        self.window_state = 2
        return 15


    async def close_window_1(self):
        if (not self.window_close_task_1 or self.window_close_task_1.done()) and self.percentage != 0:
            self.stop_all_window_tasks_except(4)
            self.window_close_task_1 = asyncio.create_task(self.perform_window_1_close())
            return await self.window_close_task_1

    async def perform_window_1_close(self):
        print("close windows /wind")
        temp = self.percentage
        self.window_state = 1
        await asyncio.sleep(self.settings.windows_total_closing)
        self.window_state = 2
        self.percentage = 0
        return self.percentage

    async def close_window_2(self):
        check = self.check_windows_operations()
        if 4 not in check and 6 not in check:
            if (not self.window_close_task_2 or self.window_close_task_2.done()) and self.percentage > 14:
                self.stop_all_window_tasks_except(2,3,4,5,6)
                self.window_close_task_2 = asyncio.create_task(self.perform_window_2_close())
                return await self.window_close_task_2


    async def perform_window_2_close(self):
        print("close windows /cold")
        temp = self.percentage
        self.window_state = 1
        await asyncio.sleep(self.settings.windows_total_closing)
        self.window_state = 2
        self.percentage = 0
        return self.percentage

    async def close_window_3(self):
        check = self.check_windows_operations()
        if 4 not in check and 5 not in check:
            if (not self.window_close_task_3 or self.window_close_task_3.done()) and self.percentage > 15:
                self.stop_all_window_tasks_except(2,3,4,5,6)
                self.window_close_task_3 = asyncio.create_task(self.perform_window_3_close())
                return await self.window_close_task_3

    async def perform_window_3_close(self):
        print("close windows /rain")
        temp = self.percentage
        self.window_state = 1
        await asyncio.sleep(self.settings.windows_total_closing)
        self.window_state = 2
        self.percentage = 0
        return self.percentage


    # CURTAINS OPERATIONS

    async def open_curtains_1(self):
        if ((not self.curtains_open_task_1 or self.curtains_open_task_1.done()) and self.percentagecurtains !=100 ):
            if self.curtains_pause_task and not self.curtains_pause_task.done():
                self.curtains_pause_task.cancel()
            self.curtains_open_task_1 = asyncio.create_task(self.perform_curtains_1_open())
            return await self.curtains_open_task_1

    async def perform_curtains_1_open(self):
        print("light potition ", self.light_position(self.settings))
        print("curtains open /low_light")
        self.percentagecurtains = 10
        self.curtain_state = 3
        await asyncio.sleep(self.settings.curtains_total_closing)
        self.curtain_state = 2
        self.percentagecurtains = 100
        return self.percentagecurtains

    async def close_curtains_1(self):
        if ((not self.curtains_close_task_1 or self.curtains_close_task_1.done())and self.percentagecurtains !=15):
            if self.curtains_pause_task and not self.curtains_pause_task.done():
                self.curtains_pause_task.cancel()
            self.curtains_close_task_1 = asyncio.create_task(self.perform_curtains_1_close())
            return await self.curtains_close_task_1

    async def perform_curtains_1_close(self):
        print("light potition ", self.light_position(self.settings))
        print("curtains close /hight_light")
        self.percentagecurtains = 90
        self.curtain_state = 1
        await asyncio.sleep(self.settings.curtains_total_closing)
        self.curtain_state = 2
        await asyncio.sleep(5)
        self.curtain_state = 3
        await asyncio.sleep(self.settings.curtains_open_after_closing)
        self.curtain_state = 2
        self.percentagecurtains = 15
        return self.percentagecurtains

    async def close_curtains_2(self):
        if ((not self.curtains_close_task_2 or self.curtains_close_task_2.done()) and self.percentagecurtains != 0):
            self.curtains_close_task_2 = asyncio.create_task(self.perform_curtains_2_close())
            return await self.curtains_close_task_2

    async def perform_curtains_2_close(self):
        print("light potition ", self.light_position(self.settings))
        print("curtains close 2")
        self.percentagecurtains = 90
        temp = self.percentagecurtains
        self.curtain_state = 1
        await asyncio.sleep(self.settings.curtains_total_closing)
        self.curtain_state = 2
        self.percentagecurtains = 0
        return self.percentagecurtains

    async def pause_curtains_1(self):
        print("light potition ", self.light_position(self.settings))
        print("going to stop")
        if ((not self.curtains_pause_task or self.curtains_pause_task.done()) and self.percentagecurtains != 46):
            if (self.curtains_open_task_1 and not self.curtains_open_task_1.done()):
                self.curtains_open_task_1.cancel()
            if (self.curtains_close_task_1 and not self.curtains_close_task_1.done()):
                self.curtains_close_task_1.cancel()
            self.curtains_pause_task = asyncio.create_task(self.perform_curtains_pause())
            return await self.curtains_pause_task

    async def perform_curtains_pause(self):
        print("light potition ", self.light_position(self.settings))
        print("curtains pause")
        self.curtain_state = 2
        self.percentagecurtains = 46

    async def close_curtains_3(self):
        if ((not self.curtains_close_task_3 or self.curtains_close_task_3.done()) and self.percentagecurtains == 0):
            self.curtains_close_task_3 = asyncio.create_task(self.perform_curtains_3_close())
            return await self.curtains_close_task_3

    async def perform_curtains_3_close(self):
        print("curtains close 3")
        self.curtain_state = 3
        await asyncio.sleep(self.settings.curtains_open_humidity)
        self.curtain_state = 2
        await asyncio.sleep(self.settings.humidity_curtains_sleep_step)
        self.curtain_state = 1
        await asyncio.sleep(self.settings.curtains_open_humidity+5)
        self.curtain_state = 2
        await asyncio.sleep(self.settings.humidity_curtains_cycle_await)
        self.percentagecurtains = 0
        return self.percentagecurtains


    # Heating operations
    
    
    
    async def open_main_heating_1(self):
        if ((not self.main_heating_start_task_1 or self.main_heating_start_task_1.done())):
            self.main_heating_start_task_1 = asyncio.create_task(self.perform_main_heating_1())
            return await self.main_heating_start_task_1

    async def perform_main_heating_1(self):
        for _ in range(5):
            if not self.is_cold_heating(self.settings.main_heat_start_temp):
                if self.main_heating_start_task_1:
                    self.main_heating_start_task_1.cancel()
                return  # Stop the function execution
            await asyncio.sleep(0.5)
            print("open 1")
        self.main_heat_state = 2
        await asyncio.sleep(self.settings.main_heat_max_time)
        print("close 1")
        self.main_heat_state = 1
        await asyncio.sleep(self.settings.main_heat_pause_time)
        return
    
    async def open_secondary_heating_1(self):
        if ((not self.secondary_heating_start_task_1 or self.secondary_heating_start_task_1.done())):
            self.secondary_heating_start_task_1 = asyncio.create_task(self.perform_secondary_heating_1())
            return await self.secondary_heating_start_task_1

    async def perform_secondary_heating_1(self):
        for _ in range(5):
            if not self.is_cold_heating2(self.settings.secondary_heat_start_temp):
                if self.secondary_heating_start_task_1:
                    self.secondary_heating_start_task_1.cancel()
                return  # Stop the function execution
            await asyncio.sleep(0.5)
        self.secondary_heat_state = 2
        await asyncio.sleep(self.settings.secondary_heat_max_time)
        self.secondary_heat_state = 1
        await asyncio.sleep(self.settings.secondary_heat_pause_time)
        return
    
    async def open_main_heating_2(self):
        if ((not self.main_heating_start_task_2 or self.main_heating_start_task_2.done())):
            self.main_heating_start_task_2 = asyncio.create_task(self.perform_main_heating_2())
            return await self.main_heating_start_task_2

    async def perform_main_heating_2(self):
        for _ in range(5):
            if not self.is_humidity_heating(self.settings.main_heat_humidity_start):
                if self.main_heating_start_task_2:
                    self.main_heating_start_task_2.cancel()
                return  # Stop the function execution
            await asyncio.sleep(0.5)
        self.main_heat_state = 2
        print("open 2")
        await asyncio.sleep(self.settings.main_heat_humidity_max_time)
        self.main_heat_state = 1
        print("close 2")
        await asyncio.sleep(self.settings.main_heat_humidity_pause_time)
        return
    
    async def open_secondary_heating_2(self):
        if ((not self.secondary_heating_start_task_2 or self.secondary_heating_start_task_2.done())):
            self.secondary_heating_start_task_2 = asyncio.create_task(self.perform_secondary_heating_2())
            return await self.secondary_heating_start_task_2

    async def perform_secondary_heating_2(self):
        for _ in range(5):
            if not self.is_humidity_heating(self.settings.secondary_heat_humidity_start):
                if self.secondary_heating_start_task_2:
                    self.secondary_heating_start_task_2.cancel()
                return  # Stop the function execution
            await asyncio.sleep(0.5)
        self.secondary_heat_state = 2
        await asyncio.sleep(self.settings.secondary_heat_humidity_max_time)
        self.secondary_heat_state = 1
        await asyncio.sleep(self.settings.secondary_heat_humidity_pause_time)
        return

       

    #
    # -------------------------------------------
    #
    def check_for_publish(self):
        temp = False
        if self.settings.curtains_manual_operation != self.latest_curtains_op:
            self.latest_curtains_op = self.settings.curtains_manual_operation
            temp = True
        if self.settings.window_manual_operation != self.latest_windows_op:
            self.latest_windows_op = self.settings.window_manual_operation
            temp = True
        if self.curtain_state != self.latest_curtains:
            self.latest_curtains = self.curtain_state
            temp = True
        if self.window_state != self.latest_windows:
            self.latest_windows = self.window_state
            temp = True
        return temp
    
    def check_for_publish2(self):
        temp = False
        if self.settings.main_heating_manual_operation != self.latest_main_heat_op:
            self.latest_main_heat_op = self.settings.main_heating_manual_operation
            temp = True
        if self.settings.secondary_heating_manual_operation != self.latest_secondary_heat_op:
            self.latest_secondary_heat_op = self.settings.secondary_heating_manual_operation
            temp = True
        if self.main_heat_state != self.latest_main_heat:
            self.latest_main_heat = self.main_heat_state
            temp = True
        if self.secondary_heat_state != self.latest_secondary_heat:
            self.latest_secondary_heat = self.secondary_heat_state
            temp = True
        return temp


    def publish_control_(self, topic, payload):
        self.client.publish_control(topic, payload)

    def is_humidity_heating(self,hum):
            if(self.humidity > hum):
                self.hum_main_heat = True
                return True
            if self.hum_main_heat == True:
                if(self.humidity > self.settings.main_heat_humidity_stop):
                    return True
                else:
                    self.hum_main_heat = False
                    return False
            self.hum_main_heat = False
            return False
    
    def is_humidity_heating2(self,hum):
            if(self.humidity > hum):
                self.hum_secondary_heat = True
                return True
            if self.hum_secondary_heat == True:
                if(self.humidity > self.settings.secondary_heat_humidity_stop):
                    return True
                else:
                    self.hum_secondary_heat = False
                    return False
            self.hum_secondary_heat = False
            return False

    def is_cold_heating(self,temp):
            if(self.temperature < temp):
                self.cold_main_heat = True
                return True
            if self.cold_main_heat == True:
                if(self.temperature < self.settings.main_heat_stop_temp):
                    return True
                else:
                    self.cold_main_heat = False
                    return False
            self.cold_main_heat = False
            return False
    
    def is_cold_heating2(self,temp):
            if(self.temperature < temp):
                self.cold_secondary_heat = True
                return True
            if self.cold_secondary_heat == True:
                if(self.temperature < self.settings.secondary_heat_stop_temp):
                    return True
                else:
                    self.cold_secondary_heat = False
                    return False
            self.cold_secondary_heat = False
            return False
        
    
    def cold(self,cold_flag):
        if(self.temperature > self.settings.upper_temperature) :
            cold_flag = False
        if(self.temperature < self.settings.lower_temperature) :
            cold_flag = True
        self.cold_flag = cold_flag
        return cold_flag

    def humidity_high(self):
        if(self.humidity > self.settings.upper_humidity_windows) :
            return True
        else :
            return False
    
    def humidity_high_2(self):
        if(self.humidity > self.settings.upper_humidity_curtains) :
            return True
        else :
            return False

    def update_environment(self, temperature, humidity):
        print(f"New temperature: {temperature}, New humidity: {humidity}")
        self.temperature = temperature
        self.humidity = humidity


    def update_light(self, light_intensity):
        print("New light: ", light_intensity)
        self.light_readings.append(light_intensity)
        
        if len(self.light_readings) < self.window_size:
            # If there are not enough readings, just assign the current intensity
            self.light = light_intensity
        else:
            # Convert the deque to a list to allow slicing and sorting
            recent_readings = list(self.light_readings)[-self.window_size:]
            sorted_light = sorted(recent_readings)
            middle_index = len(sorted_light) // 2
            self.light = sorted_light[middle_index]
            print(f"Filtered light intensity (Middle Value): {self.light}")




    def update_weather(self, is_windy, is_raining):
        self.wind = is_windy
        self.rain = is_raining


    def is_day(self, sets):
        now = time.localtime()
        current_time = (now.tm_hour+2)*100 + now.tm_min
        dayStart = sets.day_start.hour*100 + sets.day_start.minute
        nightStart = sets.night_start.hour*100 + sets.night_start.minute
        if dayStart < nightStart:
            return dayStart <= current_time < nightStart
        else:
            return current_time >= dayStart or current_time < nightStart

    def light_position(self, sets):        #return 1/2/3         depending how much light there is       1<lower_light      /   lower_light<2<upper_light    / upper_light<3
        if not self.light == None and not self.light == 54612 :
            if self.light<sets.lower_light:
                return 1
            elif sets.lower_light<self.light<sets.upper_light: 
                return 2
            elif sets.upper_light<self.light:
                return 3
        return 0

    def load_settings(self):
        try:
            with get_postgresql_session() as session:
                # Fetch the latest settings for the node
                result = session.execute(
                    select(GreenhouseSettings)
                    .where(GreenhouseSettings.node_id == self.id)
                    .order_by(GreenhouseSettings.id.desc())
                ).fetchone()

            if result:
                # Extract the GreenhouseSettings instance
                settings = result[0]
                return settings
            else:
                # Handle the case where no settings are found
                print("")
                return None
        except Exception as e:
            print(f"Exception while loading settings for node {self.id}: {str(e)}")
            return None


    def check_windows_operations(self):
        running_operations = []
        running_operations.append(0)
        if self.window_open_task_1 and not self.window_open_task_1.done():
            running_operations.append(1)
        if self.window_open_task_2 and not self.window_open_task_2.done():
            running_operations.append(2)
        if self.window_open_task_3 and not self.window_open_task_3.done():
            running_operations.append(3)
        if self.window_close_task_1 and not self.window_close_task_1.done():
            running_operations.append(4)
        if self.window_close_task_2 and not self.window_close_task_2.done():
            running_operations.append(5)
        if self.window_close_task_3 and not self.window_close_task_3.done():
            running_operations.append(6)

        return running_operations


    def stop_all_window_tasks_except(self, *nums):
        # Convert nums to a set for efficient lookup
        nums_to_exclude = set(nums)

        tasks = [
            self.window_open_task_1,
            self.window_open_task_2,
            self.window_open_task_3,
            self.window_close_task_1,
            self.window_close_task_2,
            self.window_close_task_3
        ]

        # Iterate through the tasks and cancel all except the specified ones
        for i, task in enumerate(tasks, start=1):
            if i not in nums_to_exclude and task and not task.done():
                task.cancel()



    def run_node_thread(self):
        asyncio.run(self.run_node_async())

    def __repr__(self):
        return f"Node(id={self.id}, name={self.name})"
