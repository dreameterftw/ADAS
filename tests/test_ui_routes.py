"""UI smoke tests for the landing and lane pages."""

from fastapi.testclient import TestClient

from adas.api.main import app


def test_landing_page_serves_html():
	with TestClient(app) as client:
		response = client.get("/")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "ADAS" in response.text
	assert "Every minute" in response.text


def test_laning_page_serves_html():
	with TestClient(app) as client:
		response = client.get("/laning")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "LANE PLAN" in response.text or "Route overview" in response.text


def test_dashboard_page_serves_html():
	with TestClient(app) as client:
		response = client.get("/dashboard")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "Map" in response.text and "Benchmarks" in response.text
	assert "Live" in response.text or "QAOA" in response.text


def test_driver_page_serves_html():
	with TestClient(app) as client:
		response = client.get("/driver")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "EN ROUTE" in response.text or "Confirm arrival" in response.text


def test_docs_page_serves_html():
	with TestClient(app) as client:
		response = client.get("/docs")

	assert response.status_code == 200
	assert response.headers["content-type"].startswith("text/html")
	assert "Architecture" in response.text or "QUBO" in response.text
