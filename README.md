# Pod Intelligence System
### AI-Driven Real-time Kubernetes Container Monitoring

## About
An AI-powered monitoring system that watches Kubernetes 
pods in real time, detects anomalies using Machine Learning,
maps dependencies between pods, and shows everything on 
a live dashboard.

Built for ABB Accelerator 2026 — Theme 2

## Features
- Real-time pod monitoring using Docker Stats API
- Anomaly detection using Isolation Forest ML
- Pod dependency mapping
- Live Flask dashboard at localhost:5000
- Load generator for real CPU spike simulation
- Auto-refreshing alerts with timestamps

## Tech Stack
- Python
- Kubernetes (Docker Desktop)
- Docker
- Flask
- scikit-learn (Isolation Forest)
- pandas, numpy

## Project Structure
pod-intelligence-system/

├── app.py              # Real Python web server (runs in pods)

├── Dockerfile          # Docker image recipe

├── pods.yaml           # Kubernetes deployment config

├── monitor.py          # AI monitoring + anomaly detection

├── dashboard.py        # Flask web dashboard

└── load_generator.py   # Real CPU load generator

## ⚙️ How to Run

### Prerequisites
- Docker Desktop with Kubernetes enabled
- Python 3.x installed

### Steps
1. Build Docker image:
   docker build -t abb-app:latest .

2. Deploy pods:
   kubectl apply -f pods.yaml

3. Expose web-app:
   kubectl expose deployment web-app --type=NodePort --port=8080

4. Start load generator:
   python load_generator.py

5. Start AI monitor:
   python monitor.py

6. Start dashboard:
   python dashboard.py

7. Open browser:
   http://localhost:5000
