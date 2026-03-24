# Test case: login

from orbs.keyword.web import Web
from orbs.config import env


def run():
    url = env.get("url", "https://www.saucedemo.com")

    Web.open(url)
    Web.set_text("xpath=//input[@id='user-name']", env.get("username", "standard_user"))
    Web.set_text("xpath=//input[@id='password']", env.get("password", "secret_sauce"))
    Web.click("xpath=//input[@id='login-button']")
    Web.close()
