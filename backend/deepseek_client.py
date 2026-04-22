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

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model="deepseek-embedding",
            input=texts
        )
        return [item.embedding for item in response.data]

deepseek_client = DeepSeekClient()
