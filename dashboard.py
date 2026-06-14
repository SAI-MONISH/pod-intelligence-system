from flask import Flask, jsonify, render_template_string
from kubernetes import client, config
from sklearn.ensemble import IsolationForest
import subprocess
import time
import threading
from datetime import datetime

app = Flask(__name__)

config.load_kube_config()
v1 = client.CoreV1Api()

pod_data = {}
alerts = []
history = {}
scan_count = 0

def get_real_metrics():
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
        try:
            cpu = float(parts[1].replace('%', '').strip())
            mem = float(parts[2].replace('%', '').strip())
        except:
            continue
        if 'k8s_web-app' in name:
            if 'web-app' not in metrics:
                metrics['web-app'] = {'cpu': cpu, 'mem': mem}
            else:
                metrics['web-app']['cpu'] = (metrics['web-app']['cpu'] + cpu) / 2
                metrics['web-app']['mem'] = (metrics['web-app']['mem'] + mem) / 2
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

def background_monitor():
    global pod_data, alerts, scan_count
    while True:
        try:
            scan_count += 1
            metrics = get_real_metrics()
            new_data = {}
            for pod_name, m in metrics.items():
                cpu = round(m['cpu'], 3)
                mem = round(m['mem'], 3)
                is_anomaly = detect_anomaly(pod_name, cpu, mem)
                if is_anomaly or cpu > 3:
                    alert_msg = {
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "pod": pod_name,
                        "cpu": cpu,
                        "mem": mem,
                        "msg": f"CPU spike detected on {pod_name} ({cpu}%)" if cpu > 3 else f"Anomaly detected on {pod_name}"
                    }
                    alerts.insert(0, alert_msg)
                    if len(alerts) > 10:
                        alerts.pop()
                new_data[pod_name] = {
                    "cpu": cpu,
                    "mem": mem,
                    "anomaly": is_anomaly,
                    "status": "critical" if cpu > 5 or mem > 20 else "warning" if cpu > 2 else "healthy"
                }
            pod_data = new_data
        except Exception as e:
            print(f"Monitor error: {e}")
        time.sleep(10)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>ABB Pod Intelligence System</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a0f1e; color:#fff; font-family:Arial,sans-serif; }
.header { background:#0d1f3c; padding:20px 30px; border-bottom:2px solid #00b4d8; display:flex; justify-content:space-between; align-items:center; }
.header h1 { color:#00b4d8; font-size:22px; }
.header .subtitle { color:#8899aa; font-size:13px; margin-top:4px; }
.live-badge { background:#00b4d8; color:#000; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:bold; }
.real-badge { background:#2dc653; color:#000; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:bold; margin-left:8px; }
.container { padding:20px 30px; }
.stats-row { display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin-bottom:20px; }
.stat-card { background:#0d1f3c; border-radius:10px; padding:20px; text-align:center; border:1px solid #1a3a5c; }
.stat-card .num { font-size:36px; font-weight:bold; color:#00b4d8; }
.stat-card .label { font-size:12px; color:#8899aa; margin-top:5px; }
.grid { display:grid; grid-template-columns:2fr 1fr; gap:20px; }
.card { background:#0d1f3c; border-radius:10px; padding:20px; border:1px solid #1a3a5c; }
.card h3 { color:#00b4d8; margin-bottom:15px; font-size:15px; }
.pod-row { display:flex; align-items:center; padding:12px; border-radius:8px; margin-bottom:8px; background:#0a1628; gap:10px; }
.pod-name { font-size:13px; color:#cdd; width:120px; flex-shrink:0; }
.bar-section { flex:1; }
.bar-label { font-size:10px; color:#8899aa; margin-bottom:3px; }
.bar-bg { background:#1a3a5c; border-radius:4px; height:8px; width:100%; }
.bar { height:8px; border-radius:4px; transition:width 0.8s; }
.cpu-bar { background:linear-gradient(90deg,#00b4d8,#0077b6); }
.mem-bar { background:linear-gradient(90deg,#48cae4,#023e8a); }
.pct { font-size:12px; width:45px; text-align:right; flex-shrink:0; }
.dot { width:12px; height:12px; border-radius:50%; flex-shrink:0; }
.healthy { background:#2dc653; }
.warning { background:#f4a261; }
.critical { background:#e63946; animation:pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.alert-row { padding:10px; border-radius:8px; margin-bottom:8px; background:#0a1628; border-left:3px solid #e63946; }
.alert-time { font-size:10px; color:#8899aa; }
.alert-msg { font-size:12px; color:#ff6b6b; margin-top:3px; }
.alert-detail { font-size:11px; color:#8899aa; margin-top:2px; }
.dep-card { background:#0d1f3c; border-radius:10px; padding:20px; border:1px solid #1a3a5c; margin-top:20px; }
.dep-card h3 { color:#00b4d8; margin-bottom:15px; font-size:15px; }
.dep-item { padding:10px; background:#0a1628; border-radius:8px; margin-bottom:8px; font-size:12px; color:#90e0ef; border-left:3px solid #00b4d8; }
.real-tag { background:#1a3a5c; color:#2dc653; font-size:10px; padding:2px 8px; border-radius:10px; margin-left:8px; }
.footer { text-align:center; padding:15px; color:#8899aa; font-size:12px; border-top:1px solid #1a3a5c; margin-top:20px; }
</style>
<script>
async function refresh() {
    try {
        const res = await fetch('/api/data');
        const data = await res.json();
        document.getElementById('total').textContent = data.total;
        document.getElementById('healthy').textContent = data.healthy;
        document.getElementById('anomalies').textContent = data.anomalies;
        document.getElementById('scans').textContent = data.scan_count;
        document.getElementById('scantime').textContent = 'Last scan: ' + data.last_scan;

        let podHtml = '';
        for (const [name, info] of Object.entries(data.pods)) {
            const cpuWidth = Math.min(info.cpu * 10, 100);
            const memWidth = Math.min(info.mem * 5, 100);
            podHtml += `
            <div class="pod-row">
                <div class="dot ${info.status}"></div>
                <div class="pod-name">${name}</div>
                <div class="bar-section">
                    <div class="bar-label">CPU: ${info.cpu}%</div>
                    <div class="bar-bg"><div class="bar cpu-bar" style="width:${cpuWidth}%"></div></div>
                </div>
                <div class="bar-section">
                    <div class="bar-label">MEM: ${info.mem}%</div>
                    <div class="bar-bg"><div class="bar mem-bar" style="width:${memWidth}%"></div></div>
                </div>
            </div>`;
        }
        document.getElementById('pods').innerHTML = podHtml || '<p style="color:#8899aa">Loading real metrics...</p>';

        let alertHtml = '';
        if (data.alerts.length === 0) {
            alertHtml = '<p style="color:#2dc653;font-size:13px;">✅ All systems normal</p>';
        }
        for (const a of data.alerts) {
            alertHtml += `
            <div class="alert-row">
                <div class="alert-time">⏰ ${a.time}</div>
                <div class="alert-msg">🔴 ${a.msg}</div>
                <div class="alert-detail">CPU: ${a.cpu}% | MEM: ${a.mem}%</div>
            </div>`;
        }
        document.getElementById('alerts').innerHTML = alertHtml;

        let depHtml = '';
        for (const d of data.dependencies) {
            depHtml += `<div class="dep-item">🔗 ${d}</div>`;
        }
        document.getElementById('deps').innerHTML = depHtml || '<p style="color:#8899aa;font-size:13px;">Analyzing pod relationships...</p>';
    } catch(e) {
        console.log('Refresh error:', e);
    }
}
setInterval(refresh, 5000);
window.onload = refresh;
</script>
</head>
<body>
<div class="header">
    <div>
        <h1>🤖 ABB Pod Intelligence System</h1>
        <div class="subtitle">AI-Driven Container Observability & Anomaly Detection</div>
    </div>
    <div style="text-align:right;">
        <span class="live-badge">🟢 LIVE</span>
        <span class="real-badge">✅ REAL DATA</span>
        <div style="color:#8899aa;font-size:11px;margin-top:5px;" id="scantime"></div>
    </div>
</div>
<div class="container">
    <div class="stats-row">
        <div class="stat-card">
            <div class="num" id="total">-</div>
            <div class="label">Total Pods</div>
        </div>
        <div class="stat-card">
            <div class="num" style="color:#2dc653" id="healthy">-</div>
            <div class="label">Healthy</div>
        </div>
        <div class="stat-card">
            <div class="num" style="color:#e63946" id="anomalies">-</div>
            <div class="label">Anomalies</div>
        </div>
        <div class="stat-card">
            <div class="num" style="color:#f4a261" id="scans">-</div>
            <div class="label">Total Scans</div>
        </div>
    </div>
    <div class="grid">
        <div class="card">
            <h3>📊 Live Pod Metrics <span class="real-tag">REAL DATA</span></h3>
            <div id="pods">Loading...</div>
        </div>
        <div class="card">
            <h3>🚨 AI Alerts</h3>
            <div id="alerts">Loading...</div>
        </div>
    </div>
    <div class="dep-card">
        <h3>🔗 Dependency Analysis — Pod Relationships</h3>
        <div id="deps">Loading...</div>
    </div>
</div>
<div class="footer">
    ABB Accelerator Contest — AI-Driven Container Intelligence | 
    Python + Kubernetes + Docker + Machine Learning | 
    Data Source: Real Docker Metrics ✅
</div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/data')
def api_data():
    total = len(pod_data)
    healthy = sum(1 for p in pod_data.values() if p["status"] == "healthy")
    anomalies = sum(1 for p in pod_data.values() if p["anomaly"])
    deps = []
    pod_names = list(pod_data.keys())
    for i in range(len(pod_names)):
        for j in range(i+1, len(pod_names)):
            p1, p2 = pod_names[i], pod_names[j]
            if pod_data[p1]["cpu"] > 2 and pod_data[p2]["cpu"] > 2:
                deps.append(f"{p1} and {p2} both under stress simultaneously!")
            elif pod_data[p1]["cpu"] > 3:
                deps.append(f"High load on {p1} may be impacting {p2}")
    return jsonify({
        "total": total,
        "healthy": healthy,
        "anomalies": anomalies,
        "scan_count": scan_count,
        "last_scan": datetime.now().strftime("%H:%M:%S"),
        "pods": pod_data,
        "alerts": alerts,
        "dependencies": deps
    })

if __name__ == '__main__':
    t = threading.Thread(target=background_monitor, daemon=True)
    t.start()
    print("\n" + "="*50)
    print("  ABB DASHBOARD — REAL DATA MODE")
    print("  Open browser: http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=False, port=5000)