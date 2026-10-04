"""
Migration Analysis Agent
========================
Analyzes Java source code structure before conversion to Julia.

Identifies classes, methods, variables, control flow, exception handling,
collections, inheritance, static members, dependencies, and more.

This agent is part of the Migration module and is completely independent
from the existing Code Analysis and Remediation agents.
"""

import re
import json
from typing import Any, Dict, List

from google import genai
from google.genai import types

from app.core.config import settings


class MigrationAnalysisAgent:
    """
    Analyzes Java source code to produce a structured migration analysis
    report identifying all language constructs that need migration handling.
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
    # STATIC / REGEX-BASED ANALYSIS (always available)
    # ============================================================

    @staticmethod
    def _count_pattern(code: str, pattern: str, flags: int = 0) -> int:
        return len(re.findall(pattern, code, flags))

    def _static_analysis(self, code: str) -> Dict[str, Any]:
        """Performs regex-based structural analysis of Java code."""

        lines = code.splitlines()
        loc = len([l for l in lines if l.strip() and not l.strip().startswith("//")])

        analysis = {
            "language": "Java",
            "lines_of_code": loc,
            "total_lines": len(lines),
            "classes": self._count_pattern(code, r'\bclass\s+\w+'),
            "interfaces": self._count_pattern(code, r'\binterface\s+\w+'),
            "methods": self._count_pattern(code, r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'),
            "constructors": 0,
            "variables": self._count_pattern(code, r'(?:int|double|float|long|short|byte|char|boolean|String|var)\s+\w+'),
            "loops": (
                self._count_pattern(code, r'\bfor\s*\(') +
                self._count_pattern(code, r'\bwhile\s*\(') +
                self._count_pattern(code, r'\bdo\s*\{')
            ),
            "conditional_blocks": (
                self._count_pattern(code, r'\bif\s*\(') +
                self._count_pattern(code, r'\bswitch\s*\(') +
                self._count_pattern(code, r'\bcase\s+')
            ),
            "exception_handling": (
                self._count_pattern(code, r'\btry\s*\{') +
                self._count_pattern(code, r'\bcatch\s*\(')
            ),
            "collections": (
                self._count_pattern(code, r'\b(?:ArrayList|LinkedList|List|Set|HashSet|TreeSet|Map|HashMap|TreeMap|Queue|Deque|Stack|Vector)\b')
            ),
            "inheritance": self._count_pattern(code, r'\bextends\s+\w+'),
            "interface_implementations": self._count_pattern(code, r'\bimplements\s+[\w,\s]+'),
            "static_members": self._count_pattern(code, r'\bstatic\s+'),
            "imports": self._count_pattern(code, r'^import\s+', re.MULTILINE),
            "external_dependencies": [],
            "java_specific_apis": [],
            "threading_concurrency": (
                self._count_pattern(code, r'\bThread\b') +
                self._count_pattern(code, r'\bRunnable\b') +
                self._count_pattern(code, r'\bsynchronized\b') +
                self._count_pattern(code, r'\bExecutor\b') +
                self._count_pattern(code, r'\bFuture\b')
            ),
            "file_io_operations": (
                self._count_pattern(code, r'\bFile\b') +
                self._count_pattern(code, r'\bInputStream\b') +
                self._count_pattern(code, r'\bOutputStream\b') +
                self._count_pattern(code, r'\bReader\b') +
                self._count_pattern(code, r'\bWriter\b') +
                self._count_pattern(code, r'\bBuffered\w+\b')
            ),
            "input_output": (
                self._count_pattern(code, r'\bSystem\.out\b') +
                self._count_pattern(code, r'\bSystem\.in\b') +
                self._count_pattern(code, r'\bScanner\b') +
                self._count_pattern(code, r'\bSystem\.err\b')
            ),
        }

        # Detect constructor patterns (method name matches class name)
        class_names = re.findall(r'\bclass\s+(\w+)', code)
        for cname in class_names:
            analysis["constructors"] += self._count_pattern(
                code, rf'\b{re.escape(cname)}\s*\([^)]*\)\s*\{{'
            )

        # Extract import packages as external dependencies
        imports = re.findall(r'^import\s+([\w.]+);', code, re.MULTILINE)
        external_deps = []
        java_apis = []
        for imp in imports:
            if imp.startswith("java.") or imp.startswith("javax."):
                java_apis.append(imp)
            else:
                external_deps.append(imp)

        analysis["external_dependencies"] = external_deps
        analysis["java_specific_apis"] = java_apis

        return analysis

    def _identify_migration_concerns(self, analysis: Dict[str, Any]) -> List[str]:
        """Identify potential migration concerns based on the analysis."""

        concerns = []

        if analysis.get("classes", 0) > 0:
            concerns.append("Java class structure needs conversion to Julia structs/modules")

        if analysis.get("interfaces", 0) > 0:
            concerns.append("Java interfaces require Julia abstract type or trait pattern")

        if analysis.get("inheritance", 0) > 0:
            concerns.append("Java class inheritance needs Julia type hierarchy adaptation")

        if analysis.get("exception_handling", 0) > 0:
            concerns.append("Java try/catch/finally maps to Julia try/catch/finally with different semantics")

        if analysis.get("collections", 0) > 0:
            concerns.append("Java Collections (List, Map, Set) need conversion to Julia equivalents (Array, Dict, Set)")

        if analysis.get("static_members", 0) > 0:
            concerns.append("Java static methods/variables need module-level Julia functions/constants")

        if analysis.get("threading_concurrency", 0) > 0:
            concerns.append("Java threading/concurrency requires Julia Tasks/Channels adaptation (HIGH RISK)")

        if len(analysis.get("external_dependencies", [])) > 0:
            concerns.append(f"External dependencies detected: {', '.join(analysis['external_dependencies'])} — may lack Julia equivalents")

        if analysis.get("file_io_operations", 0) > 0:
            concerns.append("Java file I/O operations need Julia IO equivalents")

        if analysis.get("interface_implementations", 0) > 0:
            concerns.append("Java interface implementations need Julia multiple dispatch patterns")

        if len(analysis.get("java_specific_apis", [])) > 0:
            concerns.append("Java standard library APIs used — need Julia stdlib mapping")

        # Always add fundamental concern
        concerns.append("Java static typing differences vs Julia's type system")

        return concerns

    # ============================================================
    # LLM-ENHANCED ANALYSIS
    # ============================================================

    def _llm_enhanced_analysis(self, code: str, static_result: Dict[str, Any]) -> Dict[str, Any]:
        """Use Gemini to provide deeper structural analysis."""

        if not self.client:
            return static_result

        prompt = f"""Analyze this Java source code for migration to Julia.

I already have these static counts:
- Classes: {static_result.get('classes', 0)}
- Methods: {static_result.get('methods', 0)}
- Loops: {static_result.get('loops', 0)}
- Conditionals: {static_result.get('conditional_blocks', 0)}
- Exception handling blocks: {static_result.get('exception_handling', 0)}
- Collections: {static_result.get('collections', 0)}

Please provide a JSON response with ONLY these fields (do not include markdown fences):
{{
  "data_types": ["list of Java data types used"],
  "control_flow_patterns": ["list of control flow patterns"],
  "design_patterns": ["list of design patterns detected"],
  "complexity_assessment": "low|medium|high",
  "additional_concerns": ["list of any additional migration concerns not captured above"]
}}

Java code:
```java
{code}
```"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                ),
            )

            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

            llm_data = json.loads(text)
            static_result["data_types"] = llm_data.get("data_types", [])
            static_result["control_flow_patterns"] = llm_data.get("control_flow_patterns", [])
            static_result["design_patterns"] = llm_data.get("design_patterns", [])
            static_result["complexity_assessment"] = llm_data.get("complexity_assessment", "medium")
            additional = llm_data.get("additional_concerns", [])
            if additional:
                static_result.setdefault("additional_concerns", []).extend(additional)

        except Exception:
            # LLM enhancement is best-effort; static analysis is sufficient
            static_result["complexity_assessment"] = (
                "high" if static_result.get("threading_concurrency", 0) > 0
                else "medium" if static_result.get("classes", 0) > 2
                else "low"
            )

        return static_result

    # ============================================================
    # PUBLIC API
    # ============================================================

    def analyze(self, java_code: str) -> Dict[str, Any]:
        """
        Perform complete migration analysis of Java source code.

        Returns a structured dictionary with:
        - Structural counts (classes, methods, loops, etc.)
        - External dependencies
        - Java-specific APIs
        - Migration concerns
        - Complexity assessment
        """

        if not java_code or not java_code.strip():
            return {
                "error": "No Java code provided",
                "language": "Java",
            }

        # Step 1: Static regex-based analysis
        result = self._static_analysis(java_code)

        # Step 2: LLM-enhanced analysis (best-effort)
        result = self._llm_enhanced_analysis(java_code, result)

        # Step 3: Identify migration concerns
        result["migration_concerns"] = self._identify_migration_concerns(result)

        return result
