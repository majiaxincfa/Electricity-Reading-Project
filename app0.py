# -*- coding: utf-8 -*-
import os
import logging
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import matplotlib
matplotlib.use('Agg')  # 在没有图形界面的服务器上使用matplotlib
import matplotlib.pyplot as plt
import base64
from io import BytesIO

app = Flask(__name__)

############################################################
# 1. 日志配置
############################################################
logging.basicConfig(
    filename='server.log',  # 日志文件
    level=logging.INFO,     # 日志级别
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.before_request
def log_request_info():
    """记录每个HTTP请求信息到日志中."""
    log_data = {
        "IP": request.remote_addr,
        "Method": request.method,
        "Path": request.path,
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Args": request.args.to_dict(),
        "Data": request.get_json() if request.is_json else request.form.to_dict()
    }
    logging.info(f"Request: {log_data}")

############################################################
# 2. 全局变量及数据文件初始化
############################################################

# 用户数据保存文件
USERS_CSV_FILE = 'users.csv'

# 读数数据保存文件（存所有电表的半小时读数）
LOCAL_DB_FILE = 'local_db.csv'

# 用户DataFrame
if os.path.exists(USERS_CSV_FILE):
    users = pd.read_csv(USERS_CSV_FILE, dtype=str)
else:
    # 如果还不存在users.csv，先创建一个空的DataFrame
    users = pd.DataFrame(columns=[
        "username", "meter_id", "dwelling_type", "region", "area",
        "community", "unit", "floor", "email", "tel", "reading", "time"
    ], dtype=str)

# 读数DataFrame（用于缓存当日/最新的半小时读数）
# 最终也会合并保存到local_db.csv
if os.path.exists(LOCAL_DB_FILE):
    local_db = pd.read_csv(LOCAL_DB_FILE, dtype=str)
else:
    local_db = pd.DataFrame(columns=["meter_id", "time", "reading"], dtype=str)

# 线程池
executor = ThreadPoolExecutor(max_workers=5)

# 方便维护的一些下拉选项
dwelling_types = [
    "1-room / 2-room",
    "3-room",
    "4-room",
    "5-room and Executive",
    "Landed Properties",
    "Private Apartments and Condominiums"
]
regions = ["Central", "East", "West", "North","South"]

############################################################
# 3. 相关函数
############################################################

def save_users_to_csv():
    """将内存中的 users DataFrame 保存到 CSV."""
    users.to_csv(USERS_CSV_FILE, index=False, encoding='utf-8')

def save_local_db():
    """将内存中的 local_db DataFrame 保存到 CSV."""
    local_db.to_csv(LOCAL_DB_FILE, index=False, encoding='utf-8')

def archive_data():
    """
    示例：归档或清理数据的逻辑。
    本例只是示意，可以根据项目需求来完善归档策略:
    例如：每日将当天的数据存进一个归档文件，
         或者每月计算账单后再做归档等。
    """
    now = datetime.now()
    logging.info(f"Running daily archiving at {now}")
    # ... 这里可以执行实际的归档操作 ...
    # 示例：在这里我们暂不做额外操作，只做日志记录

def store_data_in_local_db(new_rows_df):
    """
    将半小时读数存到 local_db（DataFrame），
    并同步更新 users 里的 reading 字段。
    """
    global local_db, users

    # 追加到 local_db
    local_db = pd.concat([local_db, new_rows_df], ignore_index=True)

    # 同步更新最新 reading 到 users
    for _, row in new_rows_df.iterrows():
        meter_id = row["meter_id"]
        reading_val = row["reading"]
        # 更新 users DataFrame 里的 reading
        # （假设reading是目前电表的累计读数）
        users.loc[users["meter_id"] == meter_id, "reading"] = reading_val

    # 保存到CSV
    save_users_to_csv()
    save_local_db()
    logging.info("New meter reading stored and user info updated.")

def daily_maintenance_job():
    """
    后台定时线程：每天 00:00 ~ 00:59 禁止写操作并执行归档等批处理。
    若需要每月1号处理某些任务，也可加上判断。
    """
    while True:
        current_time = datetime.now()
        # 每天 00:00 进入维护窗口
        if current_time.hour == 0:
            # 执行每日归档
            archive_data()

            # 如果是每月第一天，可额外执行月度任务
            if current_time.day == 1:
                logging.info("Running monthly tasks... (example placeholder)")

            # 避免连续执行，睡眠60秒
            time.sleep(60)
        # 每 10 分钟检测一次
        time.sleep(600)

# 启动后台维护线程（daemon=True 表示主线程退出后它也退出）
maintenance_thread = threading.Thread(target=daily_maintenance_job, daemon=True)
maintenance_thread.start()

def calculate_usage(meter_id, start_dt, end_dt):
    """
    计算某个meter在指定时间范围内的用电量。
    假设 reading 为累计读数，区间用电量 = (最后一次读数 - 最早一次读数)。
    """
    # 先过滤出指定仪表的数据
    meter_df = local_db[local_db["meter_id"] == str(meter_id)].copy()
    if meter_df.empty:
        return 0.0

    # 转换time为datetime对象
    meter_df["dt"] = meter_df["time"].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S'))

    # 再过滤出时间范围
    mask = (meter_df["dt"] >= start_dt) & (meter_df["dt"] <= end_dt)
    meter_df = meter_df[mask].sort_values(by="dt")
    if meter_df.empty:
        return 0.0

    # usage = difference between last reading and first reading
    first_reading = float(meter_df.iloc[0]["reading"])
    last_reading = float(meter_df.iloc[-1]["reading"])
    usage_kwh = last_reading - first_reading
    return max(usage_kwh, 0.0)

def generate_usage_plot(x_labels, usage_values):
    """
    生成用电量的简单柱状图，并返回base64编码后的图片数据。
    x_labels: X轴标签
    usage_values: 用电量
    """
    plt.figure(figsize=(6,4))
    plt.bar(x_labels, usage_values, color='skyblue')
    plt.xlabel("Period")
    plt.ylabel("Usage (kWh)")
    plt.title("Electricity Usage")
    plt.tight_layout()

    # 将图表保存为字节流，再转换为base64
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    base64_img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()  # 关闭图表
    return base64_img

############################################################
# 4. Flask 路由
############################################################

@app.route('/')
def index():
    """
    首页
    """
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    用户注册，手动输入Meter ID，而非自动生成。
    """
    global users
    if request.method == 'GET':
        return render_template('register.html',
                               dwelling_types=dwelling_types,
                               regions=regions)

    if request.method == 'POST':
        # 获取表单数据
        meter_id = request.form['meter_id'].strip()
        username = request.form['username'].strip()
        dwelling_type = request.form['dwelling_type']
        region = request.form['region']
        area = request.form['area'].strip()
        community = request.form['community'].strip()
        unit = request.form['unit'].strip()
        floor = request.form['floor'].strip()
        email = request.form['email'].strip()
        tel = request.form['tel'].strip()

        # 校验是否已经存在相同的meter_id
        if meter_id in users['meter_id'].values:
            return "该 Meter ID 已被注册，请使用其他ID。", 400

        # 获取当前时间（初始化reading为0）
        timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        # 新用户行
        new_user = pd.DataFrame([{
            "username": username,
            "meter_id": meter_id,
            "dwelling_type": dwelling_type,
            "region": region,
            "area": area,
            "community": community,
            "unit": unit,
            "floor": floor,
            "email": email,
            "tel": tel,
            "reading": "0",
            "time": timestamp
        }], dtype=str)

        # 合并到users
        users = pd.concat([users, new_user], ignore_index=True)
        save_users_to_csv()

        # 同时在 local_db 里存一条初始读数记录(0)
        init_row = pd.DataFrame([{
            "meter_id": meter_id,
            "time": timestamp,
            "reading": "0"
        }], dtype=str)
        global local_db
        local_db = pd.concat([local_db, init_row], ignore_index=True)
        save_local_db()

        return f"用户 {username} 注册成功！您的电表ID为：{meter_id}。"

@app.route('/meter_reading', methods=['GET', 'POST'])
def meter_reading():
    """
    提交新的电表读数 (默认 01:00 ~ 23:59 之间)。
    00:00 ~ 00:59 系统维护，禁止提交。
    """
    global local_db
    if request.method == 'GET':
        return render_template('meter_reading.html')
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "无效的请求"}), 400

        required_keys = ("meter_id", "time", "reading")
        if not all(k in data for k in required_keys):
            return jsonify({"status": "error", "message": "请填写所有必需字段：meter_id, time, reading"}), 400

        meter_id = data["meter_id"].strip()
        time_str = data["time"]
        reading_val = data["reading"]

        # 判断meter_id是否在users里存在
        if meter_id not in users["meter_id"].values:
            return jsonify({"status": "error", "message": "该Meter ID尚未注册，请先注册。"}), 403

        # 判断是否在维护时段
        time_obj = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
        if time_obj.hour == 0:
            return jsonify({"status": "error", "message": "系统维护时段(00:00-00:59)，禁止提交读数。"}), 403

        # 格式化time
        formatted_time = time_obj.strftime('%Y-%m-%d %H:%M:%S')

        # 将新记录添加到DataFrame
        new_data = pd.DataFrame([{
            "meter_id": meter_id,
            "time": formatted_time,
            "reading": str(reading_val)
        }], dtype=str)

        # 启动线程将数据存入local_db并更新users信息
        executor.submit(store_data_in_local_db, new_data)

        return jsonify({"status": "success",
                        "message": f"New reading saved: {meter_id}, {formatted_time}, {reading_val}"}), 201

@app.route('/query_usage', methods=['GET', 'POST'])
def query_usage():
    """
    查询指定用户在当日/当周/当月/上月 或者自定义时间范围内的总用电量。
    并返回简单图表可视化。
    """
    global local_db, users
    if request.method == 'GET':
        # 显示查询页面
        return render_template('query_usage.html')
    else:
        # 处理查询逻辑
        meter_id = request.form.get('meter_id', '').strip()
        query_type = request.form.get('query_type', '')
        custom_start = request.form.get('start_time', '')
        custom_end = request.form.get('end_time', '')

        if meter_id not in users["meter_id"].values:
            msg = f"Meter ID {meter_id} 尚未注册!"
            return render_template('query_usage.html', result=msg)

        now = datetime.now()
        usage_result = 0.0
        usage_details = ""  # 用于显示在页面上的结果文字
        usage_period_labels = []
        usage_values = []

        if query_type == 'today':
            # 当日 0点 到 现在
            start_dt = datetime(now.year, now.month, now.day, 0, 0, 0)
            end_dt = now
            usage_result = calculate_usage(meter_id, start_dt, end_dt)
            usage_details = f"当日({start_dt.strftime('%Y-%m-%d')})用电量: {usage_result:.2f} kWh"
            usage_period_labels.append("Today")
            usage_values.append(usage_result)

        elif query_type == 'this_week':
            # 本周周一 0点 到 现在
            weekday = now.weekday()  # 周一=0
            monday = now - timedelta(days=weekday)
            start_dt = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
            end_dt = now
            usage_result = calculate_usage(meter_id, start_dt, end_dt)
            usage_details = f"本周(从 {start_dt.strftime('%Y-%m-%d')} 至今)用电量: {usage_result:.2f} kWh"
            usage_period_labels.append("This Week")
            usage_values.append(usage_result)

        elif query_type == 'this_month':
            # 本月1日 0点 到 现在
            start_dt = datetime(now.year, now.month, 1, 0, 0, 0)
            end_dt = now
            usage_result = calculate_usage(meter_id, start_dt, end_dt)
            usage_details = f"本月(从 {start_dt.strftime('%Y-%m-%d')} 至今)用电量: {usage_result:.2f} kWh"
            usage_period_labels.append("This Month")
            usage_values.append(usage_result)

        elif query_type == 'last_month':
            # 上个月1号 到 上个月最后一天
            first_day_last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
            year_lm = first_day_last_month.year
            month_lm = first_day_last_month.month
            start_dt = datetime(year_lm, month_lm, 1, 0, 0, 0)
            # 下个月1号 - 1天
            next_month_first = (start_dt.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_dt = next_month_first - timedelta(seconds=1)
            usage_result = calculate_usage(meter_id, start_dt, end_dt)
            usage_details = f"上个月({start_dt.strftime('%Y-%m-%d')} - {end_dt.strftime('%Y-%m-%d')})用电量: {usage_result:.2f} kWh"
            usage_period_labels.append("Last Month")
            usage_values.append(usage_result)

        elif query_type == 'custom' and custom_start and custom_end:
            # 用户自定义开始、结束时间
            try:
                start_dt = datetime.strptime(custom_start, '%Y-%m-%dT%H:%M')
                end_dt = datetime.strptime(custom_end, '%Y-%m-%dT%H:%M')
                if end_dt < start_dt:
                    return render_template('query_usage.html', result="结束时间不能早于开始时间！")
                usage_result = calculate_usage(meter_id, start_dt, end_dt)
                usage_details = (f"自定义时间范围({start_dt.strftime('%Y-%m-%d %H:%M')} - "
                                 f"{end_dt.strftime('%Y-%m-%d %H:%M')})用电量: {usage_result:.2f} kWh")
                usage_period_labels.append("Custom Range")
                usage_values.append(usage_result)
            except ValueError:
                return render_template('query_usage.html', result="时间格式不正确，请重试！")
        else:
            usage_details = "请选择或输入正确的查询方式/时间段。"

        # 若查询成功，生成图表
        chart_data = None
        if usage_values:
            chart_data = generate_usage_plot(usage_period_labels, usage_values)

        return render_template('query_usage.html',
                               result=usage_details,
                               chart_data=chart_data)

@app.route('/view_user', methods=['GET', 'POST'])
def view_user():
    """
    查询用户信息的示例路由（功能与之前 get_user 类似）。
    """
    if request.method == 'GET':
        return """
        <h2>View User</h2>
        <form action="/view_user" method="POST">
            <label>Meter ID:</label>
            <input type="text" name="meter_id" placeholder="e.g. 123-456-789" required>
            <button type="submit">Search</button>
        </form>
        <p><a href="/">Return Home</a></p>
        """
    else:
        meter_id = request.form.get('meter_id', '').strip()
        user_rec = users[users["meter_id"] == meter_id]
        if user_rec.empty:
            return f"未找到 Meter ID 为 {meter_id} 的用户", 404
        else:
            user_dict = user_rec.iloc[0].to_dict()
            return f"""
            <h3>用户信息:</h3>
            <p><strong>Username:</strong> {user_dict["username"]}</p>
            <p><strong>Meter ID:</strong> {user_dict["meter_id"]}</p>
            <p><strong>Dwelling Type:</strong> {user_dict["dwelling_type"]}</p>
            <p><strong>Region:</strong> {user_dict["region"]}</p>
            <p><strong>Area:</strong> {user_dict["area"]}</p>
            <p><strong>Community:</strong> {user_dict["community"]}</p>
            <p><strong>Unit:</strong> {user_dict["unit"]}</p>
            <p><strong>Floor:</strong> {user_dict["floor"]}</p>
            <p><strong>Email:</strong> {user_dict["email"]}</p>
            <p><strong>Phone:</strong> {user_dict["tel"]}</p>
            <p><strong>Reading:</strong> {user_dict["reading"]}</p>
            <p><a href="/">Return Home</a></p>
            """

############################################################
# 5. 主函数
############################################################

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
