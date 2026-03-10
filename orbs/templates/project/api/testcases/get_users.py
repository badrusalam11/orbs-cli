# Test case: get_users

from orbs.keyword.api import API
from orbs.config import config


def run():
    base_url = config.target("api_url", "https://jsonplaceholder.typicode.com")

    API.set_base_url(base_url)
    API.get("/users")
    API.verify_status_code(200)
    API.verify_json_field_exists("data[0].id")

    API.get("/users/1")
    API.verify_status_code(200)
    API.verify_json_equals("data.id", 1)

    API.post("/users", body={"name": "John Doe", "email": "john@example.com"})
    API.verify_status_code(201)

    API.close_session()
