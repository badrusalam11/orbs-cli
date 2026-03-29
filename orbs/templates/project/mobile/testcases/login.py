# Test case: login

from orbs.keyword import Mobile
from orbs.config import env

def run():
    # Mobile.launch("com.swaglabsmobileapp", "com.swaglabsmobileapp.MainActivity", reset=True)
    Mobile.launch_and_install("apk/sauce_labs.apk")
    Mobile.set_text("accessibility_id=test-Username", env.get("username", "standard_user"))
    Mobile.set_text("accessibility_id=test-Password", env.get("password", "secret_sauce"))
    Mobile.tap("accessibility_id=test-LOGIN")

    Mobile.verify_element_visible("accessibility_id=test-PRODUCTS")
    Mobile.take_screenshot("home_screen.png")

    Mobile.terminate_app("com.swaglabsmobileapp")
    Mobile.quit()
