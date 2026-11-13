"""
Tests for MIRAI Assistant Financial Safety & Guardrails (M16)
Validates compliance disclaimers, guarantee sanitization, and verdict integrity.
"""

import pytest
from src.assistant.financial_safety import FinancialSafetyGuard, STANDARD_DISCLAIMER


def test_disclaimer_attachment():
    raw_text = "TCS Stock Strength Score is 78.5."
    guarded = FinancialSafetyGuard.attach_disclaimer(raw_text)
    assert "Disclaimer:" in guarded
    assert "quantitative research and paper-trading simulation" in guarded

    # If already present, don't duplicate
    second_pass = FinancialSafetyGuard.attach_disclaimer(guarded)
    assert second_pass.count("Disclaimer:") == 1


def test_prohibited_guarantee_detection():
    bad_text = "Investing in this stock provides a guaranteed return of 25%."
    audit = FinancialSafetyGuard.audit_response(bad_text)
    assert audit["is_compliant"] is False
    assert any("guaranteed return" in v for v in audit["violations"])


def test_prohibited_guarantee_sanitization():
    bad_text = "This strategy ensures a guaranteed profit with zero risk."
    clean_text = FinancialSafetyGuard.sanitize_guarantee_claims(bad_text)
    assert "guaranteed profit" not in clean_text
    assert "potential algorithmic return" in clean_text
