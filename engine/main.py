from dotenv import load_dotenv, find_dotenv

from core.orchestrator import Orchestrator

load_dotenv(find_dotenv())


def main():
    # Initialize objects 
    agent = Orchestrator()

    # Initialize new session_id
    session_id = "new"

    while True:
        user_input = input("You: ")
        if user_input.lower().strip() in ["exit", "q", "quit", "stop"]:
            break

        session_id, response = agent.run_turn(session_id, user_input)
        print(response)


if __name__ == "__main__":
    main()
