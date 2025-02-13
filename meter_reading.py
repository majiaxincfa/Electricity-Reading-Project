from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/meterreading', methods=['GET','POST'])
def meter_reading():
    if request.method == 'GET':
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Meter Reading System</title>
        </head>
        <body>
            <h2>Meter Reading System</h2>
            <form id="meterForm">
                <label>MeterID：</label>
                <input type="text" id="meter_id" required>
                <br>
                <label>UserID：</label>
                <input type="text" id="user_id" required>
                <br>
                <label>Time：</label>
                <input type="datetime-local" id="time" required>
                <br>
                <label>Meter reading (kWh)：</label>
                <input type="number" id="reading" step="0.01" required>
                <br><br>
                <button type="submit">Submit</button>
            </form>

            <script>
            document.getElementById("meterForm").addEventListener("submit", function(event) {
                event.preventDefault();
                fetch("/meterreading", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        meter_id: document.getElementById("meter_id").value,
                        user_id: document.getElementById("user_id").value,
                        time: document.getElementById("time").value,
                        reading: parseFloat(document.getElementById("reading").value)
                    })
                })
                .then(response => response.json())
                .then(data => alert(data.message))
                .catch(error => console.error("Failure:", error));
            });
            </script>
        </body>
        </html>
    
        """
    elif request.method == 'POST':

        data = request.get_json()
        if not all(k in data for k in ("meter_id", "user_id", "time", "reading")):
            return jsonify({"status": "error", "message": "Please fill out all blanks."}), 400

        meter_id = data["meter_id"]
        user_id = data["user_id"]
        time = data["time"]
        reading = data["reading"]

        # 这里可以存入数据库，目前只返回数据
        return jsonify({"status": "success", "message": f"We have received: {meter_id}, {user_id}, from{starttime} to {endtime}, {reading}"}), 201

if __name__ == '__main__':
    app.run(debug=True)
