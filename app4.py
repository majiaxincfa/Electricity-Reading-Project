import os
import logging
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ============ 全局常量与初始化 =============
LOCAL_DB_FILE = "local_db.csv"
DAILY_USAGE_FILE = "daily_usage.csv"
USERS_CSV_FILE = "users.csv"

data_columns = ["meter_id", "time", "reading"]

# 如果 local_db.csv 不存在，创建一个空的
if not os.path.exists(LOCAL_DB_FILE):
    pd.DataFrame(columns=data_columns).to_csv(LOCAL_DB_FILE, index=False)

# 如果 daily_usage.csv 不存在，创建一个空的
if not os.path.exists(DAILY_USAGE_FILE):
    pd.DataFrame(columns=data_columns).to_csv(DAILY_USAGE_FILE, index=False)

# 如果 users.csv 不存在，创建一个空的
if not os.path.exists(USERS_CSV_FILE):
    pd.DataFrame(columns=[
        "username", "meter_id", "dwelling_type", "region", "area",
        "community", "unit", "floor", "email", "tel", "reading", "time"
    ]).to_csv(USERS_CSV_FILE, index=False)

# 读取用户信息
users = pd.read_csv(USERS_CSV_FILE, dtype={"meter_id": str})

# ===== 日志配置 =====
logging.basicConfig(
    filename='server.log',  # 日志文件
    level=logging.INFO,     # 日志级别
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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


# ============ 工具函数：归档与清空 =============
def load_data_store():
    """从 local_db.csv 加载当前所有半小时读数"""
    try:
        return pd.read_csv(LOCAL_DB_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=data_columns)

def calculate_daily_usage(data_store):
    """
    根据 current data_store 中每个 meter 的最新读数，写入 daily_usage.csv。
    这里的做法是：按 (meter_id, date) 分组，提取最后一次读数。
    """
    if data_store.empty:
        print("No data available for daily usage calculation.")
        return

    data_store["time"] = pd.to_datetime(data_store["time"])
    
    # 提取 date
    data_store['date'] = data_store['time'].dt.date
    # 按 meter_id, date 排序后取最后一条
    latest_readings = (data_store.sort_values('time')
                       .groupby(['meter_id', 'date'])
                       .last()
                       .reset_index())

    # 把 time 转为字符串
    latest_readings['time'] = latest_readings['time'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # 只保留所需列
    latest_readings = latest_readings[['meter_id', 'time', 'reading']]

    # 将结果追加到 daily_usage.csv
    if os.path.exists(DAILY_USAGE_FILE):
        daily_df = pd.read_csv(DAILY_USAGE_FILE)
        combined_df = pd.concat([daily_df, latest_readings], ignore_index=True)
        combined_df.to_csv(DAILY_USAGE_FILE, index=False)
    else:
        latest_readings.to_csv(DAILY_USAGE_FILE, index=False)

    print(f"Daily usage data updated with {len(latest_readings)} records.")


def archive_data():
    """
    将 local_db.csv 的数据进行日度归档，然后清空 local_db.csv。
    """
    data_store = load_data_store()
    if data_store.empty:
        print("No unarchived data found in local_db.csv.")
        return

    try:
        # 1) 根据 data_store 计算每日最新读数并写入 daily_usage.csv
        calculate_daily_usage(data_store)

        # 2) 清空 local_db.csv，让它重新接收当天的半小时数据
        pd.DataFrame(columns=data_columns).to_csv(LOCAL_DB_FILE, index=False)
        print("local_db.csv has been cleared after archiving.")
    except Exception as e:
        print(f"Error archiving data: {e}")


def scheduled_task():
    """
    后台线程：每天 00:00 - 00:59 间，每隔10分钟检查一次，
    如果到达 0点时段，就调用 archive_data()，并 sleep 1分钟防止多次重复触发。
    """
    while True:
        current_time = datetime.now()
        # 如果当前处在 0点~0:59 范围内
        if current_time.hour == 0:
            print(f"Running daily data maintenance at {current_time}")
            archive_data()
            # 避免重复多次触发
            time.sleep(60)
        time.sleep(600)  # 每10分钟检查一次


# 后台线程启动
maintenance_thread = threading.Thread(target=scheduled_task, daemon=True)
maintenance_thread.start()


# ============ 线程池与数据处理 =============
executor = ThreadPoolExecutor(max_workers=10)

def save_users_to_csv():
    """将 `users` 数据保存到 CSV 文件，以防止数据丢失。"""
    users.to_csv(USERS_CSV_FILE, index=False, encoding='utf-8')


def store_data_in_df(new_data):
    """
    后台线程用来处理保存半小时meter reading到 local_db.csv。
    并更新 users 中对应 meter_id 的 reading
    """
    time.sleep(1)  # 模拟写入延迟
    print("Storing new meter reading:", new_data)

    if os.path.exists(LOCAL_DB_FILE):
        df_existing = pd.read_csv(LOCAL_DB_FILE)
        updated_df = pd.concat([df_existing, new_data], ignore_index=True)
    else:
        updated_df = new_data

    updated_df.to_csv(LOCAL_DB_FILE, index=False)

    # 同步更新 users
    global users
    for idx, row in new_data.iterrows():
        meter_id = str(row["meter_id"])
        new_reading = row["reading"]
        users.loc[users["meter_id"] == meter_id, "reading"] = new_reading

    save_users_to_csv()
    print("Data stored successfully in local_db.csv.")


# ============ 路由：主页 ============
@app.route('/')
def index():
    return render_template('index.html')


# ============ 路由：登记新用户 ============
dwelling_types = [
    "1-room / 2-room", 
    "3-room", 
    "4-room", 
    "5-room and Executive", 
    "Landed Properties", 
    "Private Apartments and Condominiums"
]
regions = ["Central", "East", "West", "North","South"]

@app.route('/register', methods=['GET', 'POST'])
def register():
    global users
    if request.method == 'GET':
        return render_template('register.html', dwelling_types=dwelling_types, regions=regions)

    if request.method == 'POST':
        timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        meter_id = request.form['meter_id'].strip()
        if meter_id in users['meter_id'].values:
            return "The Meter ID has been registered, please use another.", 400

        user_data = pd.DataFrame([{
            "username": request.form['username'].strip(),
            "meter_id": meter_id,
            "dwelling_type": request.form['dwelling_type'].strip(),
            "region": request.form['region'].strip(),
            "area": request.form['area'].strip(),
            "community": request.form['community'].strip(),
            "unit": request.form['unit'].strip(),
            "floor": request.form['floor'].strip(),
            "email": request.form['email'].strip(),
            "tel": request.form['tel'].strip(),
            "reading": 0,  # 初始读数
            "time": timestamp
        }])

        users = pd.concat([users, user_data], ignore_index=True)
        save_users_to_csv()

        # 也可以在 local_db.csv 初始化一行，但不是强制
        # 这里可省略或自行决定是否写入。

        user_dict = user_data.iloc[0].to_dict()
        return render_template('register_success.html', user=user_dict)


# ============ 路由：查看用户信息 ============
@app.route('/view_user', methods=['GET', 'POST'])
def view_user():
    global users
    if request.method == 'GET':
        return render_template('view_user.html')

    if request.method == 'POST':
        meter_id = request.form.get('meter_id', '').strip()
        user = users[users["meter_id"] == meter_id].to_dict(orient="records")
        if user:
            return render_template('view_user.html', user_info=user[0])
        else:
            return render_template('view_user.html',
                                   not_found=True,
                                   meter_id=meter_id)


# ============ 路由：上传电表读数 ============
@app.route('/meterreading', methods=['GET', 'POST'])
def meter_reading():
    global users

    if request.method == 'GET':
        return render_template('meter_reading.html')
    
    elif request.method == 'POST':
        data = request.get_json()
        if not all(k in data for k in ("meter_id", "time", "reading")):
            return jsonify({"status": "error", "message": "Please fill out all blanks."}), 400

        meter_id = data["meter_id"]
        time_str = data["time"]
        reading = data["reading"]

        # 检查 meter_id
        if meter_id not in users["meter_id"].values:
            return jsonify({"status": "error",
                            "message": "You are not registered. Please register first."}), 403

        # 检查时间是否在 00:00-01:00
        # 这个时间系统维护，不接受数据
        time_obj = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        if time_obj.hour == 0 or (time_obj.hour == 1 and time_obj.minute == 0):
            return jsonify({"status": "error",
                            "message": "System maintenance in progress. Please try again after 1am."}), 403

        # 构造新的 DataFrame
        formatted_time = time_obj.strftime('%Y-%m-%d %H:%M:%S')
        new_data = pd.DataFrame([{"meter_id": meter_id,
                                  "time": formatted_time,
                                  "reading": reading}])

        # 线程池异步写入
        executor.submit(store_data_in_df, new_data)

        # 返回成功信息
        return jsonify({"status": "success",
                        "message": f"New reading saved: {meter_id}, {formatted_time}, {reading}"}), 201


# ============ 路由：查询用量 /query_usage ============
@app.route('/query_usage', methods=['GET', 'POST'])
def query_usage():
    if request.method == 'GET':
        return render_template('query_usage.html', plot_url=None, total_usage=None)
    
    meter_id = request.form.get('meter_id', '').strip()
    time_range = request.form.get('time_range', 'today')
    start_date_str = request.form.get('start_date', '')
    end_date_str = request.form.get('end_date', '')

    if not meter_id:
        return render_template('query_usage.html',
                               error="Meter ID is required!",
                               plot_url=None,
                               total_usage=None)
    
    # ============ 当日数据，从 local_db.csv 读取(半小时级) ============
    if time_range == 'today':
        df = pd.read_csv(LOCAL_DB_FILE)
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df.dropna(subset=['time'], inplace=True)
        df = df[df['meter_id'] == meter_id]

        if df.empty:
            return render_template('query_usage.html',
                                   error=f"No data found for meter_id: {meter_id}",
                                   plot_url=None,
                                   total_usage=None)
        
        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59)

        mask = (df['time'] >= start_date) & (df['time'] <= end_date)
        df_range = df.loc[mask].copy()

        if df_range.empty:
            return render_template('query_usage.html',
                                   error="No meter readings found for today.",
                                   plot_url=None,
                                   total_usage=None)

        # 计算 usage
        df_range.sort_values(by='time', inplace=True)
        df_range['reading'] = pd.to_numeric(df_range['reading'], errors='coerce').fillna(0)
        df_range['usage'] = df_range['reading'].diff().fillna(0)

        # 删除第一条
        df_range = df_range.iloc[1:]

        df_range['time_str'] = df_range['time'].dt.strftime('%m-%d %H:%M')
        x_data = df_range['time_str'].tolist()
        y_data = df_range['usage'].tolist()

    else:
        # ============ 上周、上个月或自定义，从 daily_usage.csv 读取(日度级) ============
        df = pd.read_csv(DAILY_USAGE_FILE)
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df.dropna(subset=['time'], inplace=True)
        df = df[df['meter_id'] == meter_id]

        if df.empty:
            return render_template('query_usage.html',
                                   error=f"No daily data found for meter_id: {meter_id}",
                                   plot_url=None,
                                   total_usage=None)

        now = datetime.now()
        if time_range == 'last_week':
            end_date = now.replace(hour=23, minute=59, second=59)
            start_date = end_date - timedelta(days=7)
        elif time_range == 'last_month':
            end_date = now.replace(hour=23, minute=59, second=59)
            start_date = end_date - timedelta(days=30)
        else:
            # 自定义
            try:
                if start_date_str and end_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                else:
                    return render_template('query_usage.html',
                                           error="Please select both start and end date for custom range.",
                                           plot_url=None,
                                           total_usage=None)
            except ValueError:
                return render_template('query_usage.html',
                                       error="Invalid date format. Use YYYY-MM-DD.",
                                       plot_url=None,
                                       total_usage=None)

        mask = (df['time'] >= start_date) & (df['time'] <= end_date)
        df_range = df.loc[mask].copy()

        if df_range.empty:
            return render_template('query_usage.html',
                                   error="No meter readings found in the selected date range.",
                                   plot_url=None,
                                   total_usage=None)

        df_range.sort_values(by='time', inplace=True)
        df_range['reading'] = pd.to_numeric(df_range['reading'], errors='coerce').fillna(0)
        df_range['usage'] = df_range['reading'].diff().fillna(0)

        # 删除第一条
        df_range = df_range.iloc[1:]

        df_range['date'] = df_range['time'].dt.date
        x_data = df_range['date'].astype(str).tolist()
        y_data = df_range['usage'].tolist()

    total_usage = sum(y_data)

    # ============ 绘制柱状图 ============
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(x_data, y_data, color='royalblue')

    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                f'{height:.2f}',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 5),
                textcoords='offset points',
                ha='center',
                fontsize=10,
                color='black'
            )

    ax.set_title(f"Electricity Usage for Meter {meter_id}")
    ax.set_xlabel("Time")
    ax.set_ylabel("Usage (kWh)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
    plot_url = f"data:image/png;base64,{encoded}"
    plt.close(fig)

    return render_template(
        'query_usage.html',
        plot_url=plot_url,
        total_usage=total_usage
    )


# ============ 主程序入口 ============
if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
