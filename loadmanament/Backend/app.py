import os
import pandas as pd
from pymongo import MongoClient
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_apscheduler import APScheduler
from LSTM import predict_lstm
from cnn_lstm_model import predict_cnn_lstm
from datetime import datetime, timezone,time
from dateutil import parser
from power_calculation import process_power_data,calculate_difference,calculate_time_period





app = Flask(__name__)
CORS(app)

# ---------------------------
# APScheduler Configuration
# ---------------------------
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# ---------------------------
# MongoDB Connection
# ---------------------------
client = os.getenv('client')  # mongodb://localhost:27017/
db = os.getenv('db')  # mydatabase
predictions_collection = os.getenv('predictions_collection')  # Predictions
realtime_collection = os.getenv('realtime_collection')  # realtimedata
collection = os.getenv('collection')  # realtimedata

print(client)
print(db)
print(predictions_collection)
print(realtime_collection)
print(collection)

# ---------------------------
# Helper: Convert Timestamp to ISO 8601 with 'Z'
# ---------------------------
def convert_to_iso(timestamp):
    """
    Converts a timestamp string (or datetime) to ISO 8601 format with a trailing 'Z'.
    """
    if isinstance(timestamp, str):
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        raise ValueError("Unsupported timestamp type.")
    return dt.replace(tzinfo=timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")

# ---------------------------
# Endpoint: Predict with LSTM and Save to MongoDB
# ---------------------------
@app.route('/predictlstm', methods=['POST'])
def predict():
    try:
        data = request.json
        print("➡️ Data received:", data)

        building = data.get('building')
        params = data.get('parameters')
        if not building or not params:
            return jsonify({'error': "Missing 'building' or 'parameters'"}), 400

        # Query raw data for the specified building from MongoDB (collection "Data")
        building_data = list(db["Data"].find(
            {"house_no": building},
            {"_id": 0, "timestamp": 1, "raw_p_h": 1}
        ))
        if not building_data:
            return jsonify({'error': f"No data found for building {building}"}), 404

        # Run LSTM prediction function
        result = predict_lstm(building_data, params)
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        # Convert each prediction's timestamp to ISO 8601 with 'Z'
        for prediction in result["predict"]:
            prediction["timestamp"] = convert_to_iso(prediction["timestamp"])
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow())

        # Save prediction result to MongoDB
        prediction_entry = {
            "building": building,
            "model": "LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse"),
            "rmse": result.get("rmse"),
            "mae": result.get("mae")
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ Saved LSTM predictions for {building} at {first_prediction_timestamp}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ---------------------------
# Endpoint: Predict with CNN-LSTM and Save to MongoDB
# ---------------------------
@app.route('/predict_cnn_lstm', methods=['POST'])
def predict_CNN_LSTM():
    try:
        data = request.json
        print("➡️ Data received:", data)

        building = data.get('building')
        params = data.get('parameters')
        if not building or not params:
            return jsonify({'error': "Missing 'building' or 'parameters'"}), 400

        # Query raw data for the specified building from MongoDB (collection "Data")
        building_data = list(db["Data"].find(
            {"house_no": building},
            {"_id": 0, "timestamp": 1, "raw_p_h": 1}
        ))
        if not building_data:
            return jsonify({'error': f"No data found for building {building}"}), 404

        # Run CNN-LSTM prediction function
        result = predict_cnn_lstm(building_data, params)
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        # Convert timestamps to ISO 8601 with 'Z'
        for prediction in result["predict"]:
            prediction["timestamp"] = convert_to_iso(prediction["timestamp"])
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow())

        # Save prediction result to MongoDB
        prediction_entry = {
            "building": building,
            "model": "CNN-LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse"),
            "rmse": result.get("rmse"),
            "mae": result.get("mae")
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ Saved CNN-LSTM predictions for {building} at {first_prediction_timestamp}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ---------------------------
# Endpoint: Calculate Power Using Latest Prediction Data from MongoDB
# ---------------------------
@app.route('/calculate_power', methods=['POST'])
def calculate_power_api():
    data = request.json
    Psh = data.get('Psh', 4)
    carbon_factor = data.get('carbon_factor', 0.5)  # kg CO2/kWh
    electricity_rate = data.get('electricity_rate', 4.15)  # THB/kWh
    building = data.get('building', 'h2')
    model_type = data.get('model', 'LSTM')  # ตัวเลือก: "LSTM" หรือ "CNN-LSTM"
    selected_date = data.get('date')  # หากมีระบุวันที่ เช่น "2024-01-05"

    try:
        # ถ้ามีการระบุวันที่ ให้แปลงเป็น start_date และ end_date
        if selected_date:
            start_date = datetime.strptime(selected_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_date = start_date.replace(hour=23, minute=59, second=59)
            query = {
                "building": building,
                "model": model_type,
                "timestamp": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
            }
            # ดึง prediction ตามวันที่ที่ระบุ (เรียงจากล่าสุดไปหาเก่าสุด)
            prediction_record = db["Predictions"].find_one(query, sort=[("timestamp", -1)])
        else:
            # หากไม่ได้ระบุวันที่ ให้ดึง prediction ล่าสุด
            prediction_record = db["Predictions"].find_one(
                {"building": building, "model": model_type},
                sort=[("timestamp", -1)]
            )

        if not prediction_record:
            return jsonify({"error": f"No predictions found for building {building} with model {model_type}"}), 404

        # Extract predictions
        predict_data = prediction_record.get("predictions", [])
        if not predict_data:
            return jsonify({"error": "Prediction data is empty"}), 404

        # Convert predictions list into a DataFrame
        df = pd.DataFrame(predict_data)

        # Process power data using your custom function
        results = process_power_data(df, Psh)

        # Calculate special metrics
        P_New_array = [record["P_New"] for record in results if "P_New" in record]
        P_Peak_New = max(P_New_array) if P_New_array else 0
        Reduction_Peak = P_Peak_New - Psh

        starttimes = []
        endtimes = []
        in_positive_phase = False

        for record in results:
            P_B_out = record.get("P_B_out", 0)
            timestamp = record.get("timestamp", "Unknown")
            if P_B_out > 0 and not in_positive_phase:
                starttimes.append(timestamp)
                in_positive_phase = True
            elif P_B_out == 0 and in_positive_phase:
                endtimes.append(timestamp)
                in_positive_phase = False

        if in_positive_phase:
            endtimes.append("Still ongoing")

        time_period = calculate_time_period(starttimes, endtimes)
        results = calculate_difference(results)

        Email_status = 1 if starttimes and endtimes else 0
        total_Difference_kWh = sum(record.get("Difference_kWh", 0) for record in results)
        total_carbon_emission = total_Difference_kWh * carbon_factor  # kg CO2
        total_electricity_cost = total_Difference_kWh * electricity_rate  # THB

        return jsonify({
            "results": results,
            "P_Peak_New": P_Peak_New,
            "Reduction_Peak": Reduction_Peak,
            "starttimes": starttimes,
            "endtimes": endtimes,
            "time_period": time_period,
            "Email_status": Email_status,
            "Total_Difference_kWh": total_Difference_kWh,
            "Total_Carbon_Emission": total_carbon_emission,
            "Total_Electricity_Cost": total_electricity_cost
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------
# Endpoint: Get Predictions by Date
# ---------------------------
@app.route('/calculate_cbl_by_date', methods=['GET'])
def calculate_cbl_by_date():
    try:
        building = request.args.get('building', 'h2').strip()
        selected_date_str = request.args.get('date', '').strip()  # Format: YYYY-MM-DD

        if not selected_date_str:
            return jsonify({"error": "Missing 'date' parameter"}), 400

        # แปลง selected_date_str เป็น date object
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        selected_weekday = selected_date.weekday()  # 0=Monday, ... 6=Sunday

        # กำหนด end_datetime เป็นเวลาสิ้นสุดของวันที่เลือก (offset-aware)
        end_datetime = datetime.combine(selected_date, time(23, 59, 59)).replace(tzinfo=timezone.utc)
        
        # ดึงเอกสารทั้งหมดสำหรับ building ที่ระบุ (timestamp, house_no, raw_p_h)
        docs = list(collection.find(
            {"house_no": building},
            {"timestamp": 1, "house_no": 1, "raw_p_h": 1, "_id": 0}
        ))
        if not docs:
            return jsonify({"error": f"No data found for house_no '{building}'"}), 404

        # รวบรวม distinct dates จากเอกสารโดยแปลง timestamp จาก string เป็น datetime
        distinct_dates = set()
        for doc in docs:
            ts_val = doc.get("timestamp")
            if not isinstance(ts_val, datetime):
                ts = parser.parse(ts_val)
            else:
                ts = ts_val
            doc_date = ts.date()
            if doc_date > selected_date:
                continue
            if selected_weekday < 5:
                if doc_date.weekday() < 5:  # weekday
                    distinct_dates.add(doc_date)
            else:
                if doc_date.weekday() >= 5:  # weekend
                    distinct_dates.add(doc_date)

        # เรียงลำดับ distinct_dates จากล่าสุดไปเก่า แล้วเลือก 10 วันล่าสุด
        distinct_dates = sorted(list(distinct_dates), reverse=True)
        if len(distinct_dates) > 10:
            distinct_dates = distinct_dates[:10]
        if not distinct_dates:
            day_type = "weekday" if selected_weekday < 5 else "weekend"
            return jsonify({"error": f"No {day_type} data found for house_no '{building}' up to {selected_date_str}"}), 404

        # หาวันที่เก่าที่สุดในช่วง 10 วันล่าสุดและทำให้เป็น offset-aware
        min_date = min(distinct_dates)
        start_datetime = datetime.combine(min_date, datetime.min.time()).replace(tzinfo=timezone.utc)

        # ดึงเอกสารในช่วง retrospective: จาก start_datetime ถึง end_datetime
        docs_filtered = []
        for doc in docs:
            ts_val = doc.get("timestamp")
            ts = parser.parse(ts_val) if isinstance(ts_val, str) else ts_val
            if start_datetime <= ts <= end_datetime:
                docs_filtered.append(doc)
        if not docs_filtered:
            return jsonify({"error": f"No data found for house_no '{building}' in the retrospective period"}), 404

        # แปลงเอกสารที่ได้เป็น DataFrame
        df = pd.DataFrame(docs_filtered)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # ปัด (floor) timestamp ให้เป็นชั่วโมง
        df['hour'] = df['timestamp'].dt.floor('h')

        # คำนวณค่าเฉลี่ยรายชั่วโมงของ raw_p_h
        df_hourly = df.groupby(['house_no', 'hour'])['raw_p_h'].mean().reset_index()
        # สกัดชั่วโมงของวัน
        df_hourly['hour_of_day'] = df_hourly['hour'].dt.hour

        # คำนวณ CBL โดยการเฉลี่ยค่า raw_p_h ในแต่ละชั่วโมง
        cbl = df_hourly.groupby(['house_no', 'hour_of_day'])['raw_p_h'].mean().reset_index()
        cbl.rename(columns={'raw_p_h': 'CBL'}, inplace=True)

        return jsonify({"cbl": cbl.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------------------------
# Endpoint: Get Realtime Data by Date
# ---------------------------

@app.route('/get_predictions_by_date', methods=['GET'])
def get_predictions_by_date():
    """ API สำหรับดึงค่าพยากรณ์ตามวันที่ที่เลือกจาก MongoDB (ISO 8601 + 'Z') """
    try:
        building = request.args.get('building', '').strip()
        model_type = request.args.get('model', 'LSTM').strip()
        selected_date = request.args.get('date', '').strip()

        if not building:
            return jsonify({"error": "Missing 'building' parameter"}), 400
        if not selected_date:
            return jsonify({"error": "Missing 'date' parameter"}), 400

        start_timestamp = datetime.strptime(selected_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_timestamp = start_timestamp.replace(hour=23, minute=59, second=59)

        data = list(predictions_collection.find(
            {
                "building": building,
                "model": model_type,
                "timestamp": {"$gte": start_timestamp.isoformat(), "$lte": end_timestamp.isoformat()}
            },
            {"_id": 0}
        ))
        if not data:
            return jsonify({"error": f"No predictions found for {building} on {selected_date} with model {model_type}"}), 404

        return jsonify({"predictions": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ---------------------------
# Scheduled Job: Daily LSTM Prediction at 23:50
# ---------------------------
def scheduled_predict_lstm():
    try:
        building = "h2"  # or change as needed
        params = {
            "epochs": 10,
            "batch_size": 256,
            "time_step": 1344,
            "forecast_horizon": 96
        }
        building_data = list(db["Data"].find(
            {"house_no": building},
            {"_id": 0, "timestamp": 1, "raw_p_h": 1}
        ))
        if not building_data:
            print(f"No data found for building {building}")
            return

        result = predict_lstm(building_data, params)
        if "error" in result:
            print("Error in LSTM prediction:", result["error"])
            return

        for prediction in result["predict"]:
            prediction["timestamp"] = convert_to_iso(prediction["timestamp"])
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow())

        prediction_entry = {
            "building": building,
            "model": "LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse"),
            "rmse": result.get("rmse"),
            "mae": result.get("mae")
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ [Scheduled LSTM] Saved predictions for {building} at {first_prediction_timestamp}")
    except Exception as e:
        print(f"❌ [Scheduled LSTM] Exception: {str(e)}")

# ---------------------------
# Scheduled Job: Daily CNN-LSTM Prediction at 23:50
# ---------------------------
def scheduled_predict_cnn_lstm():
    try:
        building = "h2"
        params = {
            "epochs": 10,
            "batch_size": 256,
            "time_step": 1344,
            "forecast_horizon": 96
        }
        building_data = list(db["Data"].find(
            {"house_no": building},
            {"_id": 0, "timestamp": 1, "raw_p_h": 1}
        ))
        if not building_data:
            print(f"No data found for building {building}")
            return

        result = predict_cnn_lstm(building_data, params)
        if "error" in result:
            print("Error in CNN-LSTM prediction:", result["error"])
            return

        for prediction in result["predict"]:
            prediction["timestamp"] = convert_to_iso(prediction["timestamp"])
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow())

        prediction_entry = {
            "building": building,
            "model": "CNN-LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse"),
            "rmse": result.get("rmse"),
            "mae": result.get("mae")
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ [Scheduled CNN-LSTM] Saved predictions for {building} at {first_prediction_timestamp}")
    except Exception as e:
        print(f"❌ [Scheduled CNN-LSTM] Exception: {str(e)}")

@app.route('/get_realtime_data_by_date', methods=['GET'])
def get_realtime_data_by_date():
    try:
        building = request.args.get('building', '').strip()
        selected_date = request.args.get('date', '').strip()
        if not building or not selected_date:
            return jsonify({"error": "Missing 'building' or 'date' parameter"}), 400

        start_timestamp = datetime.strptime(selected_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_timestamp = start_timestamp.replace(hour=23, minute=59, second=59)
        data = list(realtime_collection.find(
            {
                "house_no": building,
                "timestamp": {"$gte": start_timestamp.isoformat(), "$lte": end_timestamp.isoformat()}
            },
            {"_id": 0, "raw_p_h": 1, "timestamp": 1}
        ))
        if not data:
            return jsonify({"error": f"No realtime data found for {building} on {selected_date}"}), 404
        # Optionally, format the timestamp as ISO 8601 with 'Z'
        for record in data:
            record["timestamp"] = convert_to_iso(record["timestamp"])
        return jsonify({"realtime_data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

        

# Schedule the daily jobs at 23:50
scheduler.add_job(
    id='job_predict_lstm',
    func=scheduled_predict_lstm,
    trigger='cron',
    hour=18,
    minute=31
)
scheduler.add_job(
    id='job_predict_cnn_lstm',
    func=scheduled_predict_cnn_lstm,
    trigger='cron',
    hour=18,
    minute=32
)

# ---------------------------
# Start Flask Server
# ---------------------------
if __name__ == '__main__':
    print("🚀 Starting Flask Server...")
    app.run(debug=True, host='127.0.0.1', port=5000)
