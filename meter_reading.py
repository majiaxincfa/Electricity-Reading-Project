from flask import Flask, request, jsonify
import pandas as pd
from datetime import datetime


app = Flask(__name__)

#初始化表格
data_columns = ["meter_id", "time", "reading"]
data_store = pd.DataFrame(columns=data_columns)

#读取本地database
local_db = pd.read_csv('local_db.csv')

@app.route('/meterreading', methods=['GET','POST'])
def meter_reading():
    global data_store

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
        if not all(k in data for k in ("meter_id", "time", "reading")):
            return jsonify({"status": "error", "message": "Please fill out all blanks."}), 400

        meter_id = data["meter_id"]
        time = data["time"]
        reading = data["reading"]

        #check meterID是否存在于库中,临时库和本地库
        if meter_id not in data_store["meter_id"].values and not in local_db["meter_id"].values:
            return jsonify({"status": "error", "message": "You are not registered. Please register first."}), 403

        
        #check 时间是否在12点到1点
        time_obj = datetime.strptime(time, "%Y-%m-%dT%H:%M") 

        if time_obj.hour == 0 and time_obj.minute > 0:
            return jsonify({"status": "error", "message": "System maintenance in progress. Please try again after 1am."}), 403
        elif time_obj.hour == 1 and time_obj.minute == 0:
            return jsonify({"status": "error", "message": "System maintenance in progress. Please try again after 1am."}), 403

        
        # 追加数据到 DataFrame
        new_data = pd.DataFrame([data])
        print(new_data)
        data_store = pd.concat([data_store, new_data], ignore_index=True)
        

        # 这里可以存入数据库，目前只返回数据
        return jsonify({"status": "success", "message": f"We have received: {meter_id}, {time}, {reading}"}), 201

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True) 
