import pandas as pd
import time
import threading
from datetime import datetime

# 定义数据列
data_columns = ["meter_id", "time", "reading"]

# 文件路径
LOCAL_DB_FILE = "local_db.csv"  # 存储所有的历史数据
DAILY_USAGE_FILE = "daily_usage.csv"  # 存储每日用电量

# **初始化 `local_db.csv`（如果文件不存在，则创建）**
try:
    local_db = pd.read_csv(LOCAL_DB_FILE)
except FileNotFoundError:
    local_db = pd.DataFrame(columns=data_columns)
    local_db.to_csv(LOCAL_DB_FILE, index=False)


# **从 `local_db.csv` 读取数据**
def load_data_store():
    try:
        return pd.read_csv(LOCAL_DB_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=data_columns)

# **计算每日用电量**
def calculate_daily_usage(data_store):
    if data_store.empty:
        print("No data available for daily usage calculation.")
        return

    data_store["time"] = pd.to_datetime(data_store["time"])
    today_str = datetime.now().strftime("%Y-%m-%d")

    # ✅ 计算 `reading` 增量，得到每日真实用电量
    data_store = data_store.sort_values(by=["meter_id", "time"])
    data_store["prev_reading"] = data_store.groupby("meter_id")["reading"].shift(1)
    data_store["daily_usage"] = data_store["reading"] - data_store["prev_reading"]
    data_store["daily_usage"].fillna(0, inplace=True) 

    daily_usage = data_store.groupby("meter_id")["daily_usage"].sum().reset_index()
    daily_usage["date"] = today_str

    try:
        try:
            daily_db = pd.read_csv(DAILY_USAGE_FILE)
        except FileNotFoundError:
            daily_db = pd.DataFrame(columns=["meter_id", "date", "daily_usage"])

        daily_db = pd.concat([daily_db, daily_usage], ignore_index=True)
        daily_db.to_csv(DAILY_USAGE_FILE, index=False)
        print(f"Daily usage saved for {today_str}")

    except Exception as e:
        print(f"Error saving daily usage: {e}")

# **归档 `data_store` 数据**
def archive_data():
    global data_store  # 允许修改全局变量

    if data_store.empty:
        print("No data to archive.")
        return

    try:
        today_str = datetime.now().strftime("%Y-%m-%d")

        # ✅ **第一步：存储 `data_store` 到本地 `local_db.csv`**
        data_store.to_csv(LOCAL_DB_FILE, mode='a', header=False, index=False)
        print(f"Data archived successfully for {today_str}.")

        # ✅ **第二步：计算日用电量**
        calculate_daily_usage(data_store)

        # ✅ **第三步：清空 `data_store`，准备新一天的数据**
        data_store = pd.DataFrame(columns=data_columns)  # 重新初始化 `data_store`
        print("data_store reset for new day.")

    except Exception as e:
        print(f"Error archiving data: {e}")

# **每天 00:00 进行数据归档**
def maintenance_scheduler():
    last_ran_date = None

    while True:
        now = datetime.now()
        # now = datetime(2025, 2, 16, 0, 30, 0) 
        today_str = now.strftime("%Y-%m-%d")

        if now.hour == 0 and now.minute == 0 and last_ran_date != today_str:
            print("Midnight maintenance started...")
            archive_data()
            last_ran_date = today_str  # 记录今天已执行
            time.sleep(60)  # 避免多次触发

        time.sleep(10)  # 每 10 秒检查一次

# **启动后台线程**
def start_maintenance_thread():
    maintenance_thread = threading.Thread(target=maintenance_scheduler, daemon=True)
    maintenance_thread.start()
    print("Data maintenance thread started.")

if __name__ == "__main__":
    start_maintenance_thread()
    # **保持主线程运行**
    while True:
        time.sleep(3600)
