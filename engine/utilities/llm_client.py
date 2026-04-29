from agent_framework import Agent, Message
import asyncio
import json
import os
from agent_framework.ollama import OllamaChatClient 
from utilities.prompt_builder import PromptBuilder


class LLMClient:
    def __init__(self):
        model_provider = os.getenv("MODEL_PROVIDER")
        self.model = os.getenv("LLM_MODEL")
        prompt_builder = PromptBuilder()
        system_prompt = prompt_builder.build_system_prompt()

        if model_provider == "OpenAI-Compatible":
            from agent_framework.openai import OpenAIChatCompletionClient
            client = OpenAIChatCompletionClient(
                base_url=os.getenv("OPENAI_BASE_URL"),
                api_key=os.getenv("OPENAI_API_KEY"),
                model=self.model,
            )

        # TODO: Do we need this since we're accessing Ollama with OpenAI API?            
        if model_provider == "Ollama":
            os.environ["OLLAMA_MODEL"] = os.getenv("LLM_MODEL")
            client=OllamaChatClient()    
    
        self.agent = client.as_agent(
            name="chat_agent",
            instructions=system_prompt
        )

    def generate_response(self, messages: list, tools: list = None ) -> dict: 
        """
        Synchronous wrapper to keep Orchestrator code simple.
        """
        return asyncio.run(self._async_generate_response(messages, tools))

    async def _async_generate_response(self, messages: list, tools: list = None) -> dict:
        """
        Asynchronous function to clean & pass message history 
        and pass available tools to the chat agent.
        """
        cleaned_messages = []
        for msg in messages:
            # Ensure system prompts are not repeated in message history
            # and that there is content in the message
            if not msg.get("content"):
                continue
            cleaned_messages.append(
                Message(msg["role"], [msg["content"]])
            )

        kwargs = {}
        if tools:
            kwargs["tools"] = tools

        result = await self.agent.run(
            messages=cleaned_messages,
            **kwargs
        )

        tool_calls = []
        for msg in result.messages:
            for content in msg.contents:
                if content.type == "function_call":
                    tool_calls.append({
                        "call_id": content.call_id,
                        "tool_name": content.name,
                        "arguments": json.loads(content.arguments) if content.arguments else None,
                    })
                elif content.type == "function_result":
                    # Match result back to its call by call_id
                    for tc in tool_calls:
                        if tc["call_id"] == content.call_id:
                            tc["result"] = content.result
                            break
    
        return {
            "role": "assistant",
            "content": result.text or None,
            "tool_calls": tool_calls or None,
        }

