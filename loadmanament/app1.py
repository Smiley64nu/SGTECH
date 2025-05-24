import numpy as np
from tensorflow.keras.models import load_model
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split

# 📌 โหลดโมเดลจากไฟล์ .h5
model = load_model(r"C:\Users\USER\Desktop\New folder (7)\loadmanament\saved_models\Unknown_cnn_lstm_model.h5")

# 📌 โหลดข้อมูล (สมมติว่ามี X และ y)
# หากมีข้อมูลอยู่แล้ว ให้ใช้ข้อมูลจริงแทน
X = np.load("X.npy")  # โหลดไฟล์ข้อมูลอินพุต (ถ้ามี)
y = np.load("y.npy")  # โหลดไฟล์ข้อมูลผลลัพธ์จริง (ถ้ามี)

# 📌 แบ่งข้อมูลเป็นชุด Train/Test (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 📌 ใช้โมเดลพยากรณ์ค่า
y_pred = model.predict(X_test)

# 📌 คำนวณค่า Error ต่างๆ
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, y_pred)
mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
accuracy = 100 - mape  # คำนวณความแม่นยำ

# 📌 แสดงผลลัพธ์
print("📊 Model Evaluation:")
print(f"MSE (Mean Squared Error): {mse:.6f}")
print(f"RMSE (Root Mean Squared Error): {rmse:.6f}")
print(f"MAE (Mean Absolute Error): {mae:.6f}")
print(f"MAPE (Mean Absolute Percentage Error): {mape:.2f}%")
print(f"Model Accuracy: {accuracy:.2f}%")

