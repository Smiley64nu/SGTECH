import os
import pandas as pd
from pymongo import MongoClient
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_apscheduler import APScheduler
from LSTM import predict_lstm
from cnn_lstm_model import predict_cnn_lstm
from datetime import datetime, timezone

app = Flask(__name__)
CORS(app)  # Enable CORS

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
# เชื่อมต่อกับ MongoDB
# ---------------------------
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["mydatabase"]
    predictions_collection = db["Predictions"]
    realtime_collection = db["realtimedata"]
    print("✅ Connected to MongoDB Database")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {str(e)}")

# ---------------------------
# ฟังก์ชันช่วยแปลง timestamp เป็น ISO 8601 พร้อม 'Z'
# ---------------------------
def convert_to_iso(timestamp):
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")

# ---------------------------
# Endpoint: Predict with LSTM
# ---------------------------
@app.route('/predictlstm', methods=['POST'])
def predict():
    """ API สำหรับพยากรณ์ด้วย LSTM และบันทึกค่าลง MongoDB (ISO 8601 + 'Z') """
    try:
        data = request.json
        print("➡️ Data received:", data)

        building = data.get('building')
        params = data.get('parameters')

        if not building or not params:
            return jsonify({'error': "Missing 'building' or 'parameters'"}), 400

        # ดึงข้อมูลจาก MongoDB สำหรับอาคารที่ระบุ
        building_data = list(db["Data"].find(
            {"house_no": building},
            {"_id": 0, "timestamp": 1, "raw_p_h": 1}
        ))

        if not building_data:
            return jsonify({'error': f"No data found for building {building}"}), 404

        # พยากรณ์ด้วย LSTM
        result = predict_lstm(building_data, params)
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        # แปลง timestamp ในผลลัพธ์
        for prediction in result["predict"]:
            prediction["timestamp"] = convert_to_iso(prediction["timestamp"])
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow().isoformat())

        # บันทึกค่าพยากรณ์ลง MongoDB
        prediction_entry = {
            "building": building,
            "model": "LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse", None),
            "rmse": result.get("rmse", None),
            "mae": result.get("mae", None)
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ Saved LSTM predictions for {building} with timestamp {first_prediction_timestamp}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ---------------------------
# Endpoint: Predict with CNN-LSTM
# ---------------------------
@app.route('/predict_cnn_lstm', methods=['POST'])
def predict_CNN_LSTM():
    """ API สำหรับพยากรณ์ด้วย CNN-LSTM และบันทึกค่าลง MongoDB (ISO 8601 + 'Z') """
    try:
        data = request.json
        print("➡️ Data received:", data)

        building = data.get('building')
        params = data.get('parameters')

        if not building or not params:
            return jsonify({'error': "Missing 'building' or 'parameters'"}), 400

        # ดึงข้อมูลจาก MongoDB สำหรับอาคารที่ระบุ
        building_data = list(db["Data"].find(
            {"house_no": building},
            {"_id": 0, "timestamp": 1, "raw_p_h": 1}
        ))
        if not building_data:
            return jsonify({'error': f"No data found for building {building}"}), 404

        # พยากรณ์ด้วย CNN-LSTM
        result = predict_cnn_lstm(building_data, params)
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        # แปลง timestamp
        for prediction in result["predict"]:
            prediction["timestamp"] = convert_to_iso(prediction["timestamp"])
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow().isoformat())

        # บันทึกค่าพยากรณ์ลง MongoDB
        prediction_entry = {
            "building": building,
            "model": "CNN-LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse", None),
            "rmse": result.get("rmse", None),
            "mae": result.get("mae", None)
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ Saved CNN-LSTM predictions for {building} with timestamp {first_prediction_timestamp}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ---------------------------
# Endpoint: Get Predictions by Date
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
# Endpoint: Get Realtime Data by Date
# ---------------------------
@app.route('/get_realtime_data_by_date', methods=['GET'])
def get_realtime_data_by_date():
    """
    API สำหรับดึงข้อมูล Realtime ตามวันที่ที่เลือกจาก MongoDB 
    (เฉพาะ raw_p_h และ timestamp ในรูปแบบ ISO 8601 + 'Z')
    """
    try:
        building = request.args.get('building', '').strip()
        selected_date = request.args.get('date', '').strip()

        if not building:
            return jsonify({"error": "Missing 'building' parameter"}), 400
        if not selected_date:
            return jsonify({"error": "Missing 'date' parameter"}), 400

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

        for record in data:
            record["timestamp"] = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).replace(
                tzinfo=timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")
        return jsonify({"realtime_data": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------
# Endpoint: Get Predictions by Range
# ---------------------------
@app.route('/get_predictions_by_range', methods=['GET'])
def get_predictions_by_range():
    """ ดึงค่าพยากรณ์ตามช่วงวันที่ (ISO 8601 + 'Z') """
    try:
        building = request.args.get('building', '').strip()
        model_type = request.args.get('model', 'LSTM').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()

        if not building or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters"}), 400

        start_timestamp = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat()
        end_timestamp = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc).isoformat()

        data = list(predictions_collection.find(
            {
                "building": building,
                "model": model_type,
                "timestamp": {"$gte": start_timestamp, "$lte": end_timestamp}
            },
            {"_id": 0}
        ))
        if not data:
            return jsonify({"error": f"No predictions found for {building} ({model_type}) from {start_date} to {end_date}"}), 404

        return jsonify({"predictions": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------
# Endpoint: Get Realtime Data by Range
# ---------------------------
@app.route('/get_realtime_data_by_range', methods=['GET'])
def get_realtime_data_by_range():
    """ ดึงข้อมูล Real-time ตามช่วงวันที่ (ISO 8601 + 'Z') """
    try:
        building = request.args.get('building', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()

        if not building or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters"}), 400

        start_timestamp = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat()
        end_timestamp = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc).isoformat()

        data = list(realtime_collection.find(
            {
                "house_no": building,
                "timestamp": {"$gte": start_timestamp, "$lte": end_timestamp}
            },
            {"_id": 0, "raw_p_h": 1, "timestamp": 1}
        ))
        if not data:
            return jsonify({"error": f"No realtime data found for {building} from {start_date} to {end_date}"}), 404

        return jsonify({"realtime_data": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------
# Scheduled Job: LSTM Prediction at 23:50 Daily
# ---------------------------
def scheduled_predict_lstm():
    try:
        building = "h2"
        # ใช้พารามิเตอร์ที่ระบุไว้
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
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow().isoformat())

        prediction_entry = {
            "building": building,
            "model": "LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse", None),
            "rmse": result.get("rmse", None),
            "mae": result.get("mae", None)
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ [Scheduled LSTM] Saved predictions for {building} at {first_prediction_timestamp}")
    except Exception as e:
        print(f"❌ [Scheduled LSTM] Exception: {str(e)}")

# ---------------------------
# Scheduled Job: CNN-LSTM Prediction at 23:50 Daily
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
        first_prediction_timestamp = result["predict"][0]["timestamp"] if result["predict"] else convert_to_iso(datetime.utcnow().isoformat())

        prediction_entry = {
            "building": building,
            "model": "CNN-LSTM",
            "timestamp": first_prediction_timestamp,
            "predictions": result["predict"],
            "mse": result.get("mse", None),
            "rmse": result.get("rmse", None),
            "mae": result.get("mae", None)
        }
        predictions_collection.insert_one(prediction_entry)
        print(f"✅ [Scheduled CNN-LSTM] Saved predictions for {building} at {first_prediction_timestamp}")
    except Exception as e:
        print(f"❌ [Scheduled CNN-LSTM] Exception: {str(e)}")

# เพิ่ม Scheduled Jobs ให้รันทุกวันเวลา 23:50 น.
scheduler.add_job(
    id='job_predict_lstm',
    func=scheduled_predict_lstm,
    trigger='cron',
    hour=23,
    minute=50
)

scheduler.add_job(
    id='job_predict_cnn_lstm',
    func=scheduled_predict_cnn_lstm,
    trigger='cron',
    hour=23,
    minute=50
)

# ---------------------------
# เริ่มต้น Server
# ---------------------------
if __name__ == '__main__':
    print("🚀 Starting Flask Server...")
    app.run(debug=True, host='127.0.0.1', port=5000)
