import os
from openai import AsyncOpenAI
from typing import Optional

class DeepSeekClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com"
        )

    async def chat_completion(self, messages: list, tools: Optional[list] = None, stream: bool = False):
        kwargs = {
            "model": "deepseek-chat",
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream"] = True
        return await self.client.chat.completions.create(**kwargs)

    # NOTE: DeepSeek does not expose an embeddings endpoint. Embeddings are
    # produced locally by ChromaDB's DefaultEmbeddingFunction (see rag.py).

deepseek_client = DeepSeekClient()
