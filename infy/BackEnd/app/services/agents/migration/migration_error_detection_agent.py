"""
Migration Error Detection Agent
================================
Analyzes generated Julia code for syntax errors, invalid constructs,
type issues, undefined variables/functions, incorrect imports,
and unsupported Java remnants.

This agent is part of the Migration module and is completely independent
from the existing Code Analysis and Remediation agents.
"""

import re
import json
from typing import Any, Dict, List

from google import genai
from google.genai import types

from app.core.config import settings


class MigrationErrorDetectionAgent:
    """
    Detects errors in generated Julia code after migration from Java.
    Combines static pattern detection with LLM-based semantic analysis.
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
    # STATIC ERROR DETECTION
    # ============================================================

    def _detect_java_remnants(self, julia_code: str) -> List[Dict[str, Any]]:
        """Detect Java-specific syntax that shouldn't appear in Julia."""

        errors = []
        lines = julia_code.splitlines()

        java_patterns = [
            (r'\bpublic\s+', "Java access modifier 'public' detected"),
            (r'\bprivate\s+', "Java access modifier 'private' detected"),
            (r'\bprotected\s+', "Java access modifier 'protected' detected"),
            (r'\bSystem\.out\.println\b', "Java System.out.println — use Julia println()"),
            (r'\bSystem\.out\.print\b', "Java System.out.print — use Julia print()"),
            (r'\bSystem\.in\b', "Java System.in — use Julia stdin or readline()"),
            (r'\bnew\s+\w+', "Java 'new' keyword — Julia does not use 'new' for instantiation"),
            (r'\bvoid\s+\w+', "Java 'void' return type — Julia functions don't need return type annotations"),
            (r';\s*$', "Trailing semicolon — Julia does not require semicolons"),
            (r'\bimport\s+java\.', "Java import statement detected — use Julia 'using' or 'import'"),
            (r'\bclass\s+\w+\s*\{', "Java class declaration with brace — use Julia 'struct' with 'end'"),
            (r'\bextends\s+', "Java 'extends' keyword — use Julia abstract types"),
            (r'\bimplements\s+', "Java 'implements' keyword — not applicable in Julia"),
            (r'\bnull\b', "Java 'null' — use Julia 'nothing'"),
            (r'\btrue\b(?!\s)', "Verify 'true' is lowercase (Julia uses lowercase)"),
            (r'\bfalse\b(?!\s)', "Verify 'false' is lowercase (Julia uses lowercase)"),
            (r'\bString\[\]', "Java String array syntax — use Julia Vector{String} or Array{String}"),
            (r'\bint\[\]', "Java int array syntax — use Julia Vector{Int64} or Array{Int64}"),
            (r'&&', "Java logical AND — use Julia '&&' (same in Julia, but verify context)"),
        ]

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            for pattern, message in java_patterns:
                # Skip some patterns that are also valid in Julia
                if pattern == r'&&':
                    continue  # && is valid in Julia too
                if pattern in (r'\btrue\b(?!\s)', r'\bfalse\b(?!\s)'):
                    continue  # true/false are valid in Julia

                if re.search(pattern, line):
                    severity = "HIGH" if "access modifier" in message or "'new'" in message or "class declaration" in message else "MEDIUM"
                    errors.append({
                        "type": "ERROR" if severity == "HIGH" else "WARNING",
                        "line": line_num,
                        "issue": message,
                        "severity": severity,
                        "code_snippet": stripped[:100],
                    })

        return errors

    def _detect_syntax_issues(self, julia_code: str) -> List[Dict[str, Any]]:
        """Detect basic Julia syntax issues."""

        errors = []
        lines = julia_code.splitlines()

        # Track block opening/closing
        block_openers = 0
        block_closers = 0

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Count block structures
            if re.match(r'\b(function|if|for|while|try|begin|let|do|module|struct|mutable\s+struct|abstract\s+type|quote)\b', stripped):
                block_openers += 1
            if stripped == "end" or stripped.startswith("end ") or stripped.startswith("end#"):
                block_closers += 1

            # Detect curly braces used as blocks (Java pattern)
            if re.search(r'[^{]\{[^}]*$', stripped) and not re.search(r'Dict|Set|Array|Vector|Tuple|Type\{', stripped):
                if '{' in stripped and not re.search(r'\b\w+\{', stripped):
                    errors.append({
                        "type": "ERROR",
                        "line": line_num,
                        "issue": "Curly brace used as block delimiter — Julia uses 'end' to close blocks",
                        "severity": "HIGH",
                        "code_snippet": stripped[:100],
                    })

        # Check for mismatched blocks
        if block_openers > 0 and abs(block_openers - block_closers) > 1:
            errors.append({
                "type": "ERROR",
                "line": len(lines),
                "issue": f"Possible mismatched block structure: {block_openers} openers vs {block_closers} 'end' statements",
                "severity": "HIGH",
                "code_snippet": f"Block openers: {block_openers}, end statements: {block_closers}",
            })

        return errors

    # ============================================================
    # LLM-BASED ERROR DETECTION
    # ============================================================

    def _llm_error_detection(
        self,
        julia_code: str,
        java_code: str,
        static_errors: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use Gemini to detect semantic errors in the Julia code."""

        if not self.client:
            return static_errors

        static_summary = "\n".join(
            f"- Line {e['line']}: {e['issue']} ({e['severity']})"
            for e in static_errors[:10]
        )

        prompt = f"""You are a Julia code reviewer analyzing migrated code from Java.

Check this Julia code for errors including:
1. Syntax errors
2. Invalid Julia constructs
3. Type-related issues
4. Undefined variables or functions
5. Incorrect imports/using statements
6. Invalid conversions from Java patterns
7. Incorrect function definitions
8. Missing dependencies
9. Array indexing errors (1-based vs 0-based)

Already detected issues:
{static_summary if static_summary else "None detected statically"}

Respond with ONLY valid JSON (no markdown fences):
{{
  "errors": [
    {{
      "type": "ERROR|WARNING",
      "line": <line_number_or_0_if_unknown>,
      "issue": "description of the issue",
      "severity": "HIGH|MEDIUM|LOW",
      "code_snippet": "the problematic code"
    }}
  ]
}}

If no additional errors found, return: {{"errors": []}}

Original Java code (for reference):
```java
{java_code}
```

Julia code to check:
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
            llm_errors = llm_data.get("errors", [])

            for err in llm_errors:
                if "issue" in err:
                    err.setdefault("type", "WARNING")
                    err.setdefault("line", 0)
                    err.setdefault("severity", "MEDIUM")
                    err.setdefault("code_snippet", "")
                    if err["severity"] not in ("HIGH", "MEDIUM", "LOW"):
                        err["severity"] = "MEDIUM"
                    static_errors.append(err)

        except Exception:
            pass  # LLM enhancement is best-effort

        return static_errors

    # ============================================================
    # PUBLIC API
    # ============================================================

    def detect_errors(
        self,
        julia_code: str,
        java_code: str = "",
    ) -> Dict[str, Any]:
        """
        Detect errors in generated Julia code.

        Returns:
            Dictionary with errors list and summary statistics.
        """

        if not julia_code or not julia_code.strip():
            return {
                "errors": [],
                "summary": {
                    "total": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "has_critical_errors": False,
                },
            }

        # Step 1: Detect Java remnants
        errors = self._detect_java_remnants(julia_code)

        # Step 2: Detect syntax issues
        errors.extend(self._detect_syntax_issues(julia_code))

        # Step 3: LLM-enhanced detection
        errors = self._llm_error_detection(julia_code, java_code, errors)

        # Step 4: Deduplicate by line+issue
        seen = set()
        unique_errors = []
        for err in errors:
            key = (err.get("line", 0), err.get("issue", ""))
            if key not in seen:
                seen.add(key)
                unique_errors.append(err)

        # Sort by severity then line
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        unique_errors.sort(key=lambda e: (severity_order.get(e.get("severity", "LOW"), 3), e.get("line", 0)))

        high_count = sum(1 for e in unique_errors if e.get("severity") == "HIGH")
        medium_count = sum(1 for e in unique_errors if e.get("severity") == "MEDIUM")
        low_count = sum(1 for e in unique_errors if e.get("severity") == "LOW")

        return {
            "errors": unique_errors,
            "summary": {
                "total": len(unique_errors),
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
                "has_critical_errors": high_count > 0,
            },
        }
