# Test case: search

from orbs.keyword.web import Web
from orbs.config import config


def run():
    url = config.target("url", "https://www.google.com")

    Web.open(url)
    Web.set_text("xpath=//textarea[@name='q']", "orbs automation")
    Web.click("xpath=//textarea[@name='q']")
    Web.close()
