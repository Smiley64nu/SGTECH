import os
import numpy as np
import pandas as pd
import time
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Input, Conv1D, MaxPooling1D, Flatten, Dropout
from keras.optimizers import Adam
from keras import backend as K

def predict_cnn_lstm(house_data, params):
    try:
        epochs = int(params.get("epochs", 100))
        batch_size = int(params.get("batch_size", 32))
        time_step = int(params.get("time_step", 100))
        forecast_horizon = int(params.get("forecast_horizon", 48))

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
            y.append(dataset[i + time_step, 0])  

        X, y = np.array(X), np.array(y)
        X_cnn = X.reshape((X.shape[0], time_step, 2))  # ✅ แก้ให้สอดคล้องกับ Conv1D

        building = house_data[0].get("house_no", "Unknown")
        model_path = f"saved_models/{building}_cnn_lstm_model.h5"

        if os.path.exists(model_path):
            model = load_model(model_path)
        else:
            K.clear_session()
            model = Sequential([
                Conv1D(64, 3, activation='relu', input_shape=(time_step, 2)),  # ✅ แก้ input_shape
                MaxPooling1D(2),  # ✅ เปลี่ยน pool_size เป็น 2
                LSTM(50, return_sequences=False),  # ✅ เปลี่ยน return_sequences=False
                Flatten(),
                Dense(25, activation='relu'),
                Dense(1)
            ])
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mean_squared_error')

        if not os.path.exists(model_path):
            model.fit(X_cnn, y, epochs=epochs, batch_size=batch_size, verbose=1)
            model.save(model_path)

        rolling_input = X_cnn[-1].reshape(1, time_step, 2)
        rolling_predictions = []

        for _ in range(forecast_horizon):
            pred = model.predict(rolling_input)[0, 0]
            rolling_predictions.append(pred)

            new_day_of_week = (timestamps[-1].dayofweek + 1) % 7
            new_input = np.append(rolling_input[0, 1:], [[pred, new_day_of_week]], axis=0)
            rolling_input = new_input.reshape(1, time_step, 2)

        future_timestamps = pd.date_range(start=timestamps[-1], periods=forecast_horizon+1, freq='15T')[1:]
        predict_data = [{"value": float(val), "timestamp": ts.isoformat()} for val, ts in zip(rolling_predictions, future_timestamps)]

        return {"predict": predict_data}

    except Exception as e:
        return {"error": str(e)}
