import matplotlib.pyplot as plt
import json
from datetime import datetime

# ข้อมูล JSON
data = {
    "predict": [
        {"timestamp": "2024-01-08T00:00:00", "value": 0.892793},
        {"timestamp": "2024-01-08T00:15:00", "value": 1.046287},
        {"timestamp": "2024-01-08T00:30:00", "value": 1.223737},
        {"timestamp": "2024-01-08T00:45:00", "value": 1.410505},
        {"timestamp": "2024-01-08T01:00:00", "value": 1.600828},
        {"timestamp": "2024-01-08T01:15:00", "value": 1.790347},
        {"timestamp": "2024-01-08T01:30:00", "value": 1.976827},
        {"timestamp": "2024-01-08T01:45:00", "value": 2.160273},
        {"timestamp": "2024-01-08T02:00:00", "value": 2.342423},
        {"timestamp": "2024-01-08T02:15:00", "value": 2.525948},
        {"timestamp": "2024-01-08T02:30:00", "value": 2.713642},
        {"timestamp": "2024-01-08T02:45:00", "value": 2.907820},
        {"timestamp": "2024-01-08T03:00:00", "value": 3.109973},
        {"timestamp": "2024-01-08T03:15:00", "value": 3.320668},
        {"timestamp": "2024-01-08T03:30:00", "value": 3.539586},
        {"timestamp": "2024-01-08T03:45:00", "value": 3.765648},
        {"timestamp": "2024-01-08T04:00:00", "value": 3.997144},
        {"timestamp": "2024-01-08T04:15:00", "value": 4.231866},
        {"timestamp": "2024-01-08T04:30:00", "value": 4.467209},
        {"timestamp": "2024-01-08T04:45:00", "value": 4.700289},
        {"timestamp": "2024-01-08T05:00:00", "value": 4.928047},
        {"timestamp": "2024-01-08T05:15:00", "value": 5.147376},
        {"timestamp": "2024-01-08T05:30:00", "value": 5.355248},
        {"timestamp": "2024-01-08T05:45:00", "value": 5.548843},
        {"timestamp": "2024-01-08T06:00:00", "value": 5.725652},
        {"timestamp": "2024-01-08T06:15:00", "value": 5.883563},
        {"timestamp": "2024-01-08T06:30:00", "value": 6.020901},
        {"timestamp": "2024-01-08T06:45:00", "value": 6.136447},
        {"timestamp": "2024-01-08T07:00:00", "value": 6.229434},
        {"timestamp": "2024-01-08T07:15:00", "value": 6.299512},
        {"timestamp": "2024-01-08T07:30:00", "value": 6.346724},
        {"timestamp": "2024-01-08T07:45:00", "value": 6.371464},
        {"timestamp": "2024-01-08T08:00:00", "value": 6.374447},
        {"timestamp": "2024-01-08T08:15:00", "value": 6.356677},
        {"timestamp": "2024-01-08T08:30:00", "value": 6.319415},
        {"timestamp": "2024-01-08T08:45:00", "value": 6.264166},
        {"timestamp": "2024-01-08T09:00:00", "value": 6.192645}
    ]
}

# แปลง JSON เป็น Python object
timestamps = [datetime.fromisoformat(entry["timestamp"]) for entry in data["predict"]]
values = [entry["value"] for entry in data["predict"]]

# พล็อตกราฟ
plt.figure(figsize=(12, 6))
plt.plot(timestamps, values, marker='o', linestyle='-', color='b', label='Predicted Values')
plt.xlabel('Timestamp')
plt.ylabel('Predicted Value')
plt.title('Rolling Forecasting Predictions')
plt.xticks(rotation=45)
plt.legend()
plt.grid(True)
plt.show()
