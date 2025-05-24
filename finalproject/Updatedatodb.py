import pandas as pd
import mysql.connector

# โหลดข้อมูลจาก CSV
file_path = r'C:\Users\USER\Desktop\New folder (7)\loadmanament\Data2024_h2_15min (1).csv'
data = pd.read_csv(file_path)

# แทนที่ NaN ด้วย None
data = data.where(pd.notnull(data), None)

# ลบแถวที่มีค่า NULL ในคอลัมน์สำคัญ
data = data.dropna(subset=['timestamp', 'RAW_P_H', 'house_no'])

# เชื่อมต่อ MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="finalproject"
)
cursor = db.cursor()

# คำสั่ง SQL สำหรับ INSERT ข้อมูล
insert_query = """
INSERT INTO data (timestamp, RAW_P_H, RAW_P_H_PV, RAW_E_H_IM, RAW_E_H_EX, FLAG, house_no)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

# เตรียมข้อมูลเพื่อ INSERT
records = []
for _, row in data.iterrows():
    records.append((
        row['timestamp'], 
        row['RAW_P_H'], 
        row['RAW_P_H_PV'], 
        row['RAW_E_H_IM'], 
        row['RAW_E_H_EX'], 
        row['FLAG'], 
        row['house_no']
    ))

# ตรวจสอบข้อมูลก่อน INSERT
print(f"🔍 Total records to insert: {len(records)}")

# ทำการ INSERT ข้อมูล
cursor.executemany(insert_query, records)
db.commit()

# ปิดการเชื่อมต่อ
cursor.close()
db.close()
print(f"✅ Inserted {len(records)} records into MySQL database.")
