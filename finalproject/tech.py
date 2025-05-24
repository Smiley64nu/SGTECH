# Load data into a DataFrame
df = pd.DataFrame(data)
# Constants
R_TR = 100  # Transformer rating
P_F = 0.9  # Power factor
OL = 0.8  # Overload limit
RF = 0.15 # Reverse Flow limit
N = 0.81 # loss BESS
battery_size = 20 # kWh
battery_size_power = battery_size*60/15 # kW
Power_bat_max = 10 # Kw power ของ battery ที่จ่ายได้สูงสุดทุก 15 นาที

start_time = 9 #ของ TOU rate
end_time = 22  #ของ TOU rate
# Calculate TR limit
TR_limit = R_TR * P_F * OL
RF_limit = R_TR * P_F * RF

# Placeholder for results
results = []

# Function to calculate P_New and P_B_out based on timestamp and P_forecasting
def calculate_power(P_forecasting, timestamp, Psh, TR_limit, RF_limit, N):
    if timestamp.hour >= start_time and timestamp.hour < end_time:
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

# Function to check and adjust P_Bat based on Power_bat_max and battery size
def check_power_bat_max(P_Bat_1, Power_bat_max, battery_size_power, previous_battery_usage):
    if P_Bat_1 > Power_bat_max:
        P_Bat = Power_bat_max
    else:
        P_Bat = P_Bat_1

    # Check if the cumulative battery usage exceeds the battery size
    total_battery_usage = previous_battery_usage + P_Bat

    if total_battery_usage > battery_size_power:
        # If it exceeds, adjust P_Bat to only use the remaining battery capacity
        P_Bat = battery_size_power - previous_battery_usage
        total_battery_usage = battery_size_power  # Ensure it does not exceed the battery size

    # Ensure that total_battery_usage does not become negative
    if total_battery_usage < 0:
         total_battery_usage = 0

    return P_Bat, total_battery_usage
  # Function to recheck and adjust P_New based on new P_Bat using similar conditions as calculate_power
def recheck_p_new(P_forecasting,Power_bat_max, timestamp, P_B_out, P_Bat, Psh, TR_limit, RF_limit):

    if P_forecasting > 0:
      P_New = P_forecasting - P_Bat*N
      P_New = min(P_New, TR_limit)

      if start_time <= timestamp.hour < end_time:
        if Psh == 0:
          P_New = 0
          P_B_out = P_forecasting

          # Recheck P_New
          delP = P_forecasting - Psh
          if delP <= Power_bat_max:
            P_B_out = delP
            P_Bat = P_B_out / N
            P_New = P_forecasting - P_Bat
          elif delP > Power_bat_max:
            P_B_out = Power_bat_max
            P_Bat = P_B_out / N
            P_New = P_forecasting - P_Bat

    elif P_forecasting < 0:
        if abs(P_forecasting) > RF_limit:
          P_New = -RF_limit

        else:
          P_New = max(P_forecasting, -RF_limit)

    else:
        P_New = 0
        P_B_out = 0
    # Ensure P_New does not become negative if P_Bat exceeds the forecasted power
    if P_New < 0:
        P_new = P_forecasting
        P_New = max(P_new ,-RF_limit)

    #P_Bat = P_B_out / N if P_New != 0 else 0

    return P_New

#Function to check Peak of P_New as P_peak_New
def check_P_New_max(P_New, timestamp, P_New_max):
    if start_time <= timestamp.hour < end_time:
        if P_New > P_New_max:
            P_New_max = P_New

        # ถ้า P_New ต่ำกว่า P_New_max ให้ค่า P_New_max คงอยู่
    return P_New_max
# Main function
def main(df, Psh, TR_limit, RF_limit, N,Power_bat_max, battery_size_power):

    results = []
    previous_battery_usage = 0  # Track cumulative battery usage
    P_New_counter = 0  # Initialize P_peak_New
    P_New_max = 0  # Initialize P_New_max


    for i in range(len(df)):
        P_forecasting = df.loc[i, 'Overall Average of Sum of active_power_kw']
        timestamp = pd.to_datetime(df.loc[i, 'timestamp per 15 minutes'])

        P_New, P_B_out, P_Bat_1 = calculate_power(P_forecasting, timestamp, Psh, TR_limit, RF_limit, N)

        # Check and adjust P_Bat based on Power_bat_max and battery size
        P_Bat, total_battery_usage = check_power_bat_max(P_Bat_1, Power_bat_max, battery_size_power, previous_battery_usage)

        # Recalculate P_New based on the new P_Bat value
        P_New = recheck_p_new(P_forecasting,Power_bat_max, timestamp, P_B_out, P_Bat, Psh, TR_limit, RF_limit)

        # Check and adjust P_peak_New
        P_New_max = check_P_New_max(P_New,timestamp,P_New_max)

        # Update the previous battery usage
        previous_battery_usage = total_battery_usage



        results.append({
            'timestamp': df.loc[i, 'timestamp per 15 minutes'],
            'P_forecasting': P_forecasting,
            'P_New': P_New,
            'P_New_max': P_New_max,
            'P_B_out': P_B_out,
            'P_Bat_1': P_Bat_1,
            'P_Bat': P_Bat,

        })

        Fitness_value = P_New_max



    return results


results = main(df, Psh, TR_limit, RF_limit, N, Power_bat_max, battery_size_power)
# email status
# 1 = ส่ง
# 0 = ไม่ส่ง
Email_status = 0  # initial Email status
P_New_array = []

for record in results:
    P_New = record['P_New']
    P_New_array.append(P_New)

P_New_max = max(P_New_array)

P_Peak_New = P_New_max
Reduction_Peak = P_Peak_New - Psh

print("P_Peak:", P_Peak_New)
print("Re_Peak:", Reduction_Peak)

starttimes = []
endtimes = []
in_positive_phase = False

for record in results:
    P_B_out = record.get('P_B_out', 0)
    timestamp = record.get('timestamp', 'Unknown')

    if P_B_out > 0 and not in_positive_phase:
        starttimes.append(timestamp)
        in_positive_phase = True
    elif P_B_out == 0 and in_positive_phase:
        endtimes.append(timestamp)
        in_positive_phase = False

if in_positive_phase:
    endtimes.append("Still ongoing")

positive_count = len(starttimes)

time_period = []

time_formats = ["%H:%M", "%Y-%m-%d %H:%M:%S"]

for i in range(len(starttimes)):
    if endtimes[i] != "Still ongoing":
        parsed_start = False
        parsed_end = False

        for fmt in time_formats:
            try:
                start_time = datetime.strptime(starttimes[i], fmt)
                parsed_start = True
                break
            except ValueError:
                continue

        for fmt in time_formats:
            try:
                end_time = datetime.strptime(endtimes[i], fmt)
                parsed_end = True
                break
            except ValueError:
                continue

        if not parsed_start or not parsed_end:
            print(f"Error: Unexpected time format for start: {starttimes[i]} or end: {endtimes[i]}")
            raise ValueError(f"Unexpected time format in start: {starttimes[i]} or end: {endtimes[i]}")

        duration = end_time - start_time
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        time_period.append(f"{int(hours)} ชั่วโมง และ {int(minutes)} นาที")
    else:
        time_period.append("ยังคงดำเนินอยู่")

# Check if time_period, starttimes, and endtimes are empty and set Email_status
if not time_period and not starttimes and not endtimes:
    Email_status = 0
else:
    Email_status = 1

