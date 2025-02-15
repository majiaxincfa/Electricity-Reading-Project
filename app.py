from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import pandas as pd
from datetime import datetime
import random
from concurrent.futures import ThreadPoolExecutor
import time
import threading
from datetime import datetime
from data_maintainance import archive_data

app = Flask(__name__)

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

regions = ["Central", "East", "West", "North"]

# Function to save meter_id, time, and reading to a local CSV file as DataFrame
def generate_unique_meter_id():
    while True:
        # Generate a random 9-digit number
        new_meter_id = str(random.randint(100000000, 999999999))  # Random 9-digit number
        if not any(user['meter_id'] == new_meter_id for user in users):
            return new_meter_id


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
    """后台线程用来处理数据存储。将新输入的meterreading保存到临时dataframe中。"""
    
    print(data)
    time.sleep(1)

    global data_store
    
    # 追加数据到 临时DataFrame
    data_store = pd.concat([data_store, data], ignore_index=True)
    print(f"Data stored successfully!")

    #假设数据会被存储到文件或数据库,测试用
    #data_store.to_csv('local_db.csv', index=False) 

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
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Meter Management System</title>
    </head>
    <body>
        <h1>Welcome to Meter Management System</h1>
        <p><a href="/dashboard">Go to Dashboard</a></p>
    </body>
    </html>
    """)


@app.route('/dashboard')
def dashboard():
    return render_template_string("""
    <h2>Admin Dashboard</h2>
    <p>Welcome, Admin!</p>
    <ul>
        <li><a href="/add_user">Add User</a></li>
        <li><a href="/get_user">View User</a></li>
        <li><a href="/meterreading">Meter Readings System</a></li>
    </ul>
    """)


@app.route('/meterreading', methods=['GET','POST'])
def meter_reading():
    
    global data_store

    if request.method == 'GET':
        return """
        <h2>Meter Reading System</h2>
        <form id="meterForm">
            <label>MeterID：</label>
            <input type="text" id="meter_id" required>
            <br>            
            <label>Time：</label>
            <input type="datetime-local" id="time" required>
            <br>
            <label>Meter reading (kWh)：</label>
            <input type="number" id="reading" step="0.01" required>
            <br><br>
            <button type="submit">Submit</button>
        </form>
        <p><a href="/dashboard">Return to Dashboard</a></p> 

        <script>
        document.getElementById("meterForm").addEventListener("submit", function(event) {
            event.preventDefault();
            fetch("/meterreading", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    meter_id: document.getElementById("meter_id").value,
        
                    time: document.getElementById("time").value,
                    reading: parseFloat(document.getElementById("reading").value)
                })
            })
            .then(response => response.json())
            .then(data => alert(data.message))
            .catch(error => console.error("Failure:", error));
        });
        </script>
        """
    
    elif request.method == 'POST':

        data = request.get_json()
        if not all(k in data for k in ("meter_id", "time", "reading")):
            return jsonify({"status": "error", "message": "Please fill out all blanks."}), 400

        meter_id = data["meter_id"]
        time = data["time"]
        reading = data["reading"]

        #check meterID是否存在于库中,临时库和本地库
        if meter_id not in data_store["meter_id"].values and meter_id not in local_db["meter_id"].values:
            return jsonify({"status": "error", "message": "You are not registered. Please register first."}), 403

        
        #check 时间是否在12点到1点
        time_obj = datetime.strptime(time, "%Y-%m-%dT%H:%M") 
        formatted_time = time_obj.strftime('%Y-%m-%d %H:%M:%S')

        if time_obj.hour == 0 and time_obj.minute > 0:
            return jsonify({"status": "error", "message": "System maintenance in progress. Please try again after 1am."}), 403
        elif time_obj.hour == 1 and time_obj.minute == 0:
            return jsonify({"status": "error", "message": "System maintenance in progress. Please try again after 1am."}), 403

        
        # 追加数据到 DataFrame,非线程版本
        new_data = pd.DataFrame([{"meter_id": meter_id, "time": formatted_time, "reading": reading}])
        #print(new_data)
        # data_store = pd.concat([data_store, new_data], ignore_index=True)
        
        # 启动线程来存储数据
        executor.submit(store_data_in_df, new_data)

        # 返回数据提示用户已经成功输入
        return jsonify({"status": "success", "message": f"We have received: {meter_id}, {formatted_time}, {reading}"}), 201


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'GET':
        meter_id = generate_unique_meter_id()  # 生成唯一的 meter_id
        return render_template_string("""
        <h2>Add New User</h2>
        <form action="/add_user" method="post">
            <label for="username">Username:</label>
            <input type="text" name="username" required><br><br>

            <label for="meter_id">Meter ID:</label>
            <input type="text" name="meter_id" value="{{ meter_id }}" readonly><br><br>

            <label for="dwelling_type">Dwelling Type:</label>
            <select name="dwelling_type" required>
                {% for dwelling in dwelling_types %}
                    <option value="{{ dwelling }}">{{ dwelling }}</option>
                {% endfor %}
            </select><br><br>

            <label for="region">Region:</label>
            <select name="region" required>
                {% for region in regions %}
                    <option value="{{ region }}">{{ region }}</option>
                {% endfor %}
            </select><br><br>

            <label for="area">Area:</label>
            <input type="text" name="area" required><br><br>

            <label for="community">Community:</label>
            <input type="text" name="community" required><br><br>

            <label for="unit">Unit:</label>
            <input type="text" name="unit" required><br><br>

            <label for="floor">Floor:</label>
            <input type="text" name="floor" required><br><br>

            <label for="email">Email:</label>
            <input type="email" name="email" required><br><br>

            <label for="tel">Phone:</label>
            <input type="tel" name="tel" required><br><br>

            <button type="submit">Submit</button>
        </form>
        <p><a href="/dashboard">Return to Dashboard</a></p> 
        """, dwelling_types=dwelling_types, regions=regions, meter_id=meter_id)

    if request.method == 'POST':
        meter_id = request.form['meter_id']
        timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        user_data = {
            "username": request.form['username'],
            "meter_id": meter_id,
            "dwelling_type": request.form['dwelling_type'],
            "region": request.form['region'],
            "area": request.form['area'],
            "community": request.form['community'],
            "unit": request.form['unit'],
            "floor": request.form['floor'],
            "email": request.form['email'],
            "tel": request.form['tel'],
            "reading": 0,  # Set initial reading to 0
            "time": timestamp
        }
        users.append(user_data)
        save_meter_id_to_csv(meter_id, 0)  # Save the initial reading (0)

        return jsonify({
            'status': 'success',
            'message': 'User added successfully!',
            'user_data': user_data
        })


@app.route('/get_user', methods=['GET', 'POST'])
def get_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>View User</h2>
        <form action="/get_user" method="post">
            <label for="meter_id">Meter ID (e.g. 123-456-789):</label>
            <input type="text" name="meter_id" required><br><br>
            <button type="submit">Search</button>
        </form>
        <p><a href="/dashboard">Return to Dashboard</a></p> 
        """)

    if request.method == 'POST':
        meter_id = request.form['meter_id']
        user = next((u for u in users if u['meter_id'] == meter_id), None)
        if user:
            return render_template_string("""
            <h3>User Details:</h3>
            <p><strong>Username:</strong> {{ user['username'] }}</p>
            <p><strong>Meter ID:</strong> {{ user['meter_id'] }}</p>
            <p><strong>Dwelling Type:</strong> {{ user['dwelling_type'] }}</p>
            <p><strong>Region:</strong> {{ user['region'] }}</p>
            <p><strong>Area:</strong> {{ user['area'] }}</p>
            <p><strong>Community:</strong> {{ user['community'] }}</p>
            <p><strong>Unit:</strong> {{ user['unit'] }}</p>
            <p><strong>Floor:</strong> {{ user['floor'] }}</p>
            <p><strong>Email:</strong> {{ user['email'] }}</p>
            <p><strong>Phone:</strong> {{ user['tel'] }}</p>
            <p><strong>Reading:</strong> {{ user['reading'] }}</p>
            """, user=user)
        else:
            return jsonify({
                'status': 'error',
                'message': 'User not found.'
            })


if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
