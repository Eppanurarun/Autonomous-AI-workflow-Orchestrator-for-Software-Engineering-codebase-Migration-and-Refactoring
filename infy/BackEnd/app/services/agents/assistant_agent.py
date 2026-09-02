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
        # Step 0: Friendly greeting handler
        cleaned_lower = query.strip().lower().rstrip("!?.")
        if cleaned_lower in ["hi", "hii", "hiii", "hiiii", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "help"]:
            greeting_msg = (
                f"Hello! 👋 I am your **CodeGuard AI Assistant**, specializing in **{language.capitalize()}** code quality and OWASP security.\n\n"
                f"Feel free to ask me anything about your code, or try one of these questions:\n"
                f"- *\"How can I prevent SQL injection in my code?\"*\n"
                f"- *\"Why are hardcoded secrets dangerous and how do I use environment variables?\"*\n"
                f"- *\"How do I fix mutable default arguments in Python?\"*\n"
                f"- *\"Explain the security vulnerabilities found in this file.\"*\n\n"
                f"What would you like to inspect or improve?"
            )
            return ChatResponse(
                response=greeting_msg,
                sources=[],
            )

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
                    f"Programming Language Context: {language}\n\n"
                    f"Relevant Knowledge Base Guidelines:\n{rag_context_text}\n"
                    f"{analysis_context}\n"
                    f"Instructions:\n"
                    f"1. For programming, code quality, refactoring, or security questions: Provide a clear, expert, well-explained answer with code snippets where helpful.\n"
                    f"2. For any off-topic general knowledge or trivia questions (such as geography, weather, sports, general history, or 'capital of India'): Politely state that you are specialized exclusively in code quality and security analysis, and invite the user to ask any questions regarding code review, OWASP vulnerability remediation, or secure coding guidelines for {language.capitalize()}."
                )

                history_turns = []
                if history:
                    for msg in history[-4:]:
                        role_label = "User" if msg.role == "user" else "Assistant"
                        history_turns.append(f"{role_label}: {msg.content}")

                history_prompt = "\n".join(history_turns)
                full_prompt = f"{system_prompt}\n\n{history_prompt}\nUser: {query}\nAssistant:"

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt,
                )
                if response.text and response.text.strip():
                    return ChatResponse(
                        response=response.text.strip(),
                        sources=rag_sources,
                    )
            except Exception:
                pass

        # Step 4: Fallback deterministic guidance grounded in RAG KB
        if rag_results:
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
