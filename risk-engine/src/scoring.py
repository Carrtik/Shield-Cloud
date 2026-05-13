# Dictionary acting as a mock DB for user EMAs
user_ema_db = {}
ALPHA = 0.1

def evaluate_risk(user_id, anomaly_score, login_fail, geo_change, api_spike, device_change):
    # Risk Score Formula
    composite_risk = (
        0.45 * anomaly_score +
        0.25 * login_fail +
        0.15 * geo_change +
        0.10 * api_spike +
        0.05 * device_change
    )
    
    # Adaptive Threshold (EMA)
    history = user_ema_db.get(user_id, {"ema": 0.2, "std_dev": 0.05})
    
    # Update EMA
    new_ema = (ALPHA * composite_risk) + ((1 - ALPHA) * history["ema"])
    
    # Using a simple moving standard deviation is hard without sliding window array,
    # so we mock updating standard deviation simply.
    new_std_dev = max(0.01, abs(composite_risk - new_ema) * 0.5 + history["std_dev"] * 0.5)
    
    user_ema_db[user_id] = {"ema": new_ema, "std_dev": new_std_dev}
    
    adaptive_threshold = new_ema + 2 * new_std_dev
    
    # Let's consider standard tiers as per the spec
    if composite_risk < 0.3:
        level = "LOW"
    elif 0.3 <= composite_risk < 0.6:
        level = "MEDIUM"
    elif 0.6 <= composite_risk < 0.8:
        level = "HIGH"
    else:
        level = "CRITICAL"
        
    return composite_risk, level
