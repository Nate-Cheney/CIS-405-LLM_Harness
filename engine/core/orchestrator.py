import uuid

from datetime import datetime

from managers.command_manager import CommandManager
from managers.session_manager import SessionManager
from utilities.prompt_builder import PromptBuilder
from utilities.llm_client import LLMClient


class Orchestrator:
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm = LLMClient("OpenAI-Compatible", "temp")
        self.command_manager = CommandManager()
        self.session_manager = SessionManager()

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
        else:
            response = self.llm.generate_response(messages)
            messages.append(response)
            self.session_manager.dump_session(
                session_id,
                time_initiated,
                messages
            )
            return (session_id, f"Agent: {response.get("content")}")

