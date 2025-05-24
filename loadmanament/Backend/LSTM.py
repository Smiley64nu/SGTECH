import os
import numpy as np
import pandas as pd
import time
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Input
from keras.optimizers import Adam

def predict_lstm(house_data, params):
    try:
        epochs = int(params.get("epochs", 100))
        batch_size = int(params.get("batch_size", 256))
        time_step = int(params.get("time_step", 1344))
        forecast_horizon = int(params.get("forecast_horizon", 96))

        if not house_data:
            raise ValueError("Invalid or empty house data provided")

        df = pd.DataFrame(house_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df['raw_p_h'] = df['raw_p_h'].replace([np.inf, -np.inf], np.nan).ffill().bfill()

        # ✅ เพิ่มวันในสัปดาห์ (Monday=0, Sunday=6)
        df['day_of_week'] = df.index.dayofweek  

        dataset = df[['raw_p_h', 'day_of_week']].values
        timestamps = df.index.tolist()

        X, y = [], []
        for i in range(len(dataset) - time_step - 1):
            X.append(dataset[i:(i + time_step)])
            y.append(dataset[i + time_step, 0])  # ใช้ RAW_P_H เป็นค่าเป้าหมาย

        X, y = np.array(X), np.array(y)
        X = X.reshape((X.shape[0], X.shape[1], 2))  # เพิ่ม 1 มิติสำหรับ day_of_week

        building = house_data[0].get("house_no", "Unknown")
        model_path = f"saved_models/{building}_lstm_model.h5"

        if os.path.exists(model_path):
            model = load_model(model_path)
        else:
            model = Sequential([
                Input(shape=(time_step, 2)),  # ใช้ 2 ฟีเจอร์
                LSTM(50, return_sequences=True),
                LSTM(50, return_sequences=False),
                Dense(25),
                Dense(1)
            ])
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')

        if not os.path.exists(model_path):
            start_time = time.time()
            model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=1)
            end_time = time.time()
            model.save(model_path)
        else:
            start_time = time.time()
            end_time = time.time()

        rolling_input = X[-1].reshape(1, time_step, 2)
        rolling_predictions = []

        for _ in range(forecast_horizon):
            pred = model.predict(rolling_input)[0, 0]
            rolling_predictions.append(pred)

            new_day_of_week = (timestamps[-1].dayofweek + 1) % 7  # หมุนวันในสัปดาห์
            new_input = np.append(rolling_input[0, 1:], [[pred, new_day_of_week]], axis=0)
            rolling_input = new_input.reshape(1, time_step, 2)

        future_timestamps = pd.date_range(start=timestamps[-1], periods=forecast_horizon+1, freq='15T')[1:]
        predict_data = [{"value": float(val), "timestamp": ts.isoformat()} for val, ts in zip(rolling_predictions, future_timestamps)]

        return {
            "predict": predict_data
        }

    except Exception as e:
        return {"error": str(e)}
