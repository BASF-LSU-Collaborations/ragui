#!/usr/bin/env python3
"""
Simple HTTP server for serving files from the root directory (/).
Saves the port number to a file for Streamlit to read.
"""
import os
import sys
import socket
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Configuration
DEFAULT_PORT = 8069
MAX_PORT_ATTEMPTS = 10
ROOT_DIR = "/"
PORT_FILE = os.path.expanduser("~/file_server_port.txt")

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port, max_attempts):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    return None

def save_port(port):
    """Save the port number to a file for Streamlit to read"""
    with open(PORT_FILE, 'w') as f:
        f.write(str(port))
    print(f"Port {port} saved to {PORT_FILE}")

def run_server():
    """Run the HTTP server with port fallback"""
    port = find_available_port(DEFAULT_PORT, MAX_PORT_ATTEMPTS)
    
    if not port:
        print(f"❌ No available ports found in range {DEFAULT_PORT}-{DEFAULT_PORT + MAX_PORT_ATTEMPTS - 1}")
        sys.exit(1)
    
    # Save the port to a file
    save_port(port)
    
    # Change to root directory
    os.chdir(ROOT_DIR)
    
    # Start the server
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    
    print(f"✅ Starting file server on port {port}...")
    print(f"📂 Serving files from {ROOT_DIR}")
    print(f"🌐 Access URL: http://localhost:{port}/")
    print("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    run_server()
