"""The Render service should send browser pages to the Firebase app."""

import pytest
from fastapi.testclient import TestClient

from adas.api.main import app


@pytest.mark.parametrize(
	("path", "frontend_path"),
	[
		("/", "/"),
		("/dashboard", "/dashboard"),
		("/laning", "/laning"),
		("/lane-plan", "/laning"),
		("/benchmarks", "/benchmarks"),
		("/integrations", "/integrations"),
		("/driver", "/driver"),
		("/docs", "/docs"),
	],
)
def test_browser_routes_redirect_to_firebase_frontend(path, frontend_path, monkeypatch):
	monkeypatch.setenv("FRONTEND_URL", "https://adas-nav.web.app/")
	with TestClient(app) as client:
		response = client.get(path, follow_redirects=False)

	assert response.status_code == 307
	assert response.headers["location"] == f"https://adas-nav.web.app{frontend_path}"
