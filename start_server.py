import http.server
import socketserver
import threading
import time
import os

PORT = 8000
DIRECTORY = os.path.join(os.path.dirname(__file__), "test_sites")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving test sites at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    # Ensure test_sites directory exists and files are there (omitted creation logic for brevity, assume files exist)
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer stopped.")