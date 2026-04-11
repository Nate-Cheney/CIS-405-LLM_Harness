from .session_manager import SessionManager


class CommandManager:
    def __init__(self):
        # Map commands to their respective methods
        self.commands = {
            "/?": self.list_commands,
            "/list": self.list_commands,
            "/clear": self.clear_context
        }
        self.session_manager = SessionManager()

    def is_command(self, user_input: str) -> bool:
        """
        Returns True if the input starts with the command prefix '/'.
        """
        return user_input.strip().startswith("/")

    def handle_command(self, user_input: str, session_id: str, time_initiated: str, messages: list) -> tuple[str, str]:
        """
        Executes the command and returns a tuple containing:
            1. The string response to print to the user.
            2. The session_id (updated if the command modified it, otherwise unchanged).
        """
        command_name = user_input.strip().split()[0].lower()
   
        if command_name in self.commands:
            # Set/update current session info
            self.user_input = user_input
            self.session_id = session_id
            self.time_initiated = time_initiated
            self.messages = messages 

            # Call the mapped function
            return self.commands[command_name]()
        else:
            return (f"Unknown command: '{command_name}'. Type /? to see available commands.", session_id)

    def list_commands(self) -> tuple[str, str]:
        """
        Lists all available commands for the user.
        """
        command_descriptions = {
            "/? or /list": "List all available commands.",
            "/clear": "Clear the context history and start a new session."
        }
        
        output = "\n--- Available Commands ---\n"
        for cmd, desc in command_descriptions.items():
            output += f"{cmd:<15} : {desc}\n"
        output += "--------------------------\n"
        
        return (self.session_id, output)

    def clear_context(self) -> tuple[str, str]:
        """
        Clears session context by:
            1. Dumping the current session.
            2. Overriding the session_id with 'new' (forces new session on next turn)
        """
        self.session_manager.dump_session(
            self.session_id,
            self.time_initiated,
            self.messages[:-2]
        )

        return ("new", "Context cleared! Starting a fresh session.")
