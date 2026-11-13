"""
MIRAI — Assistant Response Formatter (M16)
Formats backend quantitative results into structured markdown responses.
Provides deterministic, safety-guaranteed formatting for investment decisions and comparisons.
"""

from typing import Any, Dict, List, Optional
from src.assistant.financial_safety import FinancialSafetyGuard, STANDARD_DISCLAIMER


class ResponseFormatter:
    """
    Transforms raw backend tool outputs into clean, user-friendly markdown.
    """

    @staticmethod
    def format_investment_decision(data: Optional[Dict[str, Any]]) -> str:
        """
        Formats Part 7 authoritative investment decision response.
        Enforces verdict preservation and disclaimers.
        """
        if not data or not isinstance(data, dict):
            return "Unable to format investment decision: No structured evaluation data available."
        sym = data.get("symbol", "N/A")
        verdict = data.get("verdict", "INSUFFICIENT_DATA")
        display_label = data.get("display_label", verdict)
        score = data.get("composite_score", 0.0)
        confidence = data.get("confidence", 0.0)
        risk_status = data.get("risk_status", "UNKNOWN")
        ref_price = data.get("entry_reference_price")
        sl = data.get("suggested_stop_loss")
        tp = data.get("suggested_take_profit")
        explanation = data.get("explanation", "")
        pos_factors = data.get("positive_factors", [])
        neg_factors = data.get("negative_factors", [])
        conflicts = data.get("conflicting_signals", [])
        ts = data.get("timestamp", "Current")

        lines = [
            f"### Investment Analysis: {sym}",
            f"**Authoritative Verdict:** `{verdict}` ({display_label})",
            f"**Composite Score:** {score:.1f} / 100 | **Model Confidence:** {confidence:.2%}",
            f"**Risk Gatekeeper Status:** `{risk_status}`",
            "",
            "#### 1. Price Targets & Levels",
            f"- **Reference Entry Price:** ₹{ref_price:.2f}" if ref_price else "- **Reference Entry Price:** N/A",
            f"- **Suggested Stop-Loss:** ₹{sl:.2f}" if sl else "- **Suggested Stop-Loss:** N/A",
            f"- **Suggested Take-Profit:** ₹{tp:.2f}" if tp else "- **Suggested Take-Profit:** N/A",
            "",
            "#### 2. Decision Rationale & Evidence",
            f"{explanation}",
            "",
        ]

        if pos_factors:
            lines.append("**Key Positive Factors:**")
            for f in pos_factors:
                lines.append(f"- {f}")
            lines.append("")

        if neg_factors:
            lines.append("**Key Negative / Risk Factors:**")
            for f in neg_factors:
                lines.append(f"- {f}")
            lines.append("")

        if conflicts:
            lines.append("**Conflicting Signals Observed:**")
            for c in conflicts:
                lines.append(f"- {c}")
            lines.append("")

        lines.extend([
            f"*Data Freshness: As of {ts}*",
            "",
            "---",
            f"*Disclaimer: {STANDARD_DISCLAIMER}*",
        ])
        return "\n".join(lines)

    @staticmethod
    def format_stock_strength(data: Optional[Dict[str, Any]]) -> str:
        """Formats M05 stock strength response."""
        if not data or not isinstance(data, dict):
            return "Unable to format stock strength: No data available."
        sym = data.get("symbol", "N/A")
        score = data.get("stock_strength_score", 0.0)
        status = data.get("status", "NEUTRAL")
        confidence = data.get("confidence", 0.0)
        as_of = data.get("as_of_date", "N/A")
        factors = data.get("factor_scores", {})

        lines = [
            f"### Stock Strength Intelligence: {sym}",
            f"- **Total Score:** **{score:.1f} / 100** (`{status}`)",
            f"- **Confidence:** {confidence:.2%}",
            f"- **As of Date:** {as_of}",
            "",
            "**Pillar Breakdown:**",
        ]
        for k, v in factors.items():
            lines.append(f"- **{k.replace('_', ' ').title()}:** {v:.1f} / 100")

        lines.append("")
        lines.append(f"*Disclaimer: {STANDARD_DISCLAIMER}*")
        return "\n".join(lines)

    @staticmethod
    def format_market_regime(data: Optional[Dict[str, Any]]) -> str:
        """Formats M07 market regime response."""
        if not data or not isinstance(data, dict):
            return "Unable to format market regime: No data available."
        pipeline = data.get("pipeline", "pipeline_b_nifty")
        regime = data.get("current_regime", "UNKNOWN")
        probs = data.get("regime_probabilities", {})

        lines = [
            f"### Market Regime Intelligence ({pipeline})",
            f"**Identified Regime:** `{regime}`",
            "",
            "**Regime Probabilities:**",
        ]
        for r_name, p in probs.items():
            lines.append(f"- **{r_name}:** {p:.1%}")

        lines.append("")
        lines.append(f"*Disclaimer: {STANDARD_DISCLAIMER}*")
        return "\n".join(lines)

    @staticmethod
    def format_stock_comparison(data: Optional[Dict[str, Any]]) -> str:
        """Formats multi-stock comparison table."""
        if not data or not isinstance(data, dict):
            return "Unable to format stock comparison: No data available."
        comparison = data.get("comparison", [])
        if not comparison:
            return "No comparison data available."

        lines = [
            "### Comparative Stock Intelligence",
            "| Symbol | Strength Score | Strength Status | Fundamental Score | Classification |",
            "|:-------|:--------------:|:---------------:|:-----------------:|:--------------:|",
        ]
        for row in comparison:
            lines.append(
                f"| {row.get('symbol')} | {row.get('stock_strength_score', 0):.1f} | "
                f"{row.get('strength_status')} | {row.get('fundamental_score', 0):.1f} | "
                f"{row.get('fundamental_classification')} |"
            )

        lines.append("")
        lines.append(f"*Disclaimer: {STANDARD_DISCLAIMER}*")
        return "\n".join(lines)

    @staticmethod
    def format_generic_tool_results(tool_results: List[Dict[str, Any]]) -> str:
        """Fallback markdown formatter for generic tool executions."""
        lines = ["### MIRAI System Intelligence Results", ""]
        for tr in tool_results:
            name = tr.get("tool_name", "Tool")
            data = tr.get("data", {})
            lines.append(f"#### {name.replace('_', ' ').title()}")
            if isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"- **{k.replace('_', ' ').title()}:** {v}")
            else:
                lines.append(f"{data}")
            lines.append("")

        lines.append(f"*Disclaimer: {STANDARD_DISCLAIMER}*")
        return "\n".join(lines)
