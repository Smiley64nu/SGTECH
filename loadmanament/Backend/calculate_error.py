import requests
import numpy as np
import json

# 🔹 URL ของ API
API_URL = "http://127.0.0.1:5000/calculate_power2"

def fetch_data():
    """ เรียก API และดึงข้อมูล JSON """
    try:
        response = requests.post(API_URL)
        if response.status_code == 200:
            return response.json()  # แปลง JSON เป็น Dictionary
        else:
            print(f"❌ Error: API returned status code {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Exception while fetching API: {e}")
        return None

def calculate_error(data):
    """ คำนวณค่า MSE, MAE, RMSE """
    try:
        # 🔹 ดึงค่าที่พยากรณ์ (P_forecasting) และค่าจริง (P_New) จาก JSON
        actual_values = np.array([entry["P_New"] for entry in data["results"]])
        predicted_values = np.array([entry["P_forecasting"] for entry in data["results"]])

        # 🔹 คำนวณค่า Error Metrics
        mse = np.mean((actual_values - predicted_values) ** 2)
        mae = np.mean(np.abs(actual_values - predicted_values))
        rmse = np.sqrt(mse)

        return {
            "MSE": round(mse, 4),
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
        }
    
    except Exception as e:
        print(f"❌ Exception while calculating error: {e}")
        return None

if __name__ == "__main__":
    # 🔹 ดึงข้อมูลจาก API
    api_data = fetch_data()
    
    if api_data:
        # 🔹 คำนวณค่า Error
        error_metrics = calculate_error(api_data)
        
        if error_metrics:
            print("📊 Error Metrics Calculation:")
            print(json.dumps(error_metrics, indent=4))
        else:
            print("❌ Failed to calculate error metrics.")
    else:
        print("❌ No data received from API.")
