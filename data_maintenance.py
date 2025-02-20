import pandas as pd
import time
import threading
from datetime import datetime
datetime.now().strftime("%H:%M")
import pandas as pd
import os

# format of daily_usage.csv
data_columns = ["meter_id", "time", "reading"]


current_dir = os.path.dirname(os.path.abspath(__file__))  
LOCAL_DB_FILE = os.path.join(current_dir, "local_db.csv")
DAILY_USAGE_FILE = os.path.join(current_dir, "daily_usage.csv")

# load `local_db.csv`
def load_data_store():
    try:
        return pd.read_csv(LOCAL_DB_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=data_columns)

# get daily electrivity usage
def calculate_daily_usage(data_store):
    """Calculate daily usage from data_store"""
    if data_store.empty:
        print("No data available for daily usage calculation.")
        return

    data_store["time"] = pd.to_datetime(data_store["time"])
    
    data_store['date'] = data_store['time'].dt.date
    latest_readings = (data_store.sort_values('time')
                      .groupby(['meter_id', 'date'])
                      .last()
                      .reset_index())
    
    latest_readings['time'] = latest_readings['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    latest_readings = latest_readings[['meter_id', 'time', 'reading']]

    latest_readings.to_csv(DAILY_USAGE_FILE, index=False)
    
    print(f"Daily usage data updated with {len(latest_readings)} records")


# archive `data_store` 
def archive_data():
    data_store = load_data_store()
    if data_store.empty:
        print(" No unarchived data found.")
        return

    try:
        # daily_usage for calculation
        calculate_daily_usage(data_store)
        # clear data_store
        print(" Data store cleared after archiving.")

    except Exception as e:
        print(f" Error archiving data: {e}")

# Check for unarchived data at power-up and performs archiving
def check_and_archive_on_startup():
    print(" System startup: Checking for unarchived data...")
    archive_data()


# archive from 00:00 to 00:59 every day
def maintenance_scheduler():
    while True:
        #current_time = "01:00"
        current_time = datetime.now().strftime("%H:%M")
        if "00:00" <= current_time <= "00:59":
            print(" Midnight maintenance started...")
            archive_data()
            time.sleep(60)

        time.sleep(10)

# start thread
def start_maintenance_thread():
    maintenance_thread = threading.Thread(target=maintenance_scheduler, daemon=True)
    maintenance_thread.start()
    print(" Data maintenance thread started.")

#  data archive during maintenance time and after turn on
if __name__ == "__main__":
    print(" System startup: Checking for unarchived data...")
    check_and_archive_on_startup()  
    start_maintenance_thread()

    while True:
        time.sleep(3600)