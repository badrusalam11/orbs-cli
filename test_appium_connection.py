#!/usr/bin/env python3
"""
Simple test to verify Appium connection works with our fixed endpoints
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orbs'))

from orbs.cli import ensure_appium_server
from orbs.config import Config
import requests
import time

def test_appium_connection():
    """Test basic Appium server connection"""
    print("🧪 Testing Appium connection...")
    
    # Start Appium server
    try:
        ensure_appium_server()
        print("✅ Appium server started successfully")
    except Exception as e:
        print(f"❌ Failed to start Appium: {e}")
        return False
    
    # Check if process is still running
    import subprocess
    result = subprocess.run("ps aux | grep appium", shell=True, capture_output=True, text=True)
    print(f"🔍 Running Appium processes:\n{result.stdout}")
    
    # Wait a moment for server to stabilize
    time.sleep(3)
    
    # Test status endpoint with retries
    config = Config()
    base_url = config.get("appium_url", "http://localhost:4723")
    status_url = base_url.rstrip('/') + '/status'
    
    print(f"🔍 Testing endpoint: {status_url}")
    
    for attempt in range(3):
        try:
            print(f"📡 Connection attempt {attempt + 1}/3...")
            response = requests.get(status_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status endpoint works: {data['value']['message']}")
                print(f"🔍 Appium version: {data['value']['build']['version']}")
                return True
            else:
                print(f"❌ Status endpoint returned {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Connection attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                print("⏳ Waiting before retry...")
                time.sleep(5)
    
    return False

if __name__ == "__main__":
    success = test_appium_connection()
    if success:
        print("\n🎉 Appium connection test PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Appium connection test FAILED!")
        sys.exit(1)