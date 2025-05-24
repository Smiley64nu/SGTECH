# app.py

from flask import Flask, request, jsonify
import matplotlib.pyplot as plt
import io
import base64
from pymongo import MongoClient
from LSTM import predict_lstm
from flask_cors import CORS  # Import Flask-CORS

app = Flask(__name__)
CORS(app)  # เปิดใช้งาน CORS

client = MongoClient('mongodb://localhost:27017/')
db = client['mydatabase']
collection = db['Data'] # เดิมคือ Data

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        building = data['building']
        params = data['parameters']

        # ตรวจสอบว่า Building คือ "อาคารรวม" หรือไม่
        if building == "อาคารรวม":
            # ดึงข้อมูลทุกอาคารจาก MongoDB
            building_data = list(collection.find({}, {'_id': 0, 'timestamp': 1, 'house_no': 1, 'RAW_P_H': 1}))
            
            if not building_data:
                return jsonify({'error': "No data found for any building"}), 404

            # รวมข้อมูลพลังงาน (raw_p_h) ของทุกอาคารตาม timestamp
            import pandas as pd
            df = pd.DataFrame(building_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df_grouped = df.groupby("timestamp")['RAW_P_H'].sum().reset_index()  # รวมค่าพลังงาน
            df_grouped = df_grouped.to_dict('records')  # แปลงกลับเป็น JSON ใช้ใน LSTM
            building_data = df_grouped  # แทนที่ด้วยข้อมูลรวม

        else:
            # ดึงข้อมูลของอาคารที่เลือก
            building_data = list(collection.find({'house_no': building}, {'_id': 0, 'timestamp': 1, 'RAW_P_H': 1}))

        if not building_data:
            return jsonify({'error': f"No data found for building {building}"}), 404

        # เรียกใช้ LSTM สำหรับการคาดการณ์
        result = predict_lstm(building_data, params)
        if "error" in result:
            return jsonify({"error": result["error"]}), 400

        # เตรียม JSON สำหรับส่งข้อมูล
        response_data = {
            "house_no": building,
            "actual": result['actual'],
            "predict": result['predictions'],
            "timestamp": [data['timestamp'] for data in building_data],
            "mae": result['mae'],
            "mape": result['mape'],
            "mse": result['mse'],
            "rmse": result['rmse'],
            "time_taken": result['time_taken']
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)