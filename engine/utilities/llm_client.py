from agent_framework import Message, tool
from agent_framework.openai import OpenAIChatCompletionClient
import asyncio
import os


class LLMClient:
    def __init__(self, model_provider: str, model_name: str):
        if model_provider == "OpenAI-Compatible":
            self.client = OpenAIChatCompletionClient(
                base_url=os.getenv("OPENAI_BASE_URL"),
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("LLM_MODEL"),
            )

    def generate_response(self, messages: list, tools: list = None ) -> dict: 
        """
        Synchronous wrapper to keep Orchestrator code simple.
        """
        return asyncio.run(self._async_generate_response(messages, tools))

    async def _async_generate_response(self, messages: list, tools: list = None) -> dict:
        agent_framework_messages = []
        for msg in messages:
            agent_framework_messages.append(Message(msg["role"], [msg["content"]]))

        response = await self.client.get_response(agent_framework_messages)

        response_text = response.messages[0].text if response.messages else ""

        return {
            "role": "assistant",
            "content": response_text,
            "tool_calls": [] 
        }

