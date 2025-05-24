import pandas as pd
import mysql.connector
from flask import Flask, jsonify

app = Flask(__name__)

# ฟังก์ชันเชื่อมต่อ MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="finalproject"
    )

@app.route('/calculate_cbl', methods=['GET'])
def calculate_cbl():
    try:
        # เชื่อมต่อ Database
        db = get_db_connection()

        # ✅ ใช้ con=db เพื่อแก้ปัญหาการอ่าน SQL
        query = """
        SELECT house_no, timestamp, RAW_P_H 
        FROM Data
        WHERE timestamp >= NOW() - INTERVAL 10 DAY;
        """
        df = pd.read_sql(query, con=db)
        db.close()  # ปิดการเชื่อมต่อ

        if df.empty:
            return jsonify({"error": "No data found"}), 404

        # แปลง timestamp เป็น datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.floor('H')  # ปัดค่าให้เป็นชั่วโมง

        # รวมค่าใช้ไฟฟ้าทุก 15 นาทีให้เป็นรายชั่วโมง
        df_hourly = df.groupby(['house_no', 'hour'])['RAW_P_H'].mean().reset_index()

        # ดึงเฉพาะค่าเฉลี่ยย้อนหลัง 10 วันของแต่ละช่วงชั่วโมง
        df_hourly['date'] = df_hourly['hour'].dt.date
        df_hourly['hour_of_day'] = df_hourly['hour'].dt.hour
        cbl = df_hourly.groupby(['house_no', 'hour_of_day'])['RAW_P_H'].mean().reset_index()

        # เปลี่ยนชื่อคอลัมน์เป็น CBL
        cbl.rename(columns={'RAW_P_H': 'CBL'}, inplace=True)

        # คืนค่า JSON response
        return jsonify({"cbl": cbl.to_dict(orient="records")})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
