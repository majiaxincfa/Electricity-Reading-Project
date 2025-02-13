# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template
import logging
from datetime import datetime
import sys

app = Flask(__name__)

# Account storage (simulating a database)
accounts = {}
area_consumption = {"Downtown": [], "Suburbs": [], "Industrial": []}  # Power consumption in each area
budget_limits = {}  # Store user budgets

# Logging settings
logging.basicConfig(filename='server.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Registration page
@app.route('/register_form')
def register_form():
    return render_template('register.html')

# Submit meter reading page
@app.route('/meter_reading_form')
def meter_reading_form():
    return render_template('meter_reading.html')
# @app.route('/meterreading', methods=['GET','POST'])
# def meter_reading_form():
#     if request.method == 'GET':
#         return """
#         <!DOCTYPE html>
#         <html lang="en">
#         <head>
#             <meta charset="UTF-8">
#             <meta name="viewport" content="width=device-width, initial-scale=1.0">
#             <title>Meter Reading System</title>
#         </head>
#         <body>
#             <h2>Meter Reading System</h2>
#             <form id="meterForm">
#                 <label>MeterID：</label>
#                 <input type="text" id="meter_id" required>
#                 <br>
#                 <label>UserID：</label>
#                 <input type="text" id="user_id" required>
#                 <br>
#                 <label>Time：</label>
#                 <input type="datetime-local" id="time" required>
#                 <br>
#                 <label>Meter reading (kWh)：</label>
#                 <input type="number" id="reading" step="0.01" required>
#                 <br><br>
#                 <button type="submit">Submit</button>
#             </form>

#             <script>
#             document.getElementById("meterForm").addEventListener("submit", function(event) {
#                 event.preventDefault();
#                 fetch("/meterreading", {
#                     method: "POST",
#                     headers: { "Content-Type": "application/json" },
#                     body: JSON.stringify({
#                         meter_id: document.getElementById("meter_id").value,
#                         user_id: document.getElementById("user_id").value,
#                         time: document.getElementById("time").value,
#                         reading: parseFloat(document.getElementById("reading").value)
#                     })
#                 })
#                 .then(response => response.json())
#                 .then(data => alert(data.message))
#                 .catch(error => console.error("Failure:", error));
#             });
#             </script>
#         </body>
#         </html>
    
#         """
#     elif request.method == 'POST':

#         data = request.get_json()
#         if not all(k in data for k in ("meter_id", "user_id", "time", "reading")):
#             return jsonify({"status": "error", "message": "Please fill out all blanks."}), 400

#         meter_id = data["meter_id"]
#         user_id = data["user_id"]
#         time = data["time"]
#         reading = data["reading"]

#         # 这里可以存入数据库，目前只返回数据
#         return jsonify({"status": "success", "message": f"We have received: {meter_id}, {user_id}, from{starttime} to {endtime}, {reading}"}), 201

# Query electricity usage records page
@app.route('/query_usage_form')
def query_usage_form():
    return render_template('query_usage.html')

# Query average electricity consumption in the area page
@app.route('/compare_area_avg_form')
def compare_area_avg_form():
    return render_template('compare_area_avg.html')

# Set budget page
@app.route('/set_budget_form')
def set_budget_form():
    return render_template('set_budget.html')

# Check budget page
@app.route('/check_budget_form')
def check_budget_form():
    return render_template('check_budget.html')

# Account registration
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

# Submit meter reading
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
    return jsonify({'message': 'Reading recorded successfully'}), 201

# Query user electricity usage records
@app.route('/query_usage', methods=['POST'])
def query_usage():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': 'Account does not exist or is not registered. Please register first.'}), 404
    usage = accounts[account_id]['readings']
    if not usage:
        return jsonify({'message': 'No electricity usage records yet. Please try again later.'}), 200
    return jsonify({'usage': usage}), 200

# Query average electricity consumption in the area
@app.route('/compare_area_avg', methods=['POST'])
def compare_area_avg():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': 'Account does not exist or is not registered. Please register first.'}), 404

    area = accounts[account_id]['area']
    user_readings = [r['reading'] for r in accounts[account_id]['readings']]
    avg_consumption = sum(area_consumption[area]) / len(area_consumption[area]) if area_consumption[area] else 0

    return jsonify({'user_consumption': sum(user_readings), 'area_avg': avg_consumption}), 200

# Set user electricity budget
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

# Budget over - limit warning
@app.route('/check_budget', methods=['POST'])
def check_budget():
    account_id = request.form.get('account_id')
    if not account_id or account_id not in accounts:
        return jsonify({'message': 'Account does not exist or is not registered. Please register first.'}), 404

    total_usage = sum([r['reading'] for r in accounts[account_id]['readings']])
    budget = budget_limits.get(account_id, None)

    if budget is None:
        return jsonify({'message': 'No budget has been set. Please set a budget first.'}), 400

    warning = "⚠️ Over budget!" if total_usage > budget else "✅ Within budget"
    return jsonify({'total_usage': total_usage, 'budget': budget, 'status': warning}), 200

if __name__ == '__main__':
    try:
        app.run(debug=True)
    except Exception as e:
        logging.error(f"Server failed to start: {str(e)}")
        print(f"Server failed to start: {str(e)}")
