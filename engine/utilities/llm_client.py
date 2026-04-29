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
        to prompt a response from the LLM.

        If needed, approval for [some] tool calls are gotten
        and a response is re-generated.
        """
        cleaned_messages = self._clean_messages(messages)
        kwargs = {"tools": tools} if tools else {}
    
        result = await self.agent.run(messages=cleaned_messages, **kwargs)
    
        while True:
            approval_response_contents = self._collect_approval_responses(result)
            if not approval_response_contents:
                break
    
            # Pass approval responses back as a new user message
            approval_message = Message("user", approval_response_contents)
            result = await self.agent.run(
                messages=cleaned_messages + [approval_message],
                **kwargs
            )
    
        return self._extract_result(result)
    
    def _collect_approval_responses(self, result) -> list:
        """
        Finds function_approval_request contents, prompts the user,
        and returns a list of function_approval_response Content objects.
        """
        responses = []
        for msg in result.messages:
            for content in msg.contents:
                if content.type == "function_approval_request" and content.user_input_request:
                    function_call = content.function_call
                    args = json.loads(function_call.arguments) if function_call.arguments else {}
    
                    print(f"\n⚠  Agent wants to call: {function_call.name}")
                    print(f"   Arguments: {json.dumps(args, indent=4)}")
    
                    while True:
                        choice = input("   Approve? [y/n]: ").strip().lower()
                        if choice in ("y", "yes"):
                            # Use the framework's own method to build the response
                            responses.append(content.to_function_approval_response(approved=True))
                            break
                        if choice in ("n", "no"):
                            responses.append(content.to_function_approval_response(approved=False))
                            break
                        print("   Please enter 'y' or 'n'.")
        return responses



    async def _process_approval_requests(self, result) -> dict | None:
        """
        Scans result messages for function_approval_request events.
        Prompts user for each one. 
    
        Returns:
            dict of {request_id: approved}
        or 
            None - if there were no pending approvals.
        """
        pending = {}
    
        for msg in result.messages:
            for content in msg.contents:
                if content.type == "function_approval_request" and content.user_input_request:
                    function_call = content.function_call
                    args = json.loads(function_call.arguments) if function_call.arguments else {}
    
                    print(f"\n⚠  Agent wants to call: {function_call.name}")
                    print(f"   Arguments: {json.dumps(args, indent=4)}")
    
                    while True:
                        choice = input("   Approve? [y/n]: ").strip().lower()
                        if choice in ("y", "yes"):
                            pending[content.id] = True
                            break
                        if choice in ("n", "no"):
                            pending[content.id] = False
                            break
                        print("   Please enter 'y' or 'n'.")
    
    def _clean_messages(self, messages: list) -> list:
        cleaned = []
        for msg in messages:
            role = msg.get("role")
            if role == "tool":
                content = f"[Tool: {msg['tool_name']}]\nArgs: {msg['arguments']}\nResult: {msg['result']}"
                cleaned.append(Message("user", [content]))
            elif msg.get("content"):
                cleaned.append(Message(role, [msg["content"]]))
        return cleaned

    def _extract_result(self, result) -> dict:
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
                    for tc in tool_calls:
                        if tc["call_id"] == content.call_id:
                            tc["result"] = content.result
                            break
        return {
            "role": "assistant",
            "content": result.text or None,
            "tool_calls": tool_calls or None,
        }

