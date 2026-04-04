"""Quick test to verify cache creation"""
from orbs.keyword import Web, find_test_obj
from orbs.thread_context import set_context

# Set environment explicitly
set_context("environment", "dev")

try:
    # Open Instagram
    Web.open("https://www.instagram.com/")
    
    # Try to find element using your JSON file
    # This will create cache if successful
    element = find_test_obj("input_username.json")
    
    print("✅ Element found! Check .cache/resolved_locator.json")
    print(f"Element tag: {element.tag_name}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure the element exists on the page")

finally:
    # Close browser
    import time
    time.sleep(2)
    Web.close()
