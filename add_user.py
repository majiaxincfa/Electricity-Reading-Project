from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import pandas as pd
from datetime import datetime
import random

app = Flask(__name__)

# Sample data to simulate database
users = [
    {
        "username": "John Doe",
        "meter_no": "123-456-789",
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

# Function to save meter_no, time, and reading to a local CSV file as DataFrame
def generate_unique_meter_no():
    while True:
        # Generate a random 9-digit number
        new_meter_no = str(random.randint(100000000, 999999999))  # Random 9-digit number
        if not any(user['meter_no'] == new_meter_no for user in users):
            return new_meter_no

def save_meter_no_to_csv(meter_no, reading):
    try:
        timestamp = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        # Check if the CSV file exists
        try:
            meter_df = pd.read_csv('meter_no.csv', dtype=str)  # Ensure all data is read as strings
        except FileNotFoundError:
            # If file doesn't exist, create a new one with headers
            meter_df = pd.DataFrame(columns=["meter_no", "time", "reading"], dtype=str)

        # Append the new meter_no, timestamp, and reading to the DataFrame
        new_row = pd.DataFrame({"meter_no": [meter_no], "time": [timestamp], "reading": [str(reading)]}, dtype=str)
        meter_df = pd.concat([meter_df, new_row], ignore_index=True)

        # Save DataFrame to CSV file as text (all columns are treated as strings)
        meter_df.to_csv('meter_no.csv', index=False, header=True, encoding='utf-8')
    except Exception as e:
        print(f"Error saving meter_no: {e}")


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


@app.route('/meterreading')
def meter_reading():
    return render_template_string("""
    <h2>Meter Readings System</h2>
    <p>Welcome to the Meter Readings System.</p>
    """)


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'GET':
        meter_no = generate_unique_meter_no()  # 生成唯一的 meter_no
        return render_template_string("""
        <h2>Add New User</h2>
        <form action="/add_user" method="post">
            <label for="username">Username:</label>
            <input type="text" name="username" required><br><br>

            <label for="meter_no">Meter Number:</label>
            <input type="text" name="meter_no" value="{{ meter_no }}" readonly><br><br>

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
        """, dwelling_types=dwelling_types, regions=regions, meter_no=meter_no)

    if request.method == 'POST':
        meter_no = request.form['meter_no']
        timestamp = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        user_data = {
            "username": request.form['username'],
            "meter_no": meter_no,
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
        save_meter_no_to_csv(meter_no, 0)  # Save the initial reading (0)

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
            <label for="meter_no">Meter Number (e.g. 123-456-789):</label>
            <input type="text" name="meter_no" required><br><br>
            <button type="submit">Search</button>
        </form>
        """)

    if request.method == 'POST':
        meter_no = request.form['meter_no']
        user = next((u for u in users if u['meter_no'] == meter_no), None)
        if user:
            return render_template_string("""
            <h3>User Details:</h3>
            <p><strong>Username:</strong> {{ user['username'] }}</p>
            <p><strong>Meter Number:</strong> {{ user['meter_no'] }}</p>
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
    app.run(host='localhost', port=5000, debug=False)
