import time
from selenium.webdriver.chrome.options import Options
from behave import given, when, then
from selenium import webdriver

from orbs.browser_factory import BrowserFactory
from orbs.mobile_factory import MobileFactory

@given('the user opens the login page')
def step_open_login(context):
    pass

@when('the user fill username {username} and password {password}')
def step_username(context, username, password):
    pass

@then('the user should see the dashboard')
def step_dashboard(context):
    pass