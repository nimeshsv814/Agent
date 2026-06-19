import unittest
from importlib.util import find_spec

if find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI is not installed")

from fastapi.testclient import TestClient
from app.api import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_serves_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("QuickSlot DevOps Co-Pilot", response.text)

    def test_config_endpoint(self):
        response = self.client.get("/config")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["region"], "us-east-1")

    def test_alarms_endpoint(self):
        response = self.client.get("/alarms")
        self.assertEqual(response.status_code, 200)
        self.assertIn("count", response.json())


if __name__ == "__main__":
    unittest.main()
