import json
import uuid

from agent_framework.exceptions import ChatClientException
from datetime import datetime

from managers.command_manager import CommandManager
from managers.session_manager import SessionManager
from managers.tool_manager import ToolManager
from utilities.prompt_builder import PromptBuilder
from utilities.llm_client import LLMClient


class Orchestrator:
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm = LLMClient("OpenAI-Compatible", "temp")
        self.command_manager = CommandManager()
        self.session_manager = SessionManager()
        self.tool_manager = ToolManager()

    def __del__(self):
        self.tool_manager.close_db_connection()

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
            messages.append(response)

            # Check for and handle tool calls
            # Loop until there are no more tool calls
            while response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]
                    tool_call_id = tool_call["id"]

                    try:
                        tool_args = json.loads(tool_args_str)
                        tool_result = self.tool_manager.execute_tool(tool_name, **tool_args)
                        
                    except Exception as e:
                        tool_result = f"Error executing {tool_name}: {str(e)}"

                    # Append the tool's result to the message history
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": str(tool_result)
                    })

                # Send the updated message history (with tool results) back to the LLM
                response = self.llm.generate_response(messages)
                messages.append(response)

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

