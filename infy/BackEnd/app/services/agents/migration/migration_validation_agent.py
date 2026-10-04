"""
Migration Validation Agent
===========================
Determines whether the generated Julia code preserves the intended
functionality of the original Java code.

Generates equivalent test cases and compares expected behavior.

This agent is part of the Migration module and is completely independent
from the existing Remediation Agent.
"""

import re
import json
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from app.core.config import settings


class MigrationValidationAgent:
    """
    Validates that migrated Julia code preserves the intended
    functionality of the original Java source code.
    """

    VALIDATION_STATUSES = {
        "VALIDATED": "All identified behaviors match between Java and Julia",
        "PARTIALLY_VALIDATED": "Most behaviors match but some require manual review",
        "VALIDATION_REQUIRES_REVIEW": "Could not fully validate — manual review recommended",
        "FAILED": "Significant behavioral differences detected",
    }

    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            try:
                self.client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(
                        timeout=90000,
                        retry_options=types.HttpRetryOptions(
                            attempts=2,
                        ),
                    ),
                )
            except Exception:
                self.client = None

    # ============================================================
    # VALIDATION LOGIC
    # ============================================================

    def validate(
        self,
        java_code: str,
        julia_code: str,
        analysis: Optional[Dict[str, Any]] = None,
        errors_remaining: int = 0,
    ) -> Dict[str, Any]:
        """
        Validate functional equivalence between Java and Julia code.

        Parameters:
            java_code: Original Java source code
            julia_code: Generated Julia code
            analysis: Migration analysis result
            errors_remaining: Number of errors still present

        Returns:
            Validation report with status, test cases, and comparison.
        """

        if not julia_code or not julia_code.strip():
            return {
                "status": "FAILED",
                "status_description": "No Julia code to validate",
                "java_behavior": "",
                "julia_behavior": "",
                "test_cases": [],
                "functional_comparison": [],
                "overall_confidence": 0,
            }

        # If there are still critical errors, skip full validation
        if errors_remaining > 5:
            return {
                "status": "FAILED",
                "status_description": f"Too many remaining errors ({errors_remaining}) to validate functionality",
                "java_behavior": "",
                "julia_behavior": "",
                "test_cases": [],
                "functional_comparison": [],
                "overall_confidence": 0,
            }

        if not self.client:
            return self._static_validation(java_code, julia_code, analysis)

        return self._llm_validation(java_code, julia_code, analysis, errors_remaining)

    # ============================================================
    # STATIC VALIDATION (fallback)
    # ============================================================

    def _static_validation(
        self,
        java_code: str,
        julia_code: str,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Basic structural comparison when LLM is not available."""

        java_funcs = set(re.findall(r'(?:public|private|protected|static\s+)?\w+\s+(\w+)\s*\(', java_code))
        julia_funcs = set(re.findall(r'function\s+(\w+)\s*\(', julia_code))

        # Check if key functions are preserved
        matched = java_funcs & julia_funcs
        missing = java_funcs - julia_funcs

        comparison = []
        for func in matched:
            comparison.append({
                "feature": f"Function: {func}",
                "java_behavior": f"Method {func} defined in Java",
                "julia_behavior": f"Function {func} defined in Julia",
                "match": True,
            })

        for func in missing:
            comparison.append({
                "feature": f"Function: {func}",
                "java_behavior": f"Method {func} defined in Java",
                "julia_behavior": f"Function {func} NOT found in Julia (may be renamed)",
                "match": False,
            })

        if len(missing) == 0 and len(matched) > 0:
            status = "PARTIALLY_VALIDATED"
            confidence = 60
        elif len(missing) > len(matched):
            status = "VALIDATION_REQUIRES_REVIEW"
            confidence = 30
        else:
            status = "VALIDATION_REQUIRES_REVIEW"
            confidence = 40

        return {
            "status": status,
            "status_description": self.VALIDATION_STATUSES.get(status, ""),
            "java_behavior": f"Java code defines {len(java_funcs)} functions/methods",
            "julia_behavior": f"Julia code defines {len(julia_funcs)} functions",
            "test_cases": [],
            "functional_comparison": comparison,
            "overall_confidence": confidence,
            "note": "LLM not available — validation is based on structural comparison only",
        }

    # ============================================================
    # LLM-BASED VALIDATION
    # ============================================================

    def _llm_validation(
        self,
        java_code: str,
        julia_code: str,
        analysis: Optional[Dict[str, Any]] = None,
        errors_remaining: int = 0,
    ) -> Dict[str, Any]:
        """Use Gemini for comprehensive functional validation."""

        prompt = f"""You are a code migration validation expert. Compare the original Java code with the migrated Julia code and determine if the Julia code preserves the intended functionality.

IMPORTANT: Do NOT claim functionality is identical unless you can actually verify it through code analysis. Be honest about what can and cannot be validated through static analysis alone.

Analyze:
1. Do all Java methods/functions have Julia equivalents?
2. Do the algorithms produce the same results for the same inputs?
3. Are data structures correctly converted?
4. Are edge cases handled the same way?
5. Are there any behavioral differences?

Generate test case descriptions that could verify equivalence.

Respond with ONLY valid JSON (no markdown fences):
{{
  "status": "VALIDATED|PARTIALLY_VALIDATED|VALIDATION_REQUIRES_REVIEW|FAILED",
  "status_description": "explanation of the validation result",
  "java_behavior": "summary of what the Java code does",
  "julia_behavior": "summary of what the Julia code does",
  "test_cases": [
    {{
      "name": "test case name",
      "input": "test input description",
      "expected_java_output": "expected output from Java",
      "expected_julia_output": "expected output from Julia",
      "match": true|false
    }}
  ],
  "functional_comparison": [
    {{
      "feature": "feature being compared",
      "java_behavior": "how Java handles it",
      "julia_behavior": "how Julia handles it",
      "match": true|false
    }}
  ],
  "overall_confidence": <0-100>
}}

Remaining errors in Julia code: {errors_remaining}

Original Java code:
```java
{java_code}
```

Migrated Julia code:
```julia
{julia_code}
```"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4000,
                ),
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

            result = json.loads(text)

            # Validate status
            status = result.get("status", "VALIDATION_REQUIRES_REVIEW")
            if status not in self.VALIDATION_STATUSES:
                status = "VALIDATION_REQUIRES_REVIEW"

            return {
                "status": status,
                "status_description": result.get("status_description", self.VALIDATION_STATUSES.get(status, "")),
                "java_behavior": result.get("java_behavior", ""),
                "julia_behavior": result.get("julia_behavior", ""),
                "test_cases": result.get("test_cases", []),
                "functional_comparison": result.get("functional_comparison", []),
                "overall_confidence": min(100, max(0, result.get("overall_confidence", 50))),
            }

        except Exception:
            return self._static_validation(java_code, julia_code, analysis)
