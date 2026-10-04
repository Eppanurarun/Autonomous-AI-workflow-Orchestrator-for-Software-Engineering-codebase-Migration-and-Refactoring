"""
Migration Risk Analysis Agent
==============================
Analyzes generated Julia code and identifies constructs where
functionality may differ from the original Java code.

Categorizes risks as HIGH, MEDIUM, or LOW with descriptions,
affected code, and suggested resolutions.

This agent is part of the Migration module and is completely independent
from the existing Remediation Agent.
"""

import re
import json
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.core.config import settings


class MigrationRiskAgent:
    """
    Analyzes the migration result and identifies potential risks
    where the Julia code may not behave identically to the Java source.
    """

    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            try:
                self.client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(
                        timeout=60000,
                        retry_options=types.HttpRetryOptions(
                            attempts=2,
                        ),
                    ),
                )
            except Exception:
                self.client = None

    # ============================================================
    # STATIC RISK DETECTION
    # ============================================================

    def _static_risk_detection(
        self,
        java_code: str,
        julia_code: str,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Detect risks using pattern matching."""

        risks = []

        # HIGH risks
        if analysis and analysis.get("threading_concurrency", 0) > 0:
            risks.append({
                "risk": "Threading/Concurrency Differences",
                "description": "Java threading model (Thread, synchronized, ExecutorService) differs significantly from Julia's task-based concurrency model.",
                "affected_code": "Thread/Runnable/synchronized blocks",
                "severity": "HIGH",
                "suggested_resolution": "Review Julia Task/Channel equivalents. Manual verification of concurrent behavior is strongly recommended.",
            })

        if analysis and len(analysis.get("external_dependencies", [])) > 0:
            for dep in analysis["external_dependencies"]:
                risks.append({
                    "risk": f"External Dependency: {dep}",
                    "description": f"Java dependency '{dep}' may not have a direct Julia equivalent package.",
                    "affected_code": f"import {dep}",
                    "severity": "HIGH",
                    "suggested_resolution": f"Search Julia package registry (Pkg) for equivalent functionality or implement manually.",
                })

        if analysis and analysis.get("inheritance", 0) > 0:
            risks.append({
                "risk": "Class Inheritance Conversion",
                "description": "Java class inheritance converted to Julia abstract types. Complex inheritance hierarchies may lose behavioral nuance.",
                "affected_code": "extends/implements declarations",
                "severity": "HIGH",
                "suggested_resolution": "Verify that Julia's abstract type hierarchy + multiple dispatch correctly models the Java inheritance behavior.",
            })

        if re.search(r'\breflect\b|\bClass\.forName\b|\bgetMethod\b|\bgetField\b', java_code, re.IGNORECASE):
            risks.append({
                "risk": "Java Reflection API",
                "description": "Java Reflection has no direct Julia equivalent. Dynamic dispatch and metaprogramming can partially replace it.",
                "affected_code": "Reflection API calls",
                "severity": "HIGH",
                "suggested_resolution": "Use Julia macros and metaprogramming as alternatives where possible.",
            })

        # MEDIUM risks
        if analysis and analysis.get("exception_handling", 0) > 0:
            risks.append({
                "risk": "Exception Handling Differences",
                "description": "Java's checked exceptions and multi-catch have no direct Julia equivalent. Julia uses try/catch with exception types.",
                "affected_code": "try/catch/finally blocks",
                "severity": "MEDIUM",
                "suggested_resolution": "Ensure Julia catch blocks handle the correct exception types and that finally blocks execute properly.",
            })

        if analysis and analysis.get("collections", 0) > 0:
            risks.append({
                "risk": "Collection Behavior Differences",
                "description": "Java Collections (ArrayList, HashMap) have specific ordering/null-handling behaviors that may differ in Julia equivalents.",
                "affected_code": "Collection declarations and operations",
                "severity": "MEDIUM",
                "suggested_resolution": "Verify ordering guarantees and null/nothing handling in Julia collections match expected Java behavior.",
            })

        if re.search(r'\b(?:Integer|Double|Float|Long)\.parse\w+\b', java_code):
            risks.append({
                "risk": "Type Conversion Differences",
                "description": "Java parsing methods (Integer.parseInt, etc.) have specific error-handling behavior that may differ from Julia's parse().",
                "affected_code": "Type parsing/conversion calls",
                "severity": "MEDIUM",
                "suggested_resolution": "Use Julia's tryparse() for safe parsing and handle nothing returns appropriately.",
            })

        if analysis and analysis.get("file_io_operations", 0) > 0:
            risks.append({
                "risk": "File I/O API Differences",
                "description": "Java File/Stream APIs have different semantics from Julia's IO functions. Resource management patterns differ.",
                "affected_code": "File/Stream operations",
                "severity": "MEDIUM",
                "suggested_resolution": "Use Julia's open() with do-block pattern for automatic resource cleanup (equivalent to Java try-with-resources).",
            })

        # LOW risks
        if analysis and analysis.get("loops", 0) > 0:
            risks.append({
                "risk": "Loop Index Conversion (0-based → 1-based)",
                "description": "Java uses 0-based indexing while Julia uses 1-based indexing. Loop bounds and array accesses must be adjusted.",
                "affected_code": "for loops and array index operations",
                "severity": "LOW",
                "suggested_resolution": "Verify all array indices are correctly converted to 1-based indexing.",
            })

        if analysis and analysis.get("conditional_blocks", 0) > 0:
            risks.append({
                "risk": "Conditional Syntax",
                "description": "Basic conditional conversion is straightforward but switch/case to if/elseif may lose fall-through behavior.",
                "affected_code": "if/switch statements",
                "severity": "LOW",
                "suggested_resolution": "Verify switch fall-through behavior is not relied upon in the original Java code.",
            })

        return risks

    # ============================================================
    # LLM-ENHANCED RISK ANALYSIS
    # ============================================================

    def _llm_risk_analysis(
        self,
        java_code: str,
        julia_code: str,
        static_risks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use Gemini to detect additional migration risks."""

        if not self.client:
            return static_risks

        existing_risks_text = "\n".join(
            f"- {r['risk']} ({r['severity']})" for r in static_risks
        )

        prompt = f"""You are a migration risk analyst. Compare the original Java code with its Julia conversion and identify any additional migration risks NOT already listed.

Already identified risks:
{existing_risks_text}

Respond with ONLY valid JSON (no markdown fences):
{{
  "additional_risks": [
    {{
      "risk": "short title",
      "description": "detailed description of the risk",
      "affected_code": "the specific code construct affected",
      "severity": "HIGH|MEDIUM|LOW",
      "suggested_resolution": "how to address this risk"
    }}
  ]
}}

If there are no additional risks, return: {{"additional_risks": []}}

Original Java code:
```java
{java_code}
```

Converted Julia code:
```julia
{julia_code}
```"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=3000,
                ),
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

            llm_data = json.loads(text)
            additional = llm_data.get("additional_risks", [])

            # Validate each risk has required fields
            for risk in additional:
                if all(k in risk for k in ("risk", "description", "severity")):
                    risk.setdefault("affected_code", "N/A")
                    risk.setdefault("suggested_resolution", "Manual review recommended")
                    if risk["severity"] not in ("HIGH", "MEDIUM", "LOW"):
                        risk["severity"] = "MEDIUM"
                    static_risks.append(risk)

        except Exception:
            pass  # LLM enhancement is best-effort

        return static_risks

    # ============================================================
    # PUBLIC API
    # ============================================================

    def analyze_risks(
        self,
        java_code: str,
        julia_code: str,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive risk analysis of the migration.

        Returns:
            Dictionary with risks list and summary statistics.
        """

        if not julia_code or not julia_code.strip():
            return {
                "risks": [],
                "summary": {
                    "total": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "overall_risk_level": "UNKNOWN",
                },
            }

        # Step 1: Static risk detection
        risks = self._static_risk_detection(java_code, julia_code, analysis)

        # Step 2: LLM-enhanced risk analysis
        risks = self._llm_risk_analysis(java_code, julia_code, risks)

        # Step 3: Compute summary
        high_count = sum(1 for r in risks if r["severity"] == "HIGH")
        medium_count = sum(1 for r in risks if r["severity"] == "MEDIUM")
        low_count = sum(1 for r in risks if r["severity"] == "LOW")

        if high_count > 0:
            overall = "HIGH"
        elif medium_count > 2:
            overall = "MEDIUM"
        elif medium_count > 0:
            overall = "MEDIUM"
        else:
            overall = "LOW"

        return {
            "risks": risks,
            "summary": {
                "total": len(risks),
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
                "overall_risk_level": overall,
            },
        }
