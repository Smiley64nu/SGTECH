from tensorflow.keras.models import load_model
from tensorflow.keras.utils import plot_model

# โหลดโมเดล
model = load_model(r"C:\Users\USER\Desktop\loadmanament\saved_models\Unknown_lstm_model.h5")

# สร้างภาพ plot
plot_model(
    model,
    to_file='model_structurelstm.png',  # ไฟล์ output
    show_shapes=True,               # แสดงขนาดของ tensor ในแต่ละ layer
    show_layer_names=True           # แสดงชื่อ layer
)
