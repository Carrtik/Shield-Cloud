import os
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dropout, RepeatVector, TimeDistributed, Dense
import numpy as np

def build_model(num_features=10, sequence_length=20):
    model = Sequential([
        LSTM(64, input_shape=(sequence_length, num_features), return_sequences=True),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        RepeatVector(sequence_length),
        LSTM(32, return_sequences=True),
        Dropout(0.2),
        LSTM(64, return_sequences=True),
        TimeDistributed(Dense(num_features))
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def train_model(model, X_train, epochs=50, batch_size=64, validation_split=0.1):
    history = model.fit(
        X_train, X_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=validation_split,
        shuffle=True
    )
    # Calculate threshold based on training data reconstruction error
    X_train_pred = model.predict(X_train)
    train_mae_loss = np.mean(np.abs(X_train_pred - X_train), axis=1)
    threshold = np.max(train_mae_loss) * 1.5 # Example heuristic threshold
    return history, threshold

def save_model(model, threshold, filepath="saved_model/anomaly_lstm.h5"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    model.save(filepath)
    with open("saved_model/threshold.txt", "w") as f:
        f.write(str(threshold))
    print(f"Model saved to {filepath} with threshold {threshold}")
