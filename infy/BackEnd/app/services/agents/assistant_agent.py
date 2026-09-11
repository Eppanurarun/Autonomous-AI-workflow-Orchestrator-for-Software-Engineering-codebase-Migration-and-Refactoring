from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.assistant import ChatMessage, ChatResponse, RAGSource
from app.services.rag_service import rag_service
from app.services.storage_service import storage_service


class ConversationalAssistantAgent:
    """
    RAG-powered conversational assistant for developer Q&A, follow-up queries
    on flagged vulnerabilities, and secure coding guidance grounded in the knowledge base.
    """

    def __init__(self):
        self.rag_service = rag_service
        self.client = None
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            try:
                self.client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(
                        timeout=30000,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                )
            except Exception:
                self.client = None

    def ask(
        self,
        query: str,
        analysis_id: Optional[str] = None,
        language: str = "python",
        history: Optional[List[ChatMessage]] = None,
    ) -> ChatResponse:
        """
        Answers developer follow-up queries using RAG context and optional LLM.
        """
        display_lang = {
            "python": "Python",
            "java": "Java",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "cpp": "C++",
            "go": "Go",
            "html": "HTML",
        }.get((language or "").lower(), (language or "multi-language").capitalize())

        # Step 0: Friendly greeting handler
        cleaned_lower = query.strip().lower().rstrip("!?.")
        if cleaned_lower in ["hi", "hii", "hiii", "hiiii", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "help"]:
            greeting_msg = (
                f"Hello! 👋 I am your **CodeGuard AI Assistant**, specializing in **{display_lang}** (and Python, Java, JS, TS, C++, Go, HTML) code quality and OWASP security.\n\n"
                f"Feel free to ask me anything about your code, or try one of these questions:\n"
                f"- *\"How can I prevent SQL injection in my code?\"*\n"
                f"- *\"Why are hardcoded secrets dangerous and how do I use environment variables?\"*\n"
                f"- *\"How do I refactor code for better maintainability?\"*\n"
                f"- *\"Explain the security vulnerabilities found in this file.\"*\n\n"
                f"What would you like to inspect or improve?"
            )
            return ChatResponse(
                response=greeting_msg,
                sources=[],
            )

        # Step 0.5: Off-topic guardrail check
        query_lower = query.strip().lower()
        off_topic_keywords = [
            "capital of", "capital", "weather", "temperature", "president",
            "prime minister", "cricket", "football", "recipe", "movie", "song", "joke"
        ]
        if any(keyword in query_lower for keyword in off_topic_keywords):
            fallback_text = (
                f"I am your **CodeGuard AI Assistant**, specialized in multi-language code quality (**Python, Java, JavaScript, TypeScript, C++, Go, HTML**) and OWASP security analysis.\n\n"
                f"I don't answer general trivia or off-topic questions (like geography or weather). Feel free to ask me anything about:\n"
                f"- **Vulnerability Remediation** (e.g. *\"How do I fix SQL injection in {display_lang}?\"*)\n"
                f"- **Code Refactoring & Quality** (e.g. *\"How do I improve this code?\"*)\n"
                f"- **OWASP Security Guidelines** (e.g. *\"How do I store API keys safely?\"*)"
            )
            return ChatResponse(response=fallback_text, sources=[])

        # Step 1: Fetch RAG context
        rag_results = self.rag_service.query(
            query_text=query,
            language=language,
            top_k=3,
        )

        rag_sources = [
            RAGSource(
                title=doc.get("title", "Secure Coding Guideline"),
                category=doc.get("category", "General"),
                score=round(float(doc.get("score", 0.0)), 3),
                snippet=doc.get("content", "")[:250] + "...",
            )
            for doc in rag_results
        ]

        # Step 2: Fetch analysis context if ID is provided
        analysis_context = ""
        if analysis_id:
            analysis_data = storage_service.get_analysis(analysis_id)
            if analysis_data:
                code_snippet = analysis_data.get("code", "")[:1000]
                findings_list = analysis_data.get("findings", []) or []
                findings_str = "\n".join([
                    f"- Line {f.get('line')}: [{f.get('severity')}] {f.get('title')} - {f.get('description')}"
                    for f in findings_list[:5]
                ])
                analysis_context = f"\nAnalyzed Code:\n```\n{code_snippet}\n```\nDetected Findings:\n{findings_str}\n"

        rag_context_text = "\n\n".join([
            f"### {doc['title']} ({doc['category']})\n{doc['content']}"
            for doc in rag_results
        ])

        # Step 3: LLM Generation if available
        if self.client:
            try:
                system_prompt = (
                    f"You are an expert secure coding mentor and AI code review assistant named CodeGuard AI Assistant.\n"
                    f"You specialize strictly in programming, code quality, software architecture, and OWASP security vulnerability analysis.\n"
                    f"Supported languages: Python, Java, JavaScript, TypeScript, C++, Go, HTML. Current Language Context: {display_lang}\n\n"
                    f"Relevant Knowledge Base Guidelines:\n{rag_context_text}\n"
                    f"{analysis_context}\n"
                    f"Instructions:\n"
                    f"1. For programming, code quality, refactoring, or security questions: Provide a clear, expert, well-explained answer with code snippets where helpful.\n"
                    f"2. For any off-topic general knowledge or trivia questions (such as geography, weather, sports, general history, or 'capital of India'): Politely state that you are specialized exclusively in code quality and security analysis, and invite the user to ask any questions regarding code review, OWASP vulnerability remediation, or secure coding guidelines for {display_lang}."
                )

                history_turns = []
                if history:
                    for msg in history[-4:]:
                        role_label = "User" if msg.role == "user" else "Assistant"
                        history_turns.append(f"{role_label}: {msg.content}")

                history_prompt = "\n".join(history_turns)
                full_prompt = f"{system_prompt}\n\n{history_prompt}\nUser: {query}\nAssistant:"

                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=full_prompt,
                )
                if response.text and response.text.strip():
                    return ChatResponse(
                        response=response.text.strip(),
                        sources=rag_sources,
                    )
            except Exception:
                pass

        # Step 4: Fallback deterministic guidance grounded in RAG KB & Active Analysis
        query_lower = query.lower()

        # Off-topic guardrail check
        off_topic_keywords = [
            "capital of", "capital", "weather", "temperature", "president",
            "prime minister", "cricket", "football", "recipe", "movie", "song", "joke"
        ]
        if any(keyword in query_lower for keyword in off_topic_keywords):
            fallback_text = (
                f"I am your **CodeGuard AI Assistant**, specialized in multi-language code quality (**Python, Java, JavaScript, TypeScript, C++, Go, HTML**) and OWASP security analysis.\n\n"
                f"I don't answer general trivia or off-topic questions (like geography or weather). Feel free to ask me anything about:\n"
                f"- **Vulnerability Remediation** (e.g. *\"How do I fix SQL injection in {display_lang}?\"*)\n"
                f"- **Code Refactoring & Quality** (e.g. *\"How do I improve this code?\"*)\n"
                f"- **OWASP Security Guidelines** (e.g. *\"How do I store API keys safely?\"*)"
            )
            return ChatResponse(response=fallback_text, sources=[])

        # Active Analysis Findings & Diagnostics Query Handler
        if analysis_id:
            analysis_data = storage_service.get_analysis(analysis_id)
            if analysis_data:
                findings_list = analysis_data.get("findings", []) or []
                actionable = [f for f in findings_list if f.get("title") != "Software Architecture Metrics"]
                total_findings = len(actionable)
                high_count = sum(1 for f in actionable if str(f.get("severity", "")).lower() == "high")
                med_count = sum(1 for f in actionable if str(f.get("severity", "")).lower() == "medium")
                low_count = sum(1 for f in actionable if str(f.get("severity", "")).lower() == "low")
                filename = analysis_data.get("filename") or (f"code.{language}")

                # Query type A: "how many findings", "total issues", "count"
                if any(k in query_lower for k in ["how many", "count", "number of", "how many findings", "total findings", "findings found", "many findings"]):
                    fallback_text = (
                        f"### 🛡️ **Scan Findings Summary for `{filename}`** (ID: `{analysis_id}`)\n\n"
                        f"We detected **{total_findings} total findings** in your scanned code:\n"
                        f"- 🚨 **High Severity**: {high_count}\n"
                        f"- ⚠️ **Medium Severity**: {med_count}\n"
                        f"- 🔍 **Low / Code Smells**: {low_count}\n\n"
                    )
                    if total_findings > 0:
                        fallback_text += "#### **Detected Findings List**:\n"
                        for idx, f in enumerate(actionable[:5], 1):
                            line = f.get("line", "?")
                            sev = (f.get("severity") or "low").upper()
                            title = f.get("title", "Issue")
                            desc = f.get("description", "")
                            fallback_text += f"{idx}. **Line {line} [{sev}] - {title}**: {desc}\n"
                        fallback_text += "\n💡 *Tip*: You can view side-by-side refactored code fixes in the **AI Remediation Roadmap** tab!"
                    else:
                        fallback_text += "🎉 Great news! No vulnerabilities or code smells were flagged in this submission."

                    return ChatResponse(response=fallback_text, sources=rag_sources)

                # Query type B: "how to solve", "high severity", "issue", "what is the issue", "fix"
                if any(k in query_lower for k in ["high severity", "issue", "issues", "major", "vulnerability", "vulnerabilities", "problem", "what is", "how to solve", "how to fix", "remediate", "detail", "details", "improve", "refactor"]):
                    if total_findings > 0:
                        findings_formatted = []
                        for idx, f in enumerate(actionable[:5], 1):
                            line = f.get("line", "?")
                            sev = (f.get("severity") or "low").upper()
                            title = f.get("title", "Issue")
                            desc = f.get("description", "")
                            rec = f.get("recommendation") or f.get("description") or "Follow OWASP secure coding guidelines and sanitize untrusted inputs."
                            findings_formatted.append(
                                f"#### {idx}. **{title}** (Line {line} • `{sev}`)\n"
                                f"- **Problem**: {desc}\n"
                                f"- **How to Fix**: {rec}\n"
                            )
                        findings_str = "\n".join(findings_formatted)

                        fallback_text = (
                            f"### 🛡️ **Diagnostic Analysis & Solutions for `{filename}`**\n\n"
                            f"Found **{total_findings} issues** ({high_count} High, {med_count} Medium, {low_count} Low):\n\n"
                            f"{findings_str}\n"
                            f"💡 *Action Item*: Check the **AI Remediation Roadmap** tab for 1-click refactored code snippets."
                        )
                    else:
                        fallback_text = f"No security vulnerabilities or code smells were flagged in your scanned file (`{filename}`)."

                    return ChatResponse(response=fallback_text, sources=rag_sources)

        if any(w in query_lower for w in ["improve", "refactor", "optimize", "clean code", "better code", "fix code", "how to improve", "how to fix"]):
            fallback_text = (
                f"### 🚀 **Code Improvement & Security Checklist ({language.capitalize()})**\n\n"
                f"Here are the top 4 high-impact ways to improve and secure your codebase:\n\n"
                f"1. **🛡️ Eliminate Hardcoded Secrets**\n"
                f"   - *Problem*: Storing credentials directly in code risks leaks via git repositories.\n"
                f"   - *Fix*: Move passwords and tokens to environment variables (`os.getenv('API_KEY')`).\n\n"
                f"2. **⚡ Prevent Injection Vulnerabilities**\n"
                f"   - *Problem*: String concatenation in SQL or OS commands allows attacker code execution.\n"
                f"   - *Fix*: Use parameterized queries (`cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))`) and `subprocess.run()` without `shell=True`.\n\n"
                f"3. **🔒 Secure Deserialization & Cryptography**\n"
                f"   - *Problem*: Using `pickle.loads()` or weak `MD5`/`SHA1` algorithms.\n"
                f"   - *Fix*: Replace `pickle` with `json` or `pydantic`, and upgrade password hashing to `bcrypt` or `SHA-256`.\n\n"
                f"4. **📖 Documentation & Maintainability**\n"
                f"   - *Problem*: Missing docstrings and type annotations.\n"
                f"   - *Fix*: Add descriptive docstrings and type hints to all top-level functions."
            )
        elif rag_results:
            top_doc = rag_results[0]
            fallback_text = (
                f"### 🛡️ Knowledge Base Guidance: **{top_doc['title']}**\n\n"
                f"{top_doc['content']}\n\n"
                f"**Recommendation**: When developing in {language.capitalize()}, ensure all inputs are strictly validated, "
                f"secrets are separated from source files, and database queries use prepared statements."
            )
        else:
            fallback_text = (
                f"I am your **CodeGuard AI Assistant**, specialized in **{language.capitalize()}** code quality and OWASP security analysis.\n\n"
                f"If your query is off-topic, feel free to ask me anything about code review, security vulnerabilities, or refactoring advice!\n\n"
                f"**Core Security Guidelines**:\n"
                f"- **Input Validation**: Never trust raw user inputs; sanitize and validate against strict whitelists.\n"
                f"- **Parameterized Queries**: Always use prepared statements or bound parameters for database queries.\n"
                f"- **Secrets Management**: Store API keys, passwords, and tokens in environment variables or secret vaults."
            )

        return ChatResponse(
            response=fallback_text,
            sources=rag_sources,
        )


assistant_agent = ConversationalAssistantAgent()
