import pandas as pd
from datetime import datetime 

# 🔹 ค่าคงที่
R_TR = 100  # Transformer rating
P_F = 0.9  # Power factor
OL = 0.8  # Overload limit
RF = 0.15  # Reverse Flow limit
N = 0.81  # loss BESS
battery_size = 10  # kWh
battery_size_power = battery_size * 60 / 15  # kW
Power_bat_max = 15  # kW power ของ battery ที่จ่ายได้สูงสุดทุก 15 นาที

start_time = 9  # TOU rate start
end_time = 22  # TOU rate end

# คำนวณ TR limit
TR_limit = R_TR * P_F * OL
RF_limit = R_TR * P_F * RF

# 🔹 ฟังก์ชันคำนวณพลังงาน
def calculate_power(P_forecasting, timestamp, Psh):
    if start_time <= timestamp.hour < end_time:
        if P_forecasting > 0:
            if P_forecasting > Psh:
                P_New = Psh
                P_B_out = P_forecasting - P_New
            else:
                P_New = min(P_forecasting, TR_limit)
                P_B_out = P_forecasting - P_New
        elif P_forecasting < 0:
            if abs(P_forecasting) > RF_limit:
                P_New = -RF_limit
                P_B_out = P_forecasting - P_New
            else:
                P_New = max(P_forecasting, -RF_limit)
                P_B_out = P_forecasting - P_New
    else:
        if P_forecasting > 0:
            P_New = min(P_forecasting, TR_limit)
            P_B_out = P_forecasting - P_New
        elif P_forecasting < 0:
            if abs(P_forecasting) > RF_limit:
                P_New = -RF_limit
                P_B_out = P_forecasting - P_New
            else:
                P_New = max(P_forecasting, -RF_limit)
                P_B_out = P_forecasting - P_New

    P_Bat = P_B_out / N if P_New != 0 else 0
    return P_New, P_B_out, P_Bat

# 🔹 ฟังก์ชันตรวจสอบและปรับค่า P_Bat
def check_power_bat_max(P_Bat_1, previous_battery_usage):
    P_Bat = min(P_Bat_1, Power_bat_max)
    total_battery_usage = previous_battery_usage + P_Bat
    if total_battery_usage > battery_size_power:
        P_Bat = battery_size_power - previous_battery_usage
        total_battery_usage = battery_size_power
    total_battery_usage = max(total_battery_usage, 0)
    return P_Bat, total_battery_usage

# 🔹 ฟังก์ชันหลัก
def process_power_data(df, Psh):
    results = []
    previous_battery_usage = 0
    P_New_max = 0

    for i in range(len(df)):
        P_forecasting = df.loc[i, 'value']
        timestamp = pd.to_datetime(df.loc[i, 'timestamp'])

        P_New, P_B_out, P_Bat_1 = calculate_power(P_forecasting, timestamp, Psh)
        P_Bat, total_battery_usage = check_power_bat_max(P_Bat_1, previous_battery_usage)
        P_New_max = max(P_New, P_New_max)
        previous_battery_usage = total_battery_usage

        results.append({
            'timestamp': df.loc[i, 'timestamp'],
            'P_forecasting': P_forecasting,
            'P_New': P_New,
            'P_New_max': P_New_max,
            'P_B_out': P_B_out,
            'P_Bat_1': P_Bat_1,
            'P_Bat': P_Bat
        })

    return results
# 🔹 คำนวณ P_forecasting - P_New และแปลงเป็น kWh
def calculate_difference(results):
    start_index = None  # ตำแหน่งที่ P_New เริ่มเปลี่ยนแปลง

    for i, record in enumerate(results):
        P_forecasting = record["P_forecasting"]
        P_New = record["P_New"]

        if start_index is None and P_New > 0:
            start_index = i  # บันทึก index ที่เริ่มทำงาน

        if start_index is not None:
            diff = P_forecasting - P_New
            diff_kwh = diff * 0.25  # แปลง kW เป็น kWh (คูณ 0.25 ชม.)
            record["Difference"] = diff
            record["Difference_kWh"] = diff_kwh  # เพิ่มค่า kWh ลงไปใน results

    return results

# 🔹 คำนวณระยะเวลาการทำงานของแบตเตอรี่
def calculate_time_period(starttimes, endtimes):
    time_period = []
    for i in range(len(starttimes)):
        if endtimes[i] != "Still ongoing":
            start_time = datetime.strptime(starttimes[i], "%Y-%m-%dT%H:%M:%S")
            end_time = datetime.strptime(endtimes[i], "%Y-%m-%dT%H:%M:%S")
            duration = end_time - start_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            time_period.append(f"{int(hours)} ชั่วโมง และ {int(minutes)} นาที")
        else:
            time_period.append("ยังคงดำเนินอยู่")
    
    return time_period


