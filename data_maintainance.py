import pandas as pd
import time
import threading
from datetime import datetime

# 定义数据列
data_columns = ["meter_id", "time", "reading"]

# 文件路径
LOCAL_DB_FILE = "local_db.csv"
DAILY_USAGE_FILE = "daily_usage.csv"

# **读取 `local_db.csv`（如果文件不存在，则创建）**
try:
    local_db = pd.read_csv(LOCAL_DB_FILE)
except FileNotFoundError:
    local_db = pd.DataFrame(columns=data_columns)
    local_db.to_csv(LOCAL_DB_FILE, index=False)

# **加载 `meter_reading.py` 里的数据**
def load_data_store():
    try:
        return pd.read_csv(LOCAL_DB_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=data_columns)

# **计算当天总用电量**
def calculate_daily_usage(data_store):
    if data_store.empty:
        print("No data available for daily usage calculation.")
        return

    data_store["time"] = pd.to_datetime(data_store["time"])
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_data = data_store[data_store["time"].dt.strftime("%Y-%m-%d") == today_str]

    if today_data.empty:
        print("No records found for today.")
        return

    daily_usage = today_data.groupby("meter_id")["reading"].sum().reset_index()
    daily_usage["date"] = today_str

    try:
        try:
            daily_db = pd.read_csv(DAILY_USAGE_FILE)
        except FileNotFoundError:
            daily_db = pd.DataFrame(columns=["meter_id", "date", "reading"])

        daily_db = pd.concat([daily_db, daily_usage], ignore_index=True)
        daily_db.to_csv(DAILY_USAGE_FILE, index=False)
        print(f"Daily usage saved for {today_str}")

    except Exception as e:
        print(f"Error saving daily usage: {e}")

# **归档 `data_store` 数据**
def archive_data():
    data_store = load_data_store()
    
    if data_store.empty:
        print("No data to archive.")
        return

    try:
        # 追加数据到 `local_db.csv`
        data_store.to_csv(LOCAL_DB_FILE, mode='a', header=False, index=False)
        print("Data archived successfully.")

        # 计算日用电量
        calculate_daily_usage(data_store)

        # **清空 `local_db.csv`，准备新一天的数据**
        pd.DataFrame(columns=data_columns).to_csv(LOCAL_DB_FILE, index=False)
        print("local_db.csv reset for new day.")

    except Exception as e:
        print(f"Error archiving data: {e}")

# **每天 00:00 - 00:59 进行数据归档**
def maintenance_scheduler():
    while True:
        current_time = datetime.now().strftime("%H:%M")
        if "00:00" <= current_time <= "00:59":
            print("Midnight maintenance started...")
            archive_data()
            time.sleep(60)

        time.sleep(10)

# **启动线程**
def start_maintenance_thread():
    maintenance_thread = threading.Thread(target=maintenance_scheduler, daemon=True)
    maintenance_thread.start()
    print("Data maintenance thread started.")

if __name__ == "__main__":
    start_maintenance_thread()

    # **让主线程保持运行**
    while True:
        time.sleep(3600)