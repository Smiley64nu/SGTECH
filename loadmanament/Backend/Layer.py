from tensorflow.keras.utils import plot_model
from keras.models import load_model
model = load_model(r"saved_models\Unknown_cnn_lstm_model.h5")

plot_model(model, to_file='modelcnnlsm.png', show_shapes=False, rankdir="LR")