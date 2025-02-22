from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
from datetime import datetime
import random
from concurrent.futures import ThreadPoolExecutor
import time
import threading
from datetime import datetime
from data_maintenance import archive_data
import os
import logging



app = Flask(__name__)


# ---------------logs----------------
# 配置日志
logging.basicConfig(
    filename='server.log',  # 日志文件
    level=logging.INFO,  # 日志级别
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)

# 记录每个请求的信息
@app.before_request
def log_request_info():
    log_data = {
        "IP": request.remote_addr,
        "Method": request.method,
        "Path": request.path,
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Args": request.args.to_dict(),
        "Data": request.get_json() if request.is_json else request.form.to_dict()
    }
    logging.info(f"Request: {log_data}")

# ---------------logs----------------



# Sample data to simulate database
users = [
    {
        "username": "John Doe",
        "meter_id": "123-456-789",
        "dwelling_type": "Apartment",
        "region": "Central",
        "area": "Downtown",
        "community": "Greenfield",
        "unit": "A1",
        "floor": "5",
        "email": "john@example.com",
        "tel": "123-456-7890",
        "reading": 0  # Initial reading value
    }
]

dwelling_types = [
    "1-room / 2-room", 
    "3-room", 
    "4-room", 
    "5-room and Executive", 
    "Landed Properties", 
    "Private Apartments and Condominiums"
]

regions = ["Central", "East", "West", "North","South"]

METER_CSV_PATH = 'meter_id.csv'
LOCAL_DB_FILE = "local_db.csv"

#初始化临时dataframe

data_columns = ["meter_id", "time", "reading"]
data_store = pd.DataFrame(columns=data_columns)

#读取本地database为dataframe
local_db = pd.read_csv('local_db.csv')



def save_meter_id_to_csv(meter_id, reading):
    """
    这是一个将新用户meter_id以dataframe形式储存到memory中，并同时将日期保存为当天0点，电表读数初始化为0.
    随其他meterreading记录存储时保存在本地。
    """
    global data_store
    try:
        timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        # Check if the CSV file exists
        #try:
            #meter_df = pd.read_csv('local_db.csv', dtype=str)  # Ensure all data is read as strings
        #except FileNotFoundError:
            # If file doesn't exist, create a new one with headers
            #meter_df = pd.DataFrame(columns=["meter_id", "time", "reading"], dtype=str)

        # Append the new meter_id, timestamp, and reading to the DataFrame
        new_row = pd.DataFrame({"meter_id": [meter_id], "time": [timestamp], "reading": [str(reading)]}, dtype=str)
        
        data_store = pd.concat([data_store, new_row], ignore_index=True)
        print(new_row)

        # Save DataFrame to CSV file as text (all columns are treated as strings)
        #meter_df.to_csv('meter_id.csv', index=False, header=True, encoding='utf-8')
    except Exception as e:
        print(f"Error saving meter_id: {e}")

#创建线程池
executor = ThreadPoolExecutor(max_workers=10)

def store_data_in_df(data):
    """后台线程用来处理数据存储。将新输入的meterreading保存到临时dataframe中，并同步更新users的reading"""
    global data_store, users
    
    print("Storing new meter reading:", data)
    time.sleep(1)

    # 追加数据到 data_store
    data_store = pd.concat([data_store, data], ignore_index=True)

    if os.path.exists('local_db.csv'):
        # Read existing CSV file
        d = pd.read_csv('local_db.csv')
        # Append new data
        data_new = pd.concat([d, data_store], ignore_index=True)
    else:
        # Create new DataFrame if file doesn't exist
        data_new =data_store

    #data_new.to_csv('local_db.csv', index=False)
    
    # 更新 users 里的 reading 值
    for index, row in data_store.iterrows():
        meter_id = row["meter_id"]
        new_reading = row["reading"]

        # **正确写法：用 loc 直接更新 DataFrame**
        users.loc[users["meter_id"] == meter_id, "reading"] = new_reading
        print(f"Updated {meter_id} reading in users: {new_reading}")

    data_store = pd.DataFrame(columns=data_columns)
    
    # **同步保存到 CSV**
    save_users_to_csv()


    print("Data stored successfully!")


# **后台线程：每天 00:00 - 00:59 自动存储数据**
def scheduled_task():
    while True:
        current_time = datetime.now()
        if current_time.hour == 0:  # 00:00 触发
            print(f"Running data maintenance at {current_time}")
            archive_data()  # 数据归档
            time.sleep(60)  # 避免多次触发，暂停 1 分钟
        time.sleep(600)  # 每 10 分钟检查一次

# 启动后台线程
maintenance_thread = threading.Thread(target=scheduled_task, daemon=True)
maintenance_thread.start()

@app.route('/')
def index():
    """Main Page"""
    return render_template('index.html')


@app.route('/meterreading', methods=['GET','POST'])
def meter_reading():
    
    global data_store

    if request.method == 'GET':
        return render_template('meter_reading.html')
    
    elif request.method == 'POST':

        data = request.get_json()
        if not all(k in data for k in ("meter_id", "time", "reading")):
            return jsonify({"status": "error", "message": "Please fill out all blanks."}), 400

        meter_id = data["meter_id"]
        time = data["time"]
        reading = data["reading"]

        #check meterID是否存在于users
        if meter_id not in users["meter_id"].values:
            return jsonify({"status": "error", "message": "You are not registered. Please register first."}), 403

        
        #check 时间是否在12点到1点
        time_obj = datetime.strptime(time, "%Y-%m-%dT%H:%M") 
        formatted_time = time_obj.strftime('%Y-%m-%d %H:%M:%S')

        if time_obj.hour == 0 and time_obj.minute > 0:
            return jsonify({"status": "error", "message": "System maintenance in progress. Please try again after 1am."}), 403
        elif time_obj.hour == 1 and time_obj.minute == 0:
            return jsonify({"status": "error", "message": "System maintenance in progress. Please try again after 1am."}), 403

        
        # 追加数据到 `data_store`，然后同步更新 `users`
        new_data = pd.DataFrame([{"meter_id": meter_id, "time": formatted_time, "reading": reading}])

        # 启动线程存储数据并 **同步 `users` 里的 `reading`
        executor.submit(store_data_in_df, new_data)

        # `users` 里同步 `reading` 更新
        users.loc[users["meter_id"] == str(meter_id), "reading"] = reading  
        print(f"Updated {meter_id} reading in users: {reading}")  # 调试信息


        # 让用户知道 `reading` 已被正确存储
        return jsonify({"status": "success", "message": f"New reading saved: {meter_id}, {formatted_time}, {reading}"}), 201

import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime, timedelta

LOCAL_DB_FILE = "local_db.csv"
DAILY_USAGE_FILE = "daily_usage.csv"

import matplotlib.pyplot as plt
@app.route('/query_usage', methods=['GET', 'POST'])
def query_usage():
    if request.method == 'GET':
        return render_template('query_usage.html', plot_url=None, total_usage=None)
    
    meter_id = request.form.get('meter_id', '').strip()
    time_range = request.form.get('time_range', 'today')
    start_date_str = request.form.get('start_date', '')
    end_date_str = request.form.get('end_date', '')

    if not meter_id:
        return render_template('query_usage.html', error="Meter ID is required!", plot_url=None, total_usage=None)
    
    df = pd.read_csv(LOCAL_DB_FILE)
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time'])
    df = df[df['meter_id'] == meter_id]

    if df.empty:
        return render_template('query_usage.html', error=f"No data found for meter_id: {meter_id}", plot_url=None, total_usage=None)

    now = datetime.now()
    
    if time_range == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59)  # 覆盖整个今天
    elif time_range == 'last_week':
        end_date = now.replace(hour=23, minute=59, second=59) 
        start_date = end_date - timedelta(days=7)
    elif time_range == 'last_month':
        end_date = now.replace(hour=23, minute=59, second=59) 
        start_date = end_date - timedelta(days=30)
    else:
        try:
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)
            else:
                return render_template('query_usage.html', error="Please select both start and end date for custom range.", plot_url=None, total_usage=None)
        except ValueError:
            return render_template('query_usage.html', error="Invalid date format. Please use YYYY-MM-DD.", plot_url=None, total_usage=None)

    mask = (df['time'] >= start_date) & (df['time'] <= end_date)
    df_range = df.loc[mask].copy()

    if df_range.empty:
        return render_template('query_usage.html', error="No meter readings found in the selected date range.", plot_url=None, total_usage=None)

    df_range.sort_values(by='time', inplace=True)
    df_range['reading'] = pd.to_numeric(df_range['reading'], errors='coerce').fillna(0)
    df_range['usage'] = df_range['reading'].diff().fillna(0)
    
    #删除第一根柱子
    df_range = df_range.iloc[1:]

    #当last week 和 last month时，只查询当天使用电量
    if time_range in ['last_week', 'last_month']:
        # 提取日期部分
        df_range['date'] = df_range['time'].dt.date  
        
        # 按日期求和
        df_daily = df_range.groupby('date', as_index=False)['usage'].sum()
        
        # 更新 x_data 和 y_data
        x_data = df_daily['date'].astype(str).tolist()  # 转换为字符串以显示在 x 轴
        y_data = df_daily['usage'].tolist()
    else:
        df_range['time_str'] = df_range['time'].dt.strftime('%m-%d %H:%M')
        x_data = df_range['time_str'].tolist()
        y_data = df_range['usage'].tolist()

    total_usage = sum(y_data)

    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(x_data, y_data, color='royalblue')

    # 只在非零柱子上标注数值
    for bar in bars:
        height = bar.get_height()
        if height > 0:  # 只显示非零数值
            ax.annotate(f'{height:.2f}', 
                        xy=(bar.get_x() + bar.get_width() / 2, height), 
                        xytext=(0, 5), 
                        textcoords='offset points',
                        ha='center', 
                        fontsize=10, 
                        color='black')

    ax.set_title(f"Electricity Usage for Meter {meter_id}")
    ax.set_xlabel("Time")
    ax.set_ylabel("Usage (kWh)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
    plot_url = "data:image/png;base64," + encoded
    plt.close(fig)

    return render_template('query_usage.html', plot_url=plot_url, total_usage=total_usage)

# -------------user_management start----------------

# 定义 CSV 文件路径
USERS_CSV_FILE = 'users.csv'

# **尝试加载本地用户数据为 DataFrame**
if os.path.exists(USERS_CSV_FILE):
    users = pd.read_csv(USERS_CSV_FILE, dtype={"meter_id": str})  # 强制 meter_id 为整数
else:
    users = pd.DataFrame(columns=[
        "username", "meter_id", "dwelling_type", "region", "area", "community",
        "unit", "floor", "email", "tel", "reading", "time"
    ])



def save_users_to_csv():
    """
    将 `users` 数据保存到 CSV 文件，以防止数据丢失。
    """
    users.to_csv(USERS_CSV_FILE, index=False, encoding='utf-8')


@app.route('/register', methods=['GET', 'POST'])
def register():
    global users
    if request.method == 'GET':
        return render_template('register.html', dwelling_types=dwelling_types, regions=regions)

    if request.method == 'POST':
        timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        user_data = pd.DataFrame([{
            "username": request.form['username'].strip(),
            "meter_id": request.form['meter_id'].strip(),  
            "dwelling_type": request.form['dwelling_type'].strip(),
            "region": request.form['region'].strip(),
            "area": request.form['area'].strip(),
            "community": request.form['community'].strip(),
            "unit": request.form['unit'].strip(),
            "floor": request.form['floor'].strip(),
            "email": request.form['email'].strip(),
            "tel": request.form['tel'].strip(),
            "reading": 0,  # 初始读数设为 0
            "time": timestamp
        }])
        if request.form['meter_id'].strip() in users['meter_id'].values:
            return "The Meter ID has been registered，please use other Meter ID.", 400

        users = pd.concat([users, user_data], ignore_index=True)
        save_users_to_csv()  # 保存到本地 CSV
        save_meter_id_to_csv(request.form['meter_id'].strip(), 0)  # Save the initial reading (0)

        user_dict = user_data.iloc[0].to_dict()
        return render_template('register_success.html', user=user_dict)

@app.route('/view_user', methods=['GET', 'POST'])
def view_user():
    global users
    if request.method == 'GET':
        return render_template('view_user.html')

    if request.method == 'POST':
        meter_id = request.form.get('meter_id', '').strip()
        user = users[users["meter_id"] == meter_id].to_dict(orient="records")  # **转换为字典列表**
        if user:
            user_dict = user[0]
            return render_template('view_user.html',
                                   user_info=user_dict)
        else:
            return render_template('view_user.html',
                                   not_found=True,
                                   meter_id=meter_id)

# -------------user_management end----------------

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
