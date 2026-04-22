## Project Architecture

```
|--sessions/  # Session history from each chat interface session
|  |--{session_id}.json
|--workspace/
|  |--AGENT.md  # Multi-agent & delegation workflows
|  |--MANDATE.md  # Behavior, personality, principles
|  |--MEMORY.md  # Long-term memory
|  |--memory/  # Daily memory files
|     |--YYYY--MM-DD.md
|--tools/
|  |--read_file  # core
|  |--write_file  # core
|  |--edit_file_chunk  # core
|  |--execute_bash_command  # core
|  |--list_tools  # core
|  |--search_web
|  |--search_memory
|  |--etc
```

## Project Description

#### Sessions

A session is a unique conversation with the agent. Each session is stored as a unique json file. 

The filename for each session is: `{session_id}.json`.  The session ID is a randomly generated unique identifier.

Simple example `session_id.json` file:

``` json
{
	"session_id": "",
	"time_initiated": "",
	"token_count": "",
	"messages": [
		{
			"role": "system",
			"contents": [
				{
					"type": "text",
					"text": "You are a helpful assistant."
				}
			]
		},
		{
			"role": "user",
			"contents": [
				{
					"type": "text",
					"text": "What are you?"
				}
			]
		},
		{
			"role": "assistant",
			"contents": [
				{
					"type": "text",
					"text": "I am a helpful assistant."
				}
			]
		}
	
	]
}
```

#### Studio

The studio is the directory where the LLM does it's work.

The markdown files in the root of the `studio/` directory makeup the system prompt for the harness.
- `AGENT.md` describes agent orchestration & how to delegate complex tasks.
- `MANDATE.md` describes desired behavior, personality, and principles.
- `MEMORY.md` are snippets of information that either the model or user has deemed as important to remember.

The `memory/` directory contains a collection of daily notes. Each daily note contains a running context/recollection of the day. The current daily note is updated at the conclusion of each session.

#### Tools

All tools accessible to the model will be kept in the `tools/` directory. Tools tagged as *core* will be initialized with each agent.

