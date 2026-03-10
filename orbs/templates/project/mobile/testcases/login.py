# Test case: login

from orbs.keyword.mobile import Mobile
from orbs.config import config

def run():
    # Mobile.launch("com.swaglabsmobileapp", "com.swaglabsmobileapp.MainActivity", reset=True)
    Mobile.launch_and_install("apk/sauce_labs.apk")
    Mobile.set_text("accessibility_id=test-Username", config.target("username", "standard_user"))
    Mobile.set_text("accessibility_id=test-Password", config.target("password", "secret_sauce"))
    Mobile.tap("accessibility_id=test-LOGIN")

    Mobile.verify_element_visible("accessibility_id=test-PRODUCTS")
    Mobile.take_screenshot("home_screen.png")

    Mobile.terminate_app("com.swaglabsmobileapp")
    Mobile.quit()
