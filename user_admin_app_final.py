# -*- coding: utf-8 -*-
"""
Created on Tue Feb 11 19:20:45 2025

@author: 73671
"""

from flask import Flask, render_template_string, request, redirect, url_for

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
        "tel": "123-456-7890"
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

# Admin login credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

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
        <form action="/login" method="post">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required><br><br>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required><br><br>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    """)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return redirect(url_for('dashboard'))
    else:
        return "Invalid credentials. Please try again."

@app.route('/dashboard')
def dashboard():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Dashboard</title>
    </head>
    <body>
        <h1>Admin Dashboard</h1>
        <ul>
            <li><a href="/add_user">Add User</a></li>
            <li><a href="/get_user">View User</a></li>
            <li><a href="/modify_user">Modify User</a></li>
            <li><a href="/delete_user">Delete User</a></li>
        </ul>
    </body>
    </html>
    """)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>Add New User</h2>
        <form action="/add_user" method="post">
            <label for="username">Username:</label>
            <input type="text" name="username" required><br><br>

            <label for="meter_no">Meter Number:</label>
            <input type="text" name="meter_no" required><br><br>

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
        """, dwelling_types=dwelling_types, regions=regions)

    if request.method == 'POST':
        user_data = {
            "username": request.form['username'],
            "meter_no": request.form['meter_no'],
            "dwelling_type": request.form['dwelling_type'],
            "region": request.form['region'],
            "area": request.form['area'],
            "community": request.form['community'],
            "unit": request.form['unit'],
            "floor": request.form['floor'],
            "email": request.form['email'],
            "tel": request.form['tel']
        }
        users.append(user_data)
        return redirect(url_for('dashboard'))

@app.route('/get_user', methods=['GET', 'POST'])
def get_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>View User</h2>
        <form action="/get_user" method="post">
            <label for="meter_no">Meter Number:</label>
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
            """, user=user)
        else:
            return "User not found."

@app.route('/modify_user', methods=['GET', 'POST'])
def modify_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>Modify User</h2>
        <form action="/modify_user" method="post">
            <label for="meter_no">Meter Number:</label>
            <input type="text" name="meter_no" required><br><br>
            <button type="submit">Search</button>
        </form>
        """)

    if request.method == 'POST':
        meter_no = request.form['meter_no']
        user = next((u for u in users if u['meter_no'] == meter_no), None)
        if user:
            return render_template_string("""
            <h2>Modify User</h2>
            <form action="/modify_user/{{ meter_no }}" method="post">
                <label for="username">Username:</label>
                <input type="text" name="username" value="{{ user['username'] }}" required><br><br>

                <label for="dwelling_type">Dwelling Type:</label>
                <select name="dwelling_type" required>
                    {% for dwelling in dwelling_types %}
                        <option value="{{ dwelling }}" {% if dwelling == user['dwelling_type'] %}selected{% endif %}>{{ dwelling }}</option>
                    {% endfor %}
                </select><br><br>

                <label for="region">Region:</label>
                <select name="region" required>
                    {% for region in regions %}
                        <option value="{{ region }}" {% if region == user['region'] %}selected{% endif %}>{{ region }}</option>
                    {% endfor %}
                </select><br><br>

                <label for="area">Area:</label>
                <input type="text" name="area" value="{{ user['area'] }}" required><br><br>

                <label for="community">Community:</label>
                <input type="text" name="community" value="{{ user['community'] }}" required><br><br>

                <label for="unit">Unit:</label>
                <input type="text" name="unit" value="{{ user['unit'] }}" required><br><br>

                <label for="floor">Floor:</label>
                <input type="text" name="floor" value="{{ user['floor'] }}" required><br><br>

                <label for="email">Email:</label>
                <input type="email" name="email" value="{{ user['email'] }}" required><br><br>

                <label for="tel">Phone:</label>
                <input type="tel" name="tel" value="{{ user['tel'] }}" required><br><br>

                <button type="submit">Modify</button>
            </form>
            """, user=user, meter_no=meter_no, dwelling_types=dwelling_types, regions=regions)
        else:
            return "User not found."

@app.route('/modify_user/<meter_no>', methods=['POST'])
def submit_modified_user(meter_no):
    modified_data = {
        'username': request.form['username'],
        'dwelling_type': request.form['dwelling_type'],
        'region': request.form['region'],
        'area': request.form['area'],
        'community': request.form['community'],
        'unit': request.form['unit'],
        'floor': request.form['floor'],
        'email': request.form['email'],
        'tel': request.form['tel']
    }
    user = next((u for u in users if u['meter_no'] == meter_no), None)
    if user:
        user.update(modified_data)
        return redirect(url_for('dashboard'))
    else:
        return "User not found."

@app.route('/delete_user', methods=['GET', 'POST'])
def delete_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>Delete User</h2>
        <form action="/delete_user" method="post">
            <label for="meter_no">Meter Number:</label>
            <input type="text" name="meter_no" required><br><br>
            <button type="submit">Delete</button>
        </form>
        """)

    if request.method == 'POST':
        meter_no = request.form['meter_no']
        global users
        users = [u for u in users if u['meter_no'] != meter_no]
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=False)
