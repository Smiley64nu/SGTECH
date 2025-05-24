import os
import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Input
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split

def predict_lstm(house_data, params):
    try:
        epochs = int(params.get("epochs", 100))
        batch_size = int(params.get("batch_size", 256))
        time_step = int(params.get("time_step", 96))  # ✅ ปรับเป็น 1 วัน = 96 ค่า
        forecast_horizon = int(params.get("forecast_horizon", 96))

        if not house_data:
            raise ValueError("Invalid or empty house data provided")

        # ✅ สร้าง DataFrame
        df = pd.DataFrame(house_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df['raw_p_h'] = df['raw_p_h'].replace([np.inf, -np.inf], np.nan).ffill().bfill()

        # ✅ เพิ่มฟีเจอร์วันและชั่วโมงของวัน
        df['day_of_week'] = df.index.dayofweek  # Monday=0, Sunday=6
        df['hour_of_day'] = df.index.hour  # 0-23 ชั่วโมง

        dataset = df[['raw_p_h', 'day_of_week', 'hour_of_day']].values
        timestamps = df.index.tolist()

        # ✅ สร้าง Input และ Output
        X, y = [], []
        for i in range(len(dataset) - time_step - 1):
            X.append(dataset[i:(i + time_step)])
            y.append(dataset[i + time_step, 0])  

        X, y = np.array(X), np.array(y)
        X = X.reshape((X.shape[0], X.shape[1], 3))  # ✅ ใช้ 3 ฟีเจอร์ (RAW_P_H, day_of_week, hour_of_day)

        #  แบ่งข้อมูล Train/Test (80/20)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False, random_state=42)

        print(f"🔍 Train Data: {X_train.shape}, {y_train.shape}")
        print(f"🔍 Test Data: {X_test.shape}, {y_test.shape}")

        # ✅ โหลดโมเดล
        building = house_data[0].get("house_no", "Unknown")
        model_path = f"saved_models/{building}_lstm_model.h5"

        if os.path.exists(model_path):
            model = load_model(model_path)
        else:
            model = Sequential([
                Input(shape=(time_step, 3)),  
                LSTM(50, return_sequences=True),
                LSTM(50, return_sequences=False),
                Dense(25),
                Dense(1)
            ])
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error', metrics=['mae'])

        # ✅ ใช้ EarlyStopping เพื่อลด Overfitting
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

        # ✅ ฝึกโมเดลเฉพาะ Train Set
        if not os.path.exists(model_path):
            history = model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_data=(X_test, y_test),  # ✅ เพิ่ม Validation Set
                callbacks=[early_stopping],  # ✅ เพิ่ม EarlyStopping
                verbose=1
            )
            model.save(model_path)

            # ✅ วาดกราฟ Training & Validation Loss
            plt.plot(history.history['loss'], label='Train Loss')
            plt.plot(history.history['val_loss'], label='Validation Loss')
            plt.xlabel('Epochs')
            plt.ylabel('Loss')
            plt.legend()
            plt.title('Training vs Validation Loss')
            plt.show()

        # ✅ ทดสอบโมเดลด้วย Test Set
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)

        print(f"📊 Model Test MSE: {mse}")
        print(f"📊 Model Test RMSE: {rmse}")
        print(f"📊 Model Test MAE: {mae}")

        # ✅ ใช้ Rolling Prediction
        rolling_input = X_test[-1].reshape(1, time_step, 3)
        rolling_predictions = []

        last_timestamp = timestamps[-1]  #  ดึง timestamp สุดท้ายของข้อมูลจริง
        future_timestamps = pd.date_range(start=last_timestamp, periods=forecast_horizon+1, freq='15T')[1:]  #  สร้าง timestamps อนาคต

        for i, ts in enumerate(future_timestamps):
            pred = model.predict(rolling_input)[0, 0]
            rolling_predictions.append(pred)

            #  คำนวณ `day_of_week` และ `hour_of_day` จาก `timestamp`
            new_day_of_week = ts.dayofweek
            new_hour_of_day = ts.hour

            #  สร้างข้อมูลใหม่สำหรับการพยากรณ์ต่อ
            new_input = np.append(rolling_input[0, 1:], [[pred, new_day_of_week, new_hour_of_day]], axis=0)
            rolling_input = new_input.reshape(1, time_step, 3)

        #  บันทึกค่าพยากรณ์
        predict_data = [{"value": float(val), "timestamp": ts.isoformat()} for val, ts in zip(rolling_predictions, future_timestamps)]

        return {
            "train_size": len(X_train),
            "test_size": len(X_test),
            "mse": mse,
            "rmse": rmse,
            "mae": mae,
            "predict": predict_data
        }

    except Exception as e:
        return {"error": str(e)}
