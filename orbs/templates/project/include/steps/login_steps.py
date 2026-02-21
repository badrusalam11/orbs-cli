import time
from selenium.webdriver.chrome.options import Options
from behave import given, when, then
from selenium import webdriver

from orbs.browser_factory import BrowserFactory
from orbs.mobile_factory import MobileFactory
from orbs.config import config

@given('the user opens the login page')
def step_open_login(context):
    # Example: Get URL from environment configuration
    # url = config.target("url", "https://example.com")
    # context.driver.get(url)
    pass

@when('the user fill username {username} and password {password}')
def step_username(context, username, password):
    # Example: Get credentials from environment configuration
    # default_username = config.target("username", "test_user")
    # default_password = config.target("password", "test_password")
    pass

@then('the user should see the dashboard')
def step_dashboard(context):
    pass
