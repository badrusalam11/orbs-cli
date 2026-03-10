# Test case: login

from orbs.keyword.mobile import Mobile
from orbs.config import config


def run():
    Mobile.start_application()
    Mobile.tap("xpath=//android.widget.EditText[@resource-id='username']")
    Mobile.set_text("xpath=//android.widget.EditText[@resource-id='username']", "test_user")
    Mobile.set_text("xpath=//android.widget.EditText[@resource-id='password']", "test_password")
    Mobile.tap("xpath=//android.widget.Button[@resource-id='loginBtn']")
    Mobile.wait_for_element_visible("xpath=//android.widget.TextView[@text='Dashboard']")
    Mobile.close_application()
