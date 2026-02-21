from orbs.runner import Runner
from orbs.config import config

def run():
    # Example: Get URL from environment configuration
    # base_url = config.target("url", "https://example.com")
    # print(f"Running tests against: {base_url}")
    
    runner = Runner()
    runner.run_feature("include/features/login.feature")

