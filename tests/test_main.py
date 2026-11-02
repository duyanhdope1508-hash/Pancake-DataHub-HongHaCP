from app.main import app


def test_system_status_route_is_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/system-status" in paths
