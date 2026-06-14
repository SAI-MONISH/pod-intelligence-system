from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import math
import random

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Real computation — uses actual CPU!
        result = sum(math.sqrt(i) * math.sin(i) for i in range(20000))
        
        response = f"""
        <html>
        <head><title>ABB Web Service</title></head>
        <body style="font-family:Arial; background:#0a0f1e; color:white; padding:20px;">
            <h2 style="color:#00b4d8;">ABB Pod Service</h2>
            <p>Status: Running</p>
            <p>Computation Result: {result:.4f}</p>
            <p>Time: {time.strftime('%H:%M:%S')}</p>
            <p>Pod is healthy and processing requests!</p>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        pass  # Silence logs

if __name__ == '__main__':
    print("ABB Pod Service starting on port 8080...")
    server = HTTPServer(('0.0.0.0', 8080), Handler)
    server.serve_forever()