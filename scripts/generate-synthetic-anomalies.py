import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_data(num_samples, anomaly_ratio=0.05):
    data = []
    current_time = datetime.now()

    for i in range(num_samples):
        is_anomaly = random.random() < anomaly_ratio
        
        # Features:
        # hour_of_day, day_of_week, ip_change, geo_change, device_change,
        # login_failures_last_1h, files_accessed_last_1h, bytes_downloaded_last_1h,
        # api_calls_last_5min

        hour = current_time.hour
        day = current_time.weekday()
        
        if not is_anomaly:
            # Normal behavior
            ip_change = 0
            geo_change = 0
            device_change = 0
            login_failures = random.choice([0, 0, 0, 1])
            files_accessed = random.randint(1, 10)
            bytes_downloaded = random.randint(1000, 5000000) # 1KB to 5MB
            api_calls = random.randint(1, 20)
        else:
            # Anomaly behavior (e.g., rapid downloads, ip change, lots of failures)
            ip_change = 1
            geo_change = random.choice([0, 1])
            device_change = random.choice([0, 1])
            login_failures = random.randint(3, 10)
            files_accessed = random.randint(50, 200)
            bytes_downloaded = random.randint(10000000, 1000000000) # 10MB to 1GB
            api_calls = random.randint(100, 500)

        data.append([
            hour, day, ip_change, geo_change, device_change,
            login_failures, files_accessed, bytes_downloaded, api_calls, is_anomaly
        ])
        
        current_time += timedelta(minutes=random.randint(1, 60))

    df = pd.DataFrame(data, columns=[
        'hour_of_day', 'day_of_week', 'ip_change', 'geo_change', 'device_change',
        'login_failures_last_1h', 'files_accessed_last_1h', 'bytes_downloaded_last_1h',
        'api_calls_last_5min', 'is_anomaly'
    ])
    df.to_csv('synthetic_anomalies.csv', index=False)
    print(f"Generated {num_samples} samples. Data saved to synthetic_anomalies.csv")

if __name__ == "__main__":
    generate_data(10000)
