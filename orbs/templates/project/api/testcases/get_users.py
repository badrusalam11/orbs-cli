# Test case: get_users

from orbs.keyword.api import API
from orbs.config import env


def run():
    base_url = env.get("api_url", "https://jsonplaceholder.typicode.com")

    API.set_base_url(base_url)

    # Implicit mode — response is stored automatically
    API.get("/users")
    API.verify_status_code(200)
    API.verify_json_field_exists("[0].id")

    # Explicit mode — capture response for direct control
    response = API.get("/users/1")
    API.verify_status_code(response, 200)
    API.verify_json_equals(response, "id", 1)

    API.post("/users", json={"name": "John Doe", "email": "john@example.com"})
    API.verify_status_code(201)

    API.close_session()
