import json
import tiktoken

from pathlib import Path


class SessionManager:
    def __init__(self, session_path: str = "sessions"):
        self.session_path = Path(session_path)

    def load_session(self, session_id: str) -> tuple[str, str, list[dict]]:
        """
        Reads a session based on a given session_id number.
        Returns the message history. 
        """
        with open(f"{self.session_path}/{session_id}.json", "r") as f:
            session_file = f.read()

        session = json.loads(session_file)
        
        return (session["session_id"], session["time_initiated"], session["messages"])
       
    def create_session(self, user_input: str) -> list[dict]:
        """
        Creates a new session with a given user input.
        Returns message history.
        """
        messages = [
            {"role": "user", "content": user_input}
        ]
        return messages

    def dump_session(self, session_id: str, time_initiated: str, messages: list) -> None:
        """
        Dumps session information to a file.
        """
        # Get token count for entire message history
        total_token_count = 0
        encoding = tiktoken.encoding_for_model("gpt-4")

        for message in messages:
            content = message.get("content") if message else None
            if isinstance(content, str):
                total_token_count += len(encoding.encode(content))
            result = message.get("result") if message else None
            if isinstance(result, str):
                total_token_count += len(encoding.encode(result))
        
        session_json = json.dumps({
            "session_id": session_id,
	        "time_initiated": time_initiated,
	        "token_count": total_token_count,
            "messages": messages
        }, indent=4)

        with open(f"{self.session_path}/{session_id}.json", "w") as f:
            f.write(session_json)

