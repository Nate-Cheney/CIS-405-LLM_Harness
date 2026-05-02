import json
import os
import uuid

from agent_framework.exceptions import ChatClientException
from datetime import datetime

from managers.command_manager import CommandManager
from managers.memory_manager import MemoryManager
from managers.session_manager import SessionManager
from managers.tool_manager import ToolManager
from utilities.llm_client import LLMClient


class Orchestrator:
    def __init__(self):
        self.llm = LLMClient()
        self.command_manager = CommandManager()
        self.session_manager = SessionManager()
        self.tool_manager = ToolManager()
        self.memory_manager = MemoryManager()

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
            processed_messages = []
            messages = self.llm.generate_response(messages, self.tool_manager.tools)
            
            for msg in messages:
                role = msg.role

                match role:
                    case "assistant":
                        if hasattr(msg, "contents") and msg.contents:
                            for part in msg.contents:
                                if part.type == "text":
                                    processed_messages.append({
                                        "role": "assistant",
                                        "content": part.text, 
                                    })
                                elif part.type == "function_call": 
                                    processed_messages.append({
                                        "role": "assistant",
                                        "tool_call_id": str(part.call_id),
                                        "tool_name": part.name,
                                        "arguments": part.arguments,
                                    })
                        else:
                            processed_messages.append({
                                "role": "assistant",
                                "content": getattr(msg, "text", ""),
                            })

                    case "tool":
                        if hasattr(msg, "contents") and msg.contents:
                            for part in msg.contents:
                                # Get the result, defaulting to an empty string if it is explicitly None
                                raw_result = getattr(part, "result", None)
                                final_result = "" if raw_result is None else raw_result

                                processed_messages.append({
                                    "role": "tool",
                                    "tool_call_id": str(getattr(part, "call_id", "None")),
                                    "error_code": getattr(part, "error_code", None) or "None",
                                    "error_details": getattr(part, "error_details", None) or "None.",
                                    "result": final_result,    
                                })
                        else:
                            # Fallback just in case the tool message is malformed
                            processed_messages.append({
                                "role": "tool",
                                "tool_call_id": "Unknown",
                                "error_code": "None",
                                "error_details": "Message contained no contents.",
                                "result": "Tool call was denied by the user."
                            })

                    case "user":
                        processed_messages.append({
                            "role": "user", 
                            "content": getattr(msg, "text", "")
                        })

            # Dump the final session state
            self.session_manager.dump_session(
                session_id,
                time_initiated,
                processed_messages
            )
            
            final_message = processed_messages[-1]
            
            # Check what type of message ended the sequence to format it correctly
            if final_message["role"] == "tool":
                final_content = f"[Tool Execution] Result: {final_message.get('result')}"
            elif final_message["role"] == "assistant" and final_message.get("tool_name"):
                final_content = f"[Tool Called] Name: {final_message.get('tool_name')}"
            else:
                final_content = final_message.get("content", "")

            return (session_id, f"Agent: {final_content}")

        except ChatClientException as e:
            return (session_id, f"ERROR: Could not connect with the supplied chat client.\n{e}")

