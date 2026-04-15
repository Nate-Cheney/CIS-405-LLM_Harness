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
            if not msg.get("content") and not msg.get("tool_calls"):
                continue

            kwargs = {}
            if msg.get("tool_calls"):
                kwargs["tool_calls"] = msg["tool_calls"]
            if msg.get("tool_call_id"):
                kwargs["tool_call_id"] = msg["tool_call_id"]
            if msg.get("name"):
                kwargs["name"] = msg["name"]

            # Safely handle the content block and unpack the tool data
            content_list = [msg.get("content")] if msg.get("content") else []
            agent_framework_messages.append(Message(msg["role"], content_list, **kwargs))

        request_options = {}
        if tools:
            request_options["tools"] = tools

        #print("\n--- Sending to LLM ---")
        #for m in agent_framework_messages:
        #    # Joins the content list into a single string for printing
        #    content_str = " ".join([str(c) for c in m.contents])
        #    print(f"[{m.role.upper()}]: {content_str}")
        #print("----------------------\n")

        response = await self.client.get_response(agent_framework_messages, options=request_options)

        response_text = ""
        if response.messages and getattr(response.messages[0], "text", None):
            response_text = response.messages[0].text

        tool_calls = []
        if response.messages and getattr(response.messages[0], "tool_calls", None):
            raw_tool_calls = response.messages[0].tool_calls
            
            for tc in raw_tool_calls:
                if isinstance(tc, dict):
                    tool_calls.append(tc)
                else:
                    tool_calls.append({
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

        return {
            "role": "assistant",
            "content": response_text,
            "tool_calls": tool_calls 
        }
