from __future__ import annotations

import json
import pytest

pytest.importorskip("flask")

from web_app.app import create_app


def test_api_endpoints_smoke():
    app = create_app()
    app.testing = True
    client = app.test_client()

    r = client.get("/api/v1/cameras")
    assert r.status_code in (200, 404)

    r = client.get("/api/v1/employees")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)

    r = client.get("/api/v1/attendance/today")
    assert r.status_code == 200
