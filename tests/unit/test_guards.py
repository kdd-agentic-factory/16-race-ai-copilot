"""Unit tests for ApprovalGuard and EvidenceRequiredGuard."""

import unittest

from race_ai_copilot.guardrails.approval_guard import ApprovalGuard
from race_ai_copilot.guardrails.evidence_required_guard import (
    EvidenceRequiredGuard,
)
from race_ai_copilot.guardrails.race_decision_guard import RaceDecisionGuard
from race_ai_copilot.guardrails.safety_policy import SafetyPolicy
from race_ai_copilot.models.schemas import EvidencePacket, EvidenceItem


# ---------------------------------------------------------------------------
# ApprovalGuard
# ---------------------------------------------------------------------------

class ApprovalGuardTests(unittest.TestCase):
    """Tests that ApprovalGuard correctly flags critical keywords."""

    def setUp(self):
        self.guard = ApprovalGuard()

    def test_safe_message_returns_no_approval(self):
        result = self.guard.evaluate("What is the current tire temperature?", [])
        self.assertFalse(result["approval_required"])
        self.assertIsNone(result["approver_role"])

    def test_critical_keyword_mapping_triggers_approval(self):
        result = self.guard.evaluate("Update the fuel mapping for lap 5", [])
        self.assertTrue(result["approval_required"])
        self.assertEqual(result["approver_role"], "crew_chief")

    def test_critical_keyword_tire_pressure_triggers_approval(self):
        result = self.guard.evaluate("Change the tire pressure to 22 PSI", [])
        self.assertTrue(result["approval_required"])
        self.assertEqual(result["approver_role"], "crew_chief")

    def test_critical_keyword_suspension_triggers_approval(self):
        result = self.guard.evaluate("Adjust the suspension for turn 3", [])
        self.assertTrue(result["approval_required"])
        self.assertEqual(result["approver_role"], "crew_chief")

    def test_critical_keyword_traction_control_triggers_approval(self):
        result = self.guard.evaluate(
            "Change traction control settings for wet track", []
        )
        self.assertTrue(result["approval_required"])

    def test_critical_spanish_keyword_triggers_approval(self):
        result = self.guard.evaluate("Quiero cambiar setup para alta velocidad", [])
        self.assertTrue(result["approval_required"])

    def test_recommendations_are_also_scanned(self):
        result = self.guard.evaluate(
            "How should we handle the next stint?",
            ["Consider applying a suspension change"],
        )
        self.assertTrue(result["approval_required"])

    def test_empty_message_returns_no_approval(self):
        result = self.guard.evaluate("", [])
        self.assertFalse(result["approval_required"])


# ---------------------------------------------------------------------------
# EvidenceRequiredGuard
# ---------------------------------------------------------------------------

class EvidenceRequiredGuardTests(unittest.TestCase):
    """Tests that EvidenceRequiredGuard validates grounding correctly."""

    def setUp(self):
        self.guard = EvidenceRequiredGuard()

    def test_passes_when_require_evidence_is_false(self):
        result = self.guard.evaluate("Some answer", None, require_evidence=False)
        self.assertTrue(result["passed"])

    def test_fails_when_evidence_is_none(self):
        result = self.guard.evaluate("Some answer", None)
        self.assertFalse(result["passed"])

    def test_fails_when_evidence_is_empty_list(self):
        result = self.guard.evaluate("Some answer", [])
        self.assertFalse(result["passed"])

    def test_passes_when_evidence_is_non_empty_list(self):
        result = self.guard.evaluate("Some answer", [{"source": "rag"}])
        self.assertTrue(result["passed"])

    def test_fails_when_evidence_packet_has_empty_sources(self):
        packet = EvidencePacket(sources=[], raw_data=[])
        result = self.guard.evaluate("Some answer", packet)
        self.assertFalse(result["passed"])

    def test_passes_when_evidence_packet_has_sources(self):
        packet = EvidencePacket(
            sources=[
                EvidenceItem(
                    id="1", title="Test", url_or_path="/test", snippet="data"
                )
            ]
        )
        result = self.guard.evaluate("Some answer", packet)
        self.assertTrue(result["passed"])

    def test_passes_when_evidence_packet_has_raw_data(self):
        packet = EvidencePacket(sources=[], raw_data=["sensor temp: 98C"])
        result = self.guard.evaluate("Some answer", packet)
        self.assertTrue(result["passed"])

    def test_passes_when_evidence_is_populated_dict(self):
        result = self.guard.evaluate(
            "Some answer", {"sources": [{"title": "doc"}], "raw_data": []}
        )
        self.assertTrue(result["passed"])

    def test_fails_when_evidence_is_empty_dict(self):
        result = self.guard.evaluate("Some answer", {"sources": [], "raw_data": []})
        self.assertFalse(result["passed"])


# ---------------------------------------------------------------------------
# RaceDecisionGuard
# ---------------------------------------------------------------------------

class RaceDecisionGuardTests(unittest.TestCase):
    """Tests that RaceDecisionGuard replaces forbidden phrases."""

    def setUp(self):
        self.guard = RaceDecisionGuard()

    def test_replaces_change_is_approved(self):
        result = self.guard.sanitize(
            "The change is approved. We can proceed with the setup."
        )
        self.assertIn("this requires crew chief approval", result)
        self.assertNotIn("the change is approved", result)

    def test_replaces_apply_the_setup(self):
        result = self.guard.sanitize(
            "Apply the setup and confirm the new values."
        )
        self.assertIn("this requires crew chief approval", result)
        self.assertNotIn("apply the setup", result)

    def test_replaces_decision_is_final(self):
        result = self.guard.sanitize(
            "The decision is final. No further changes needed."
        )
        self.assertIn("this requires crew chief approval", result)
        self.assertNotIn("the decision is final", result)

    def test_no_change_when_no_forbidden_phrase(self):
        result = self.guard.sanitize("We recommend increasing front wing angle.")
        self.assertEqual(result, "We recommend increasing front wing angle.")

    def test_replaces_all_forbidden_phrases_in_one_pass(self):
        text = (
            "The change is approved. "
            "Apply the setup now. "
            "The decision is final."
        )
        result = self.guard.sanitize(text)
        expected_count = result.count("this requires crew chief approval")
        self.assertEqual(expected_count, 3)


# ---------------------------------------------------------------------------
# SafetyPolicy (integration)
# ---------------------------------------------------------------------------

class SafetyPolicyTests(unittest.TestCase):
    """Tests that SafetyPolicy correctly orchestrates all guards."""

    def setUp(self):
        self.policy = SafetyPolicy()

    def test_safe_message_passes_all(self):
        report = self.policy.check(
            message="What is the weather like?",
            recommendations=[],
            answer="It might rain during the race.",
            evidence=EvidencePacket(
                sources=[
                    EvidenceItem(
                        id="w1", title="Weather", url_or_path="/wx", snippet="Rain"
                    )
                ]
            ),
        )
        self.assertTrue(report["all_passed"])
        self.assertFalse(report["approval"]["approval_required"])
        self.assertTrue(report["evidence_check"]["passed"])

    def test_critical_message_requires_approval(self):
        report = self.policy.check(
            message="Change the suspension settings",
            recommendations=[],
            answer="I'll modify the suspension.",
            evidence=EvidencePacket(
                sources=[
                    EvidenceItem(
                        id="s1",
                        title="Setup",
                        url_or_path="/setup",
                        snippet="Current setup data",
                    )
                ]
            ),
        )
        self.assertFalse(report["all_passed"])
        self.assertTrue(report["approval"]["approval_required"])

    def test_missing_evidence_fails_check(self):
        report = self.policy.check(
            message="What is tire pressure?",
            recommendations=[],
            answer="The tire pressure is 22 PSI.",
            evidence=None,
        )
        self.assertFalse(report["all_passed"])
        self.assertFalse(report["evidence_check"]["passed"])

    def test_forbidden_phrase_is_sanitized(self):
        report = self.policy.check(
            message="Is the setup approved?",
            recommendations=[],
            answer="The change is approved.",
            evidence=EvidencePacket(
                sources=[
                    EvidenceItem(
                        id="e1",
                        title="Evidence",
                        url_or_path="/e",
                        snippet="test",
                    )
                ]
            ),
        )
        self.assertIn("this requires crew chief approval", report["sanitized_answer"])

    def test_empty_message_passes_with_no_evidence_required(self):
        report = self.policy.check(
            message="",
            recommendations=[],
            answer="",
            evidence=None,
            require_evidence=False,
        )
        self.assertTrue(report["evidence_check"]["passed"])
