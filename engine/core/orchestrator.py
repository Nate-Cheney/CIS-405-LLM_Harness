import json
import os
import uuid

from agent_framework.exceptions import ChatClientException
from datetime import datetime

from managers.command_manager import CommandManager
from managers.session_manager import SessionManager
from managers.tool_manager import ToolManager
from utilities.llm_client import LLMClient


class Orchestrator:
    def __init__(self):
        self.llm = LLMClient(os.getenv("MODEL_PROVIDER"), "temp")
        self.command_manager = CommandManager()
        self.session_manager = SessionManager()
        self.tool_manager = ToolManager()

    def run_turn(self, session_id: str, user_input: str) -> tuple[str, str]:
        """
        Executes a single turn for a given session.
        
        1. Loads session if it exists -> creates one if it does not.
        2. Either:
            - Executes a user command
            - Queries LLM & appends response to message history
        3. Dumps the session

        Returns a tuple containing the active session_id and appropriate response.
        """
        # Load / create session 
        try:
            session_id, time_initiated, messages = self.session_manager.load_session(session_id)
            messages.append({"role": "user", "content": user_input})
        except FileNotFoundError:
            # Session does not already exist -> create new session
            session_id = str(uuid.uuid4()) 
            time_initiated = datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
            messages = self.session_manager.create_session(user_input)

        # Execute user command
        if self.command_manager.is_command(user_input):
            session_id, command_response = self.command_manager.handle_command(
                user_input, 
                session_id, 
                time_initiated, 
                messages
            )
            return (session_id, f"System: {command_response}")

        # Get LLM response, append to message history, and dump
        try:
            response = self.llm.generate_response(messages, self.tool_manager.core_tools)
            for tc in response.get("tool_calls") or []:
                messages.append({
                    "role": "tool",
                    "tool_name": tc["tool_name"],
                    "arguments": tc["arguments"],
                    "result": tc["result"],
                })

            if response.get("content"):
                messages.append({"role": "assistant", "content": response["content"]})

            # Dump the final session state
            self.session_manager.dump_session(
                session_id,
                time_initiated,
                messages
            )
            
            final_content = response.get("content")
            return (session_id, f"Agent: {final_content}")

        except ChatClientException as e:
            return (session_id, f"ERROR: Could not connect with the supplied chat client.\n{e}")

