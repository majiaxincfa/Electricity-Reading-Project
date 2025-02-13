# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 14:20:02 2025

@author: Jiaxin
"""

from flask import Flask, request, jsonify, render_template
import logging
from datetime import datetime
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

# 设定预算页面
@app.route('/set_budget_form')
def set_budget_form():
    return render_template('set_budget.html')

# 检查预算页面
@app.route('/check_budget_form')
def check_budget_form():
    return render_template('check_budget.html')

# 账户注册
@app.route('/register', methods=['POST'])
def register():
    account_id = request.form.get('account_id')
    name = request.form.get('name')
    area = request.form.get('area')

    if not account_id or not name or not area:
        return jsonify({'message': '缺少必要的参数'}), 400

    if account_id in accounts:
        return jsonify({'message': '账户已存在'}), 400

    accounts[account_id] = {"name": name, "area": area, "readings": []}
    return jsonify({'message': '账户注册成功'}), 201

# 提交电表读数
@app.route('/meter_reading', methods=['POST'])
def meter_reading():
    account_id = request.form.get('account_id')
    reading = float(request.form.get('reading'))

    if not account_id or reading is None:
        return jsonify({'message': '缺少必要的参数'}), 400

    if account_id not in accounts:
        return jsonify({'message': '账户不存在'}), 404

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    accounts[account_id]['readings'].append({'time': timestamp, 'reading': reading})

    area = accounts[account_id]['area']
    area_consumption[area].append(reading)

    logging.info(f"Meter Reading - Account: {account_id}, Time: {timestamp}, Reading: {reading}")
    return jsonify({'message': '读数记录成功'}), 201

# 查询用户用电记录
@app.route('/query_usage', methods=['POST'])
def query_usage():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': '账户不存在或尚未注册，请先进行注册。'}), 404
    usage = accounts[account_id]['readings']
    if not usage:
        return jsonify({'message': '暂无用电记录，请稍后再试。'}), 200
    return jsonify({'usage': usage}), 200

# 查询区域平均用电量
@app.route('/compare_area_avg', methods=['POST'])
def compare_area_avg():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': '账户不存在或尚未注册，请先进行注册。'}), 404

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
        return jsonify({'message': '缺少必要的参数'}), 400

    if account_id not in accounts:
        return jsonify({'message': '账户不存在'}), 404

    budget_limits[account_id] = budget
    return jsonify({'message': '预算设定成功'}), 201

# 预算超额警告
@app.route('/check_budget', methods=['POST'])
def check_budget():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': '账户不存在或尚未注册，请先进行注册。'}), 404

    total_usage = sum([r['reading'] for r in accounts[account_id]['readings']])
    budget = budget_limits.get(account_id, None)

    if budget is None:
        return jsonify({'message': '未设定预算，请先设置预算。'}), 400

    warning = "⚠️ 超出预算！" if total_usage > budget else "✅ 在预算内"
    return jsonify({'total_usage': total_usage, 'budget': budget, 'status': warning}), 200

if __name__ == '__main__':
    try:
        app.run(debug=True)
    except Exception as e:
        logging.error(f"服务器启动失败: {str(e)}")
        print(f"服务器启动失败: {str(e)}")
