from behave import given, when, then

from orbs.keyword import Web
from orbs.config import env


@given('the user opens the search page')
def step_open_search(context):
    url = env.get("url", "https://www.google.com")
    Web.open_browser("chrome")
    Web.navigate(url)


@when('the user searches for {keyword}')
def step_search(context, keyword):
    Web.set_text("xpath=//textarea[@name='q']", keyword)


@then('the user should see results')
def step_verify_results(context):
    Web.close_browser()
