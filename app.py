# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template
import logging
from datetime import datetime, timedelta
import sys

app = Flask(__name__)

# 账户存储 (模拟数据库)
accounts = {}
area_consumption = {"Downtown": [], "Suburbs": [], "Industrial": []}  # 每个地区的电力消耗
budget_limits = {}  # 存储用户预算

# 日志设置
logging.basicConfig(filename='server.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 主页
@app.route('/')
def home():
    return render_template('index.html')

# 注册页面
@app.route('/register_form')
def register_form():
    return render_template('register.html')

# 提交电表读数页面
@app.route('/meter_reading_form')
def meter_reading_form():
    return render_template('meter_reading.html')

# 查询用电记录页面
@app.route('/query_usage_form')
def query_usage_form():
    return render_template('query_usage.html')

# 区域平均用电量页面
@app.route('/compare_area_avg_form')
def compare_area_avg_form():
    return render_template('compare_area_avg.html')


# 账户注册
@app.route('/register', methods=['POST'])
def register():
    account_id = request.form.get('account_id')
    name = request.form.get('name')
    area = request.form.get('area')

    if not account_id or not name or not area:
        return jsonify({'message': 'Missing required parameters'}), 400

    if account_id in accounts:
        return jsonify({'message': 'Account already exists'}), 400

    accounts[account_id] = {"name": name, "area": area, "readings": []}
    return jsonify({'message': 'Account registered successfully'}), 201

# 提交电表读数
@app.route('/meter_reading', methods=['POST'])
def meter_reading():
    account_id = request.form.get('account_id')
    reading = float(request.form.get('reading'))

    if not account_id or reading is None:
        return jsonify({'message': 'Missing required parameters'}), 400

    if account_id not in accounts:
        return jsonify({'message': 'Account does not exist'}), 404

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    accounts[account_id]['readings'].append({'time': timestamp, 'reading': reading})

    area = accounts[account_id]['area']
    area_consumption[area].append(reading)

    logging.info(f"Meter Reading - Account: {account_id}, Time: {timestamp}, Reading: {reading}")
    return jsonify({'message': 'Meter reading recorded successfully'}), 201

# 查询用户用电记录
@app.route('/query_usage', methods=['POST'])
def query_usage():
    account_id = request.form.get('account_id')
    period = request.form.get('period')  # options: 'last_30_min', 'today', 'this_week', 'this_month', 'last_month', 'last_month_bill'

    if not account_id or account_id not in accounts:
        return jsonify({'message': 'Account does not exist or is not registered'}), 404

    now = datetime.now()
    readings = accounts[account_id]['readings']

    if period == 'last_30_min':
        start_time = now - timedelta(minutes=30)
    elif period == 'today':
        start_time = now.replace(hour=0, minute=0, second=0)
    elif period == 'this_week':
        start_time = now - timedelta(days=now.weekday())
    elif period == 'this_month':
        start_time = now.replace(day=1)
    elif period == 'last_month':
        first_day_of_current_month = now.replace(day=1)
        start_time = first_day_of_current_month - timedelta(days=1)
        start_time = start_time.replace(day=1)
    elif period == 'last_month_bill':
        # Calculate last month's bill by summing readings of last month
        first_day_of_current_month = now.replace(day=1)
        start_time = first_day_of_current_month - timedelta(days=1)
        start_time = start_time.replace(day=1)
    else:
        return jsonify({'message': 'Invalid period specified'}), 400

    # Filter readings based on start_time
    filtered_readings = [r for r in readings if datetime.strptime(r['time'], '%Y-%m-%d %H:%M:%S') >= start_time]

    # Calculate bill for last month
    if period == 'last_month_bill':
        total_usage = sum(r['reading'] for r in filtered_readings)
        return jsonify({'last_month_bill_kwh': total_usage}), 200

    return jsonify({'usage': filtered_readings}), 200

# 查询区域平均用电量
@app.route('/compare_area_avg', methods=['POST'])
def compare_area_avg():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': 'Account does not exist or is not registered'}), 404

    area = accounts[account_id]['area']
    user_readings = [r['reading'] for r in accounts[account_id]['readings']]
    avg_consumption = sum(area_consumption[area]) / len(area_consumption[area]) if area_consumption[area] else 0

    return jsonify({'user_consumption': sum(user_readings), 'area_avg': avg_consumption}), 200

# 设定用户电量预算
@app.route('/set_budget', methods=['POST'])
def set_budget():
    account_id = request.form.get('account_id')
    budget = float(request.form.get('budget'))

    if not account_id or budget is None:
        return jsonify({'message': 'Missing required parameters'}), 400

    if account_id not in accounts:
        return jsonify({'message': 'Account does not exist'}), 404

    budget_limits[account_id] = budget
    return jsonify({'message': 'Budget set successfully'}), 201

# 预算超额警告
@app.route('/check_budget', methods=['POST'])
def check_budget():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': 'Account does not exist or is not registered'}), 404

    total_usage = sum([r['reading'] for r in accounts[account_id]['readings']])
    budget = budget_limits.get(account_id, None)

    if budget is None:
        return jsonify({'message': 'Budget not set. Please set a budget first'}), 400

    warning = "⚠️ Budget exceeded!" if total_usage > budget else "✅ Within budget"
    return jsonify({'total_usage': total_usage, 'budget': budget, 'status': warning}), 200

if __name__ == '__main__':
    try:
        app.run(debug=True)
    except Exception as e:
        logging.error(f"Server failed to start: {str(e)}")
        print(f"Server failed to start: {str(e)}")
