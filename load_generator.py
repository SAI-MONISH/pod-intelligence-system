import urllib.request
import threading
import time

PORT = 8080

def get_port():
    import subprocess
    result = subprocess.run(
        ["kubectl", "get", "service", "web-app", "--no-headers"],
        capture_output=True, text=True
    )
    try:
        port = result.stdout.split(":")[1].split("/")[0]
        return int(port)
    except:
        return 30000

def hit_service(port):
    while True:
        try:
            urllib.request.urlopen(
                f"http://localhost:{port}", timeout=2
            )
        except:
            pass
        time.sleep(0.05)

print("🔥 ABB Load Generator Starting...")
port = get_port()
print(f"✅ Targeting port: {port}")
print("📊 Sending real requests to create CPU load...")
print("⚠️ Press Ctrl+C to stop\n")

threads = []
for i in range(10):
    t = threading.Thread(target=hit_service, args=(port,), daemon=True)
    t.start()
    threads.append(t)
    print(f"🚀 Thread {i+1} started...")

try:
    count = 0
    while True:
        time.sleep(5)
        count += 5
        print(f"⏰ Running {count}s — sending real requests to pods!")
except KeyboardInterrupt:
    print("\n✅ Load generator stopped!")