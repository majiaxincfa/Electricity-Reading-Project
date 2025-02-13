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
    <h2>Admin Dashboard</h2>
    <p>Welcome, Admin!</p>
    <ul>
        <li><a href="/add_user">Add User</a></li>
        <li><a href="/get_user">View User</a></li>
        <li><a href="/modify_user">Modify User</a></li>
        <li><a href="/delete_user">Delete User</a></li>
        <li><a href="/meterreading">Meter Readings System</a></li>
    </ul>
    """)

@app.route('/meterreading')
def meter_reading():
    return render_template_string("""
    <h2>Meter Readings System</h2>
    <p>Welcome to the Meter Readings System.</p>
    <!-- You can add more content or functionality here -->
    """)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>Add New User</h2>
        <form action="/add_user" method="post">
            <label for="username">Username (e.g. John Doe):</label>
            <input type="text" name="username" required><br><br>

            <label for="meter_no">Meter Number (e.g. 123-456-789):</label>
            <input type="text" name="meter_no" required><br><br>

            <label for="dwelling_type">Dwelling Type (e.g. Apartment):</label>
            <select name="dwelling_type" required>
                {% for dwelling in dwelling_types %}
                    <option value="{{ dwelling }}">{{ dwelling }}</option>
                {% endfor %}
            </select><br><br>

            <label for="region">Region (e.g. Central):</label>
            <select name="region" required>
                {% for region in regions %}
                    <option value="{{ region }}">{{ region }}</option>
                {% endfor %}
            </select><br><br>

            <label for="area">Area (e.g. Downtown):</label>
            <input type="text" name="area" required><br><br>

            <label for="community">Community (e.g. Greenfield):</label>
            <input type="text" name="community" required><br><br>

            <label for="unit">Unit (e.g. A1):</label>
            <input type="text" name="unit" required><br><br>

            <label for="floor">Floor (e.g. 5):</label>
            <input type="text" name="floor" required><br><br>

            <label for="email">Email (e.g. john@example.com):</label>
            <input type="email" name="email" required><br><br>

            <label for="tel">Phone (e.g. 123-456-7890):</label>
            <input type="tel" name="tel" required><br><br>

            <button type="submit">Submit</button>
        </form>
        """, dwelling_types=dwelling_types, regions=regions)

    if request.method == 'POST':
        # Check if the meter_no already exists
        meter_no = request.form['meter_no']
        if any(user['meter_no'] == meter_no for user in users):
            return render_template_string("""
            <h2>Error: Meter Number already exists!</h2>
            <p>The meter number you entered is already registered. Please use a different meter number.</p>
            <a href="/add_user">Go back to the registration form</a>
            """)

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
            """, user=user)
        else:
            return "User not found."

@app.route('/modify_user', methods=['GET', 'POST'])
def modify_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>Modify User</h2>
        <form action="/modify_user" method="post">
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
            <h2>Modify User</h2>
            <form action="/modify_user/{{ meter_no }}" method="post">
                <label for="username">Username:</label>
                <input type="text" name="username" value="{{ user['username'] }}" required><br><br>

                <label for="email">Email:</label>
                <input type="email" name="email" value="{{ user['email'] }}" required><br><br>

                <label for="tel">Phone:</label>
                <input type="tel" name="tel" value="{{ user['tel'] }}" required><br><br>

                <button type="submit">Submit Changes</button>
            </form>
            """, user=user, meter_no=meter_no)

        else:
            return "User not found."

@app.route('/modify_user/<meter_no>', methods=['POST'])
def modify_user_post(meter_no):
    user = next((u for u in users if u['meter_no'] == meter_no), None)
    if user:
        # 获取用户提交的修改数据
        new_username = request.form['username']
        new_email = request.form['email']
        new_tel = request.form['tel']

        # 检查是否有变化
        changes_made = False
        if new_username != user["username"]:
            user["username"] = new_username
            changes_made = True
        if new_email != user["email"]:
            user["email"] = new_email
            changes_made = True
        if new_tel != user["tel"]:
            user["tel"] = new_tel
            changes_made = True
        
        if changes_made:
            return render_template_string("""
            <h2>User Information Modified Successfully</h2>
            <p><a href="/dashboard">Go back to Dashboard</a></p>
            """)
        else:
            return render_template_string("""
            <h2>No Changes Made</h2>
            <p>There were no changes to your information. Please modify at least one field.</p>
            <p><a href="/modify_user/{{ meter_no }}">Go back and make changes</a></p>
            """, meter_no=meter_no)
    else:
        return "User not found."

@app.route('/delete_user', methods=['GET', 'POST'])
def delete_user():
    if request.method == 'GET':
        return render_template_string("""
        <h2>Delete User</h2>
        <form action="/delete_user" method="post">
            <label for="meter_no">Meter Number (e.g. 123-456-789):</label>
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
