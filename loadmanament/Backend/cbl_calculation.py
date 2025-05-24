import pandas as pd
import mysql.connector
from datetime import datetime

# ✅ ฟังก์ชันเชื่อมต่อฐานข้อมูล MySQL
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="finalproject",
        autocommit=True
    )

# ✅ ฟังก์ชันดึงข้อมูล CBL ตามเงื่อนไขวัน
def calculate_cbl():
    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)
        db.ping(reconnect=True)

        # ✅ ใช้วันที่ปัจจุบัน
        today = datetime.today()
        weekday = today.weekday()  # (0=จันทร์, 6=อาทิตย์)

        # ✅ ถ้าเป็นวันจันทร์ - ศุกร์ -> ดึงข้อมูลย้อนหลัง 10 วัน (ไม่รวมเสาร์-อาทิตย์)
        if weekday < 5:
            query = """
            SELECT house_no, timestamp, RAW_P_H 
            FROM Data
            WHERE house_no = 'h2' 
            AND timestamp >= (SELECT MIN(timestamp) 
                            FROM (SELECT DISTINCT DATE(timestamp) as timestamp 
                                  FROM Data 
                                  WHERE house_no = 'h2' 
                                  ORDER BY timestamp DESC LIMIT 10) as subquery)
            AND WEEKDAY(timestamp) < 5;  -- ไม่รวมวันเสาร์อาทิตย์
            """
        
        # ✅ ถ้าเป็นวันเสาร์-อาทิตย์ -> ดึงข้อมูลย้อนหลัง 10 วัน (เฉพาะเสาร์-อาทิตย์)
        else:
            query = """
            SELECT house_no, timestamp, RAW_P_H 
            FROM Data
            WHERE house_no = 'h2' 
            AND timestamp >= (SELECT MIN(timestamp) 
                            FROM (SELECT DISTINCT DATE(timestamp) as timestamp 
                                  FROM Data 
                                  WHERE house_no = 'h2' 
                                  ORDER BY timestamp DESC LIMIT 10) as subquery)
            AND WEEKDAY(timestamp) >= 5;  -- เฉพาะวันเสาร์อาทิตย์
            """

        cursor.execute(query)
        building_data = cursor.fetchall()
        db.close()

        if not building_data:
            return {"error": "No data found for house_no 'h2' in the last 10 recorded days"}

        # ✅ แปลงข้อมูลเป็น DataFrame
        df = pd.DataFrame(building_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.floor('h')

        # ✅ รวมข้อมูลจากทุกๆ 15 นาทีเป็นรายชั่วโมง
        df_hourly = df.groupby(['house_no', 'hour'])['RAW_P_H'].mean().reset_index()

        # ✅ คำนวณค่าเฉลี่ยย้อนหลัง 10 วัน
        df_hourly['date'] = df_hourly['hour'].dt.date
        df_hourly['hour_of_day'] = df_hourly['hour'].dt.hour
        cbl = df_hourly.groupby(['house_no', 'hour_of_day'])['RAW_P_H'].mean().reset_index()

        # ✅ เปลี่ยนชื่อคอลัมน์เป็น CBL
        cbl.rename(columns={'RAW_P_H': 'CBL'}, inplace=True)

        return {"cbl": cbl.to_dict(orient="records")}

    except Exception as e:
        return {"error": str(e)}
