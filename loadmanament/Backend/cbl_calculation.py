import pandas as pd
from datetime import datetime, time
from pymongo import MongoClient
from flask import Flask, request, jsonify
from dateutil import parser

app = Flask(__name__)

# ---------------------------
# Connect to MongoDB
# ---------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]      # ปรับตามฐานข้อมูลของคุณ
collection = db["Data"]        # ปรับตามชื่อ collection ที่เก็บข้อมูล

# ---------------------------
# API Endpoint: Calculate CBL for a Retrospective 10-day Period Based on Selected Date
# ---------------------------
@app.route('/calculate_cbl_by_date', methods=['GET'])
def calculate_cbl_by_date():
    try:
        building = request.args.get('building', 'h2').strip()
        selected_date_str = request.args.get('date', '').strip()  # Format: YYYY-MM-DD

        if not selected_date_str:
            return jsonify({"error": "Missing 'date' parameter"}), 400

        # แปลงวันที่ที่เลือกเป็น date object
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        selected_weekday = selected_date.weekday()  # 0=จันทร์, ... 6=อาทิตย์

        # ดึงเอกสารทั้งหมดสำหรับ building ที่ระบุ (timestamp เก็บเป็น string)
        docs = list(collection.find(
            {"house_no": building},
            {"timestamp": 1, "_id": 0}
        ))
        if not docs:
            return jsonify({"error": f"No data found for house_no '{building}'"}), 404

        # รวบรวม distinct dates จากเอกสารโดยแปลง timestamp จาก string เป็น datetime
        distinct_dates = set()
        for doc in docs:
            ts_val = doc.get("timestamp")
            # แปลงเป็น datetime หากเป็น string
            ts = parser.parse(ts_val) if isinstance(ts_val, str) else ts_val
            doc_date = ts.date()
            # ดึงเฉพาะข้อมูลที่มีวันที่น้อยกว่าหรือเท่ากับวันที่เลือก
            if doc_date > selected_date:
                continue
            # ตรวจสอบประเภทของวัน: weekday หรือ weekend
            if selected_weekday < 5:
                if doc_date.weekday() < 5:
                    distinct_dates.add(doc_date)
            else:
                if doc_date.weekday() >= 5:
                    distinct_dates.add(doc_date)

        # เรียงลำดับ distinct dates จากล่าสุดไปเก่า แล้วเลือก 10 วันล่าสุด
        distinct_dates = sorted(list(distinct_dates), reverse=True)
        if len(distinct_dates) > 10:
            distinct_dates = distinct_dates[:10]
        if not distinct_dates:
            day_type = "weekday" if selected_weekday < 5 else "weekend"
            return jsonify({"error": f"No {day_type} data found for house_no '{building}' up to {selected_date_str}"}), 404

        # หาวันที่เก่าที่สุดในช่วง 10 วันล่าสุด
        min_date = min(distinct_dates)
        start_datetime = datetime.combine(min_date, datetime.min.time())
        # กำหนด end_datetime เป็นเวลาสิ้นสุดของวันที่เลือก
        end_datetime = datetime.combine(selected_date, time(23, 59, 59))

        # ดึงเอกสารในช่วง retrospective (จาก start_datetime ถึง end_datetime)
        docs_filtered = []
        for doc in docs:
            ts_val = doc.get("timestamp")
            ts = parser.parse(ts_val) if isinstance(ts_val, str) else ts_val
            if start_datetime <= ts <= end_datetime:
                # ให้รวม field RAW_P_H ด้วย (สมมติว่ามี field นี้ในเอกสาร)
                docs_filtered.append(doc)
        if not docs_filtered:
            return jsonify({"error": f"No data found for house_no '{building}' in the retrospective period"}), 404

        # แปลงเอกสารที่ได้เป็น DataFrame
        df = pd.DataFrame(docs_filtered)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # ปัด (floor) timestamp ให้เป็นชั่วโมง
        df['hour'] = df['timestamp'].dt.floor('h')

        # คำนวณค่าเฉลี่ยรายชั่วโมงของ RAW_P_H
        df_hourly = df.groupby(['house_no', 'hour'])['RAW_P_H'].mean().reset_index()
        df_hourly['hour_of_day'] = df_hourly['hour'].dt.hour

        # คำนวณ CBL โดยการเฉลี่ยรายชั่วโมงของ RAW_P_H สำหรับแต่ละชั่วโมงของวัน
        cbl = df_hourly.groupby(['house_no', 'hour_of_day'])['RAW_P_H'].mean().reset_index()
        cbl.rename(columns={'RAW_P_H': 'CBL'}, inplace=True)

        return jsonify({"cbl": cbl.to_dict(orient="records")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
