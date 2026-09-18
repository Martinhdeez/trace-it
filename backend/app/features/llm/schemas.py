from pydantic import BaseModel


class LLMConfigOut(BaseModel):
    role: str
    model: str


class LLMConfigIn(BaseModel):
    model: str  # LiteLLM format: "anthropic/claude-opus-5", "openai/gpt-5"
