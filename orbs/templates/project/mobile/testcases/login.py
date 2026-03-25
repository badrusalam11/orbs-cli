# Test case: login

from orbs.keyword import mobile
from orbs.config import env

def run():
    # mobile.launch("com.swaglabsmobileapp", "com.swaglabsmobileapp.MainActivity", reset=True)
    mobile.launch_and_install("apk/sauce_labs.apk")
    mobile.set_text("accessibility_id=test-Username", env.get("username", "standard_user"))
    mobile.set_text("accessibility_id=test-Password", env.get("password", "secret_sauce"))
    mobile.tap("accessibility_id=test-LOGIN")

    mobile.verify_element_visible("accessibility_id=test-PRODUCTS")
    mobile.take_screenshot("home_screen.png")

    mobile.terminate_app("com.swaglabsmobileapp")
    mobile.quit()
