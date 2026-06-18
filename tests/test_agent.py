import unittest

from app.agent import DevOpsCopilot
from app.mock_provider import MockPlatformProvider
from app.models import IacRequest


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = DevOpsCopilot(MockPlatformProvider())

    def test_triages_booking_incident(self):
        response = self.agent.handle("QuickSlot is seeing a spike in booking errors in AZ-1")
        self.assertEqual(response.intent, "incident_triage")
        self.assertEqual(response.severity, "critical")
        self.assertIn("booking", response.message.lower())

    def test_blocks_unapproved_iac_destroy(self):
        result = self.agent.provider.invoke_iac(
            IacRequest(action="destroy", environment="dev", template="quickslot-prod-like-dev", ttl_hours=4)
        )
        self.assertEqual(result["status"], "blocked")

    def test_secret_values_are_not_returned(self):
        response = self.agent.handle("validate secret quickslot/app/prod")
        self.assertEqual(response.intent, "validate_secret")
        self.assertNotIn("password", response.message.lower())


if __name__ == "__main__":
    unittest.main()
