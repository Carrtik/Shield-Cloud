"""
train_model.py
==============
Trains a supervised XGBoost binary classifier on the synthetic access-log
dataset produced by generate_dataset.py.

Why XGBoost instead of IsolationForest?
  - We now have LABELLED data (label_anomaly column) so supervised learning
    is vastly more accurate than unsupervised anomaly detection.
  - XGBoost handles class imbalance natively via scale_pos_weight.
  - It gives us a calibrated probability score (0-1), not just -1/+1.
  - It natively handles mixed numeric + one-hot features with no scaling needed.

Pipeline
--------
1. Load CSV  →  2. Encode categoricals  →  3. SMOTE over-sample minority class
4. Train XGBoost  →  5. Evaluate  →  6. Save model + feature-list to disk
"""

import json
import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, roc_auc_score,
    confusion_matrix, ConfusionMatrixDisplay
)
from xgboost import XGBClassifier

# ── 1. Load ───────────────────────────────────────────────────────────────────
print("Loading dataset...")
df = pd.read_csv("access_logs.csv")
print(f"  Rows: {len(df)}  |  Attacks: {df['label_anomaly'].sum()}")

# ── 2. Feature Engineering ────────────────────────────────────────────────────
# One-hot encode action_type  (login, upload, download, list, delete, share)
df = pd.get_dummies(df, columns=['action_type'], prefix='act')

# Ensure all action columns exist even if a category was not in data split
EXPECTED_ACTION_COLS = [
    'act_login', 'act_upload', 'act_download',
    'act_list',  'act_delete', 'act_share'
]
for col in EXPECTED_ACTION_COLS:
    if col not in df.columns:
        df[col] = 0

# Byte-count features can be huge — log-transform to reduce skew
df['log_bytes']  = np.log1p(df['bytes_transferred_last_1h'])
df['log_fsize']  = np.log1p(df['file_size_bytes'])

FEATURE_COLS = [
    # Temporal
    'hour_of_day', 'is_weekend',
    # Location / identity
    'ip_location_mismatch', 'geo_velocity_kmh',
    'unique_ips_last_24h',
    # Activity volume
    'download_count_last_1h', 'upload_count_last_1h',
    'log_bytes', 'log_fsize',
    # Auth signals
    'failed_logins_last_1h', 'failed_logins_last_24h',
    # Session
    'session_duration_min', 'time_since_last_login_h',
    # File risk
    'file_type_risk_score',
    # Network
    'request_rate_per_min', 'tor_exit_node',
    'vpn_detected', 'user_agent_anomaly',
    # Action type (one-hot)
    *EXPECTED_ACTION_COLS,
]

X = df[FEATURE_COLS]
y = df['label_anomaly']

# ── 3. Train / Test Split ─────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f"\nTrain set: {len(X_train)} rows | Test set: {len(X_test)} rows")

# ── 4. SMOTE — Oversample the minority (attack) class in training data only ───
print("Applying SMOTE to balance training set...")
sm = SMOTE(random_state=42, k_neighbors=5)
X_train_bal, y_train_bal = sm.fit_resample(X_train, y_train)
print(f"  After SMOTE  — Normal: {(y_train_bal==0).sum()}  Attack: {(y_train_bal==1).sum()}")

# ── 5. Train XGBoost ──────────────────────────────────────────────────────────
# scale_pos_weight compensates if we skip SMOTE; here left at 1 since SMOTE balanced.
model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    use_label_encoder=False,
    eval_metric='logloss',
    random_state=42,
    n_jobs=-1,
)
print("\nTraining XGBoost (300 trees)...")
model.fit(
    X_train_bal, y_train_bal,
    eval_set=[(X_test, y_test)],
    verbose=50,
)

# ── 6. Evaluate ───────────────────────────────────────────────────────────────
y_pred  = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n── Classification Report ─────────────────────────────────────")
print(classification_report(y_test, y_pred, target_names=['Normal', 'Attack']))
print(f"ROC-AUC Score : {roc_auc_score(y_test, y_proba):.4f}")

cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix:")
print(cm)
print(f"  True Negatives  (Correct Normal) : {cm[0][0]}")
print(f"  False Positives (False Alarms   ): {cm[0][1]}")
print(f"  False Negatives (Missed Attacks ): {cm[1][0]}")
print(f"  True Positives  (Caught Attacks ): {cm[1][1]}")

# ── 7. Feature Importance ─────────────────────────────────────────────────────
importances = pd.Series(model.feature_importances_, index=FEATURE_COLS)
top10 = importances.nlargest(10)
print("\n── Top-10 Feature Importances ──────────────────────────────")
for feat, imp in top10.items():
    bar = "█" * int(imp * 200)
    print(f"  {feat:<35} {imp:.4f}  {bar}")

# ── 8. Save Model + Feature List ─────────────────────────────────────────────
joblib.dump(model, "xgb_anomaly_model.pkl")

# Save feature list so inference code never has column-mismatch bugs
model_meta = {
    "feature_cols": FEATURE_COLS,
    "expected_action_cols": EXPECTED_ACTION_COLS,
    "version": "2.0-xgboost",
    "roc_auc": round(float(roc_auc_score(y_test, y_proba)), 4),
}
with open("model_meta.json", "w") as f:
    json.dump(model_meta, f, indent=2)

print("Success: Model saved  ->  xgb_anomaly_model.pkl")
print("Success: Meta  saved  ->  model_meta.json")
print(f"  ROC-AUC: {model_meta['roc_auc']}")
