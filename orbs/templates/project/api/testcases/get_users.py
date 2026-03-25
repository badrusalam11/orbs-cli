# Test case: get_users

from orbs.keyword import api
from orbs.config import env


def run():
    base_url = env.get("api_url", "https://jsonplaceholder.typicode.com")

    api.set_base_url(base_url)

    # Implicit mode — response is stored automatically
    api.get("/users")
    api.verify_status_code(200)
    api.verify_json_field_exists("[0].id")

    # Explicit mode — capture response for direct control
    response = api.get("/users/1")
    api.verify_status_code(response, 200)
    api.verify_json_equals(response, "id", 1)

    api.post("/users", json={"name": "John Doe", "email": "john@example.com"})
    api.verify_status_code(201)

    api.close_session()
