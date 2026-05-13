@echo off
setlocal enabledelayedexpansion
set PYTHONIOENCODING=utf-8

echo =========================================================
echo   ShieldCloud — Generating Data and Training Anomaly ML 
echo =========================================================

cd anomaly-service
echo [1/3] Generating 10,000 synthetic logs...
python generate_dataset.py
if %ERRORLEVEL% neq 0 (
    echo Error during data generation!
    exit /b %ERRORLEVEL%
)

echo [2/3] Training XGBoost model using SMOTE...
python train_model.py
if %ERRORLEVEL% neq 0 (
    echo Error during model training!
    exit /b %ERRORLEVEL%
)

echo [3/3] Training completed successfully. 
cd ..
exit /b 0
