from pydantic import BaseModel


class ConfigLLMOut(BaseModel):
    papel: str
    modelo: str


class ConfigLLMIn(BaseModel):
    modelo: str  # LiteLLM format: "anthropic/claude-opus-5", "openai/gpt-5"
