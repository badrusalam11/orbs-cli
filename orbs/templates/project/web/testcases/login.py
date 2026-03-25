# Test case: login

from orbs.keyword import web
from orbs.config import env


def run():
    url = env.get("url", "https://www.saucedemo.com")

    web.open(url)
    web.set_text("xpath=//input[@id='user-name']", env.get("username", "standard_user"))
    web.set_text("xpath=//input[@id='password']", env.get("password", "secret_sauce"))
    web.click("xpath=//input[@id='login-button']")
    web.close()
