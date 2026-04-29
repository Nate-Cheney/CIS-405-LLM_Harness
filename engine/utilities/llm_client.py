from agent_framework import Agent, Content, Message
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

        self.agent = client.as_agent(
            name="chat_agent",
            instructions=system_prompt
        )

    def generate_response(self, messages: list, tools: list = None ) -> dict: 
        """
        Synchronous wrapper to keep Orchestrator code simple.
        """
        return asyncio.run(self._async_generate_response(raw_messages=messages, tools=tools))

    async def _async_generate_response(self, raw_messages: list, tools: list = None) -> list[Message]:
        """
        Asynchronous function to clean & pass message history
        to prompt a response from the LLM.

        If needed, approval for [some] tool calls are gotten
        and a response is re-generated.

        Returns:
            A list of message objects.
        """
       
        # Convert raw messages from list[dict] to list[Message]
        processed_messages = []
        for msg in raw_messages:
            role = msg.get("role")
            if msg.get("content"):
                processed_messages.append(Message(role, [msg["content"]]))
        
        kwargs = {"tools": tools} if tools else {}

        while True:
            response_stream = self.agent.run(processed_messages, stream=True, **kwargs)
            #async for update in response_stream:
            #    # Temporarily print stream
            #    if update.text:
            #        print(update.text, end="", flush=True)

            final = await response_stream.get_final_response()

            processed_messages.extend(final.messages)

            # Check for function approvals and handle
            approval_contents = []
            for msg in final.messages:
                for content in msg.contents:
                    if content.type == "function_approval_request":
                        # Get approval or denial from user
                        is_approved = self._get_function_approval(content.function_call)

                        # Track decision 
                        response_content = content.to_function_approval_response(approved=is_approved)
                        approval_contents.append(response_content)
            
            # Approval is not needed, final is actually the final output
            if not approval_contents:
                break

            # Approval was needed, add approval to message history, & loop again
            approval_message = Message(role="user", contents=approval_contents)
            processed_messages.append(approval_message)

        return processed_messages 
   
    # TODO: figure out function_call's type and annotate
    def _get_function_approval(self, function_call) -> bool:

        approval_string = f"""
Would you like to approve the following tool call? 
    Name: {function_call.name}.
    Args: {function_call.arguments}

(y/n): """

        while True:
            approval_decision = input(approval_string).lower().strip()

            if approval_decision not in ["y", "yes", "n", "no"]:
                print("ERROR: Invalid input, enter y or n.")
                continue

            if approval_decision in ["y", "yes"]:
                return True
            # Approval was n or no
            return False 

