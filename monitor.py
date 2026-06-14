from kubernetes import client, config
from sklearn.ensemble import IsolationForest
import subprocess
import re
import time
from datetime import datetime

# Load kubernetes config
config.load_kube_config()
v1 = client.CoreV1Api()

# Store history for AI
history = {}

def get_real_metrics():
    """Get REAL CPU and Memory from Docker stats"""
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", 
         "{{.Name}},{{.CPUPerc}},{{.MemPerc}}"],
        capture_output=True, text=True
    )
    
    metrics = {}
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split(',')
        if len(parts) < 3:
            continue
        
        name = parts[0]
        cpu_str = parts[1].replace('%', '').strip()
        mem_str = parts[2].replace('%', '').strip()
        
        try:
            cpu = float(cpu_str)
            mem = float(mem_str)
        except:
            continue

        # Match our pods
        if 'web-app' in name and 'k8s_web-app' in name:
            pod_key = 'web-app'
            if pod_key not in metrics:
                metrics[pod_key] = {'cpu': cpu, 'mem': mem}
            else:
                # Average multiple replicas
                metrics[pod_key]['cpu'] = (metrics[pod_key]['cpu'] + cpu) / 2
                metrics[pod_key]['mem'] = (metrics[pod_key]['mem'] + mem) / 2

        elif 'k8s_database' in name:
            metrics['database'] = {'cpu': cpu, 'mem': mem}

        elif 'k8s_backend' in name:
            metrics['backend'] = {'cpu': cpu, 'mem': mem}

    return metrics

def detect_anomaly(pod_name, cpu, mem):
    if pod_name not in history:
        history[pod_name] = []
    history[pod_name].append([cpu, mem])
    if len(history[pod_name]) > 50:
        history[pod_name].pop(0)
    if len(history[pod_name]) < 10:
        return False
    model = IsolationForest(contamination=0.15, random_state=42)
    model.fit(history[pod_name])
    pred = model.predict([[cpu, mem]])
    return pred[0] == -1

def get_insight(pod_name, cpu, mem, is_anomaly):
    if is_anomaly:
        if cpu > 5:
            return f"CRITICAL: {pod_name} CPU spike detected ({cpu:.2f}%)!", "critical"
        if mem > 20:
            return f"WARNING: {pod_name} memory high ({mem:.2f}%)!", "warning"
        return f"ANOMALY: {pod_name} unusual behavior. CPU:{cpu:.2f}% MEM:{mem:.2f}%", "warning"
    if cpu > 3:
        return f"NOTICE: {pod_name} CPU rising ({cpu:.2f}%). Keep watching.", "notice"
    return f"HEALTHY: {pod_name} running normally. CPU:{cpu:.2f}% MEM:{mem:.2f}%", "healthy"

def check_dependency(pod_data):
    deps = []
    pod_names = list(pod_data.keys())
    for i in range(len(pod_names)):
        for j in range(i+1, len(pod_names)):
            p1, p2 = pod_names[i], pod_names[j]
            cpu1 = pod_data[p1]["cpu"]
            cpu2 = pod_data[p2]["cpu"]
            if cpu1 > 2 and cpu2 > 2:
                deps.append(f"DEPENDENCY: {p1} and {p2} both under stress!")
            elif cpu1 > 3:
                deps.append(f"IMPACT: High load on {p1} may affect {p2}")
    return deps

def run_monitor():
    print("\n" + "="*60)
    print("   ABB AI-DRIVEN POD INTELLIGENCE SYSTEM")
    print("   Using REAL Docker metrics!")
    print("="*60)

    cycle = 0
    while True:
        cycle += 1
        print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Scan #{cycle}")
        print("-"*60)

        try:
            metrics = get_real_metrics()

            if not metrics:
                print("⚠️ No pod metrics found — retrying...")
                time.sleep(10)
                continue

            pod_data = {}
            for pod_name, m in metrics.items():
                cpu = round(m['cpu'], 3)
                mem = round(m['mem'], 3)
                is_anomaly = detect_anomaly(pod_name, cpu, mem)
                insight, level = get_insight(pod_name, cpu, mem, is_anomaly)

                pod_data[pod_name] = {
                    "cpu": cpu,
                    "mem": mem,
                    "anomaly": is_anomaly,
                    "level": level
                }

                if level == "critical":
                    indicator = "🔴"
                elif level == "warning":
                    indicator = "🟡"
                elif level == "notice":
                    indicator = "🟠"
                else:
                    indicator = "🟢"

                print(f"{indicator} {insight}")

            deps = check_dependency(pod_data)
            if deps:
                print("\n🔗 DEPENDENCY ANALYSIS:")
                for d in deps:
                    print(f"   ↳ {d}")

            total = len(pod_data)
            anomalies = sum(1 for p in pod_data.values() if p["anomaly"])
            healthy = total - anomalies
            print(f"\n📊 SUMMARY: {healthy}/{total} healthy | {anomalies} anomalies detected")
            print(f"✅ Data source: REAL Docker metrics")

        except Exception as e:
            print(f"Error: {e}")

        print(f"\n⏳ Next scan in 15 seconds...")
        time.sleep(15)

if __name__ == "__main__":
    run_monitor()