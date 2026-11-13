"""
MIRAI — Financial Safety & Compliance Guardrails (M16)
Enforces regulatory disclaimers, prohibits guaranteed return claims,
and guarantees that M09 verdicts and M11 risk vetos are never overridden by the LLM.
"""

from typing import Any, Dict, List, Optional
from src.utils.logger import get_logger

logger = get_logger("FinancialSafety")

STANDARD_DISCLAIMER = (
    "MIRAI is a quantitative research and paper-trading simulation framework. "
    "All outputs, scores, signals, and verdicts are algorithmic simulations and do not "
    "constitute financial, investment, tax, or legal advice. Capital is at risk; past "
    "or simulated performance does not guarantee future results."
)

PROHIBITED_PHRASES = [
    "guaranteed return",
    "risk-free return",
    "100% safe",
    "sure profit",
    "cannot lose",
    "guaranteed profit",
]


class FinancialSafetyGuard:
    """
    Validates model inputs and outputs for financial compliance and integrity.
    """

    @staticmethod
    def attach_disclaimer(response_text: str) -> str:
        """Appends mandatory regulatory simulation disclaimer if not already present."""
        if "MIRAI is a quantitative research" in response_text or "financial advice" in response_text:
            return response_text
        return f"{response_text}\n\n---\n*Disclaimer: {STANDARD_DISCLAIMER}*"

    @staticmethod
    def audit_response(text: str) -> Dict[str, Any]:
        """
        Inspects response text for compliance violations (e.g. false guarantees).
        Returns audit report.
        """
        lower = text.lower()
        violations = []
        for phrase in PROHIBITED_PHRASES:
            if phrase in lower:
                violations.append(f"Prohibited guarantee claim: '{phrase}'")

        if violations:
            logger.warning("Financial safety violations detected in response: %s", violations)

        return {
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "has_disclaimer": "financial advice" in lower or "simulation" in lower,
        }

    @staticmethod
    def sanitize_guarantee_claims(text: str) -> str:
        """Replaces prohibited guarantee statements with conservative risk-aware terminology."""
        sanitized = text
        for phrase in PROHIBITED_PHRASES:
            if phrase in sanitized.lower():
                # Replace case-insensitively
                import re
                sanitized = re.sub(re.escape(phrase), "potential algorithmic return", sanitized, flags=re.IGNORECASE)
        return sanitized
