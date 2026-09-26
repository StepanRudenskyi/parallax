import os
from dotenv import load_dotenv

load_dotenv()


def get_llm():
    """
    LLM_PROVIDER=ollama -> local model (target state)
    LLM_PROVIDER=groq   -> free cloud bridge #1 (fast, LPU hardware)
    LLM_PROVIDER=google -> free cloud bridge #2 (reliable structured output)
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        model_name = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
        return ChatGroq(model=model_name, temperature=0.1)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        return ChatGoogleGenerativeAI(model=model_name, temperature=0.1)

    from langchain_ollama import ChatOllama

    model_name = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    return ChatOllama(model=model_name, temperature=0.1)


def get_active_model_label() -> str:
    """
    Human-readable "provider:model" string, stored alongside every persisted
    recommendation/agent_opinion row so we can later compare quality/cost
    across providers without guessing which one produced which row.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model_env_key = {"groq": "GROQ_MODEL", "google": "GOOGLE_MODEL", "ollama": "OLLAMA_MODEL"}[provider]
    default_model = {"groq": "qwen/qwen3.6-27b", "google": "gemini-2.5-flash", "ollama": "qwen3:4b"}[provider]
    model_name = os.getenv(model_env_key, default_model)
    return f"{provider}:{model_name}"