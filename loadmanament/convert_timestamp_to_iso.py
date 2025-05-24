import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# ✅ เชื่อมต่อกับ MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['SGTech']
collection = db['SGTech_Data_ISO']

# ✅ พาธของไฟล์ CSV ปี 2023, 2024 และ 2025
base_path = "C:/Users/User/Desktop/Work_2025/Data_2023_2024"
csv_files = {
    "2023": os.path.join(base_path, "Data_2023/Data(15min)_mean"),
    "2024": os.path.join(base_path, "Data_2024/Data(15min)_mean"),
    "2025": os.path.join(base_path, "Data_2025")  # ✅ เพิ่มโฟลเดอร์ Data_2025
}

# ✅ ฟังก์ชันตรวจสอบว่า timestamp อยู่ในรูปแบบ ISO 8601 หรือไม่
def is_iso8601(timestamp):
    try:
        datetime.fromisoformat(timestamp.replace("Z", "").split(".")[0])  # ✅ แปลง timestamp ให้เป็น ISO 8601 (ไม่มี millisecond)
        return True
    except ValueError:
        return False

# ✅ ฟังก์ชันแปลง timestamp เป็น ISO 8601 `.000Z`
def convert_to_iso8601(timestamp):
    if is_iso8601(timestamp):
        return timestamp  # ✅ ถ้าเป็น ISO 8601 แล้ว ให้ใช้ค่าเดิม
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")  # ✅ กำหนดค่า millisecond เป็น `.000Z`
    except ValueError:
        print(f"❌ Error: Invalid timestamp format -> {timestamp}")
        return None

# ✅ อ่านข้อมูลจาก CSV และบันทึกลง MongoDB
def process_csv_files():
    for year, folder_path in csv_files.items():
        if not os.path.exists(folder_path):
            print(f"⚠ โฟลเดอร์ {folder_path} ไม่พบ, ข้ามไป")
            continue
        
        for filename in os.listdir(folder_path):
            if filename.endswith(".csv"):
                file_path = os.path.join(folder_path, filename)
                
                # ✅ อ่าน CSV
                df = pd.read_csv(file_path)

                # ✅ ตรวจสอบว่ามีคอลัมน์ 'timestamp' หรือไม่
                if 'timestamp' not in df.columns:
                    print(f"⚠ ไม่มีคอลัมน์ 'timestamp' ในไฟล์ {filename}, ข้ามไฟล์นี้")
                    continue
                
                # ✅ แปลง timestamp เป็น ISO 8601 พร้อม `.000Z`
                df["timestamp"] = df["timestamp"].apply(convert_to_iso8601)
                
                # ✅ ลบแถวที่ timestamp ผิดพลาด
                df = df.dropna(subset=["timestamp"])
                
                # ✅ เพิ่มคอลัมน์ปี
                df["year"] = year
                
                # ✅ แปลง DataFrame เป็น JSON
                records = df.to_dict(orient="records")

                # ✅ บันทึกลง MongoDB
                if records:
                    collection.insert_many(records)
                    print(f"✅ นำเข้า {len(records)} records จาก {filename} สำเร็จ")
                else:
                    print(f"⚠ ไม่มีข้อมูลสำหรับไฟล์ {filename}, ข้ามไฟล์นี้")

# ✅ เรียกใช้ฟังก์ชัน
if __name__ == "__main__":
    process_csv_files()
    print("🎯 เสร็จสิ้น! ข้อมูลทั้งหมดถูกบันทึกลง MongoDB แล้ว")
