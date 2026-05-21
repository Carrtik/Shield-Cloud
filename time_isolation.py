import time
import requests
import socketio

sio = socketio.Client()
isolation_times = []
isolation_received = None

@sio.on('account_isolated')
def on_isolated(data):
    global isolation_received
    isolation_received = time.time()

sio.connect('http://localhost:3005')
print("Connected to Risk Engine WebSocket")

for trial in range(10):
    isolation_received = None
    start = time.time()
    
    requests.post("http://localhost:3005/inject-attack",
                  json={"user_id": f"test-user-{trial}"})
    
    timeout = time.time() + 15
    while isolation_received is None and time.time() < timeout:
        time.sleep(0.01)
    
    if isolation_received:
        elapsed = isolation_received - start
        isolation_times.append(elapsed)
        print(f"Trial {trial+1}: {elapsed:.3f}s")
    else:
        print(f"Trial {trial+1}: TIMEOUT")

if isolation_times:
    print(f"\nMean:   {sum(isolation_times)/len(isolation_times):.3f}s")
    print(f"Min:    {min(isolation_times):.3f}s")
    print(f"Max:    {max(isolation_times):.3f}s")
    print(f"All under 8s: {all(t < 8 for t in isolation_times)}")
