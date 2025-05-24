import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timezone

# ✅ เชื่อมต่อกับ MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['mydatabase']  # ✅ ใช้ชื่อ Database ที่ถูกต้อง
collection = db['Data']

# ✅ กำหนดรายการไฟล์ CSV ที่ต้องการอัปโหลด
csv_files = [
    r"C:\Users\USER\Desktop\loadmanament\Data_for_January_4th (1).csv"
]

# ✅ อ่านและบันทึกข้อมูล CSV ไปยัง MongoDB
for file_path in csv_files:
    if os.path.exists(file_path) and file_path.endswith(".csv"):  # ตรวจสอบว่าไฟล์มีอยู่จริง
        print(f"📂 กำลังโหลด: {file_path}")

        # ✅ โหลดข้อมูลจาก CSV
        df = pd.read_csv(file_path)

        # ✅ ตรวจสอบว่ามีคอลัมน์ timestamp หรือไม่
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)  # ✅ แปลง timestamp เป็น UTC
            df["timestamp"] = df["timestamp"].apply(lambda x: x.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))  # ✅ แปลงเป็น ISO 8601 + "Z" และเพิ่ม ".000Z"

        # ✅ แปลงข้อมูลเป็น JSON และบันทึกลง MongoDB
        records = df.to_dict(orient='records')
        if records:
            collection.insert_many(records)
            print(f"✅ บันทึกข้อมูลจาก {os.path.basename(file_path)} ไปยัง MongoDB เรียบร้อยแล้ว! (ISO 8601 + .000Z format)")
        else:
            print(f"⚠️ ไฟล์ {os.path.basename(file_path)} ไม่มีข้อมูลที่สามารถบันทึกได้")
    else:
        print(f"❌ ไม่พบไฟล์: {file_path}")

print("🚀 อัปโหลดข้อมูลจาก CSV ไปยัง MongoDB เสร็จสมบูรณ์!")
