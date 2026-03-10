# Test case: login

from orbs.keyword.web import Web
from orbs.config import config


def run():
    url = config.target("url", "https://www.saucedemo.com")

    Web.open(url)
    Web.set_text("xpath=//input[@id='user-name']", config.target("username", "standard_user"))
    Web.set_text("xpath=//input[@id='password']", config.target("password", "secret_sauce"))
    Web.click("xpath=//input[@id='login-button']")
    Web.close()
