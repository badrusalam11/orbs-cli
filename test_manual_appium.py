#!/usr/bin/env python3
"""
Simple manual test to start Appium and test connection
"""

import subprocess
import time
import requests
import signal
import sys

def signal_handler(sig, frame):
    print('\n🛑 Stopping test...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def test_manual_appium():
    """Manually start and test Appium"""
    print("🧪 Manual Appium test...")
    
    # Start Appium with real-time output
    print("🚀 Starting Appium server...")
    cmd = ["appium", "server", "--address", "localhost", "--port", "4723"]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Monitor output for startup
        startup_lines = []
        for _ in range(20):  # Wait max 20 lines for startup
            line = process.stdout.readline()
            if not line:
                break
            startup_lines.append(line.strip())
            print(f"📋 {line.strip()}")
            
            # Check if server is ready
            if "Appium REST http interface listener started" in line:
                print("✅ Server started successfully!")
                break
        
        # Test connection
        time.sleep(2)
        print("\n🔍 Testing connection...")
        
        try:
            response = requests.get("http://localhost:4723/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connection successful!")
                print(f"Server message: {data['value']['message']}")
                print(f"Appium version: {data['value']['build']['version']}")
                
                # Keep server running for a moment
                print("\n⏳ Server is running... Press Ctrl+C to stop")
                try:
                    while True:
                        time.sleep(1)
                        if process.poll() is not None:
                            print("❌ Process died unexpectedly")
                            break
                except KeyboardInterrupt:
                    pass
                    
            else:
                print(f"❌ Bad response: {response.status_code}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
        
        # Clean shutdown
        print("\n🛑 Stopping Appium...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            
    except Exception as e:
        print(f"❌ Failed to start Appium: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_manual_appium()