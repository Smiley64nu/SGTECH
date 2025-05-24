from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import requests

# สร้าง Flask สำหรับ Scheduler
scheduler_app = Flask(__name__)

# ฟังก์ชันสำหรับเรียก API
def call_api():
    print("🕛 Sending scheduled API request...")
    payload = {
        "building": "h2",
        "parameters": {
            "epochs": 10,
            "batch_size": 32,
            "time_step": 20
        }
    }
    url = "http://127.0.0.1:5000/predict"  # URL ของ API หลัก

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ API Success:", response.json())
        else:
            print("❌ API Error:", response.json())
    except Exception as e:
        print("❌ API Exception:", str(e))

# ตั้งค่า Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(call_api, 'cron', hour=14, minute=31)  # ตั้งเวลาให้เรียก API ทุกวันเวลา 00:00 น.
scheduler.start()

@scheduler_app.route("/")
def home():
    return "Scheduler is running..."

if __name__ == "__main__":
    print("🚀 Starting Flask Scheduler...")
    scheduler_app.run(debug=True, port=5001)  # ใช้พอร์ต 5001 สำหรับ Scheduler
