import os

from dotenv import load_dotenv
from langchain.chat_models import BaseChatModel, init_chat_model

load_dotenv()

_model = init_chat_model(
    model=os.getenv("LLM_NAME"),
    model_provider="openai",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
)


def get_llm_client() -> BaseChatModel:
    return _model
