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

## Quickstart

0. Clone the repo `git clone https://github.com/Nate-Cheney/CIS-405-LLM_Harness.git`.
0. Create a Python virtual environment: `python -m venv .venv`.
0. Source the venv: (Mac/Linux) `source .venv/bin/activate` or (Windows) `.venv/scripts/activate.ps1`.
0. Upgrade pip: `pip install --upgrade pip`.
0. Install libraries: `pip install dotenv agent-framework tiktoken sqlite-vec sentence-transformers`.

## Example environment files

#### vLLM

``` .env
# Huggingface
HF_TOKEN=hf_...

# Inference provider
MODEL_PROVIDER=OpenAI-Compatible
OPENAI_BASE_URL=http://localhost:8000/v1
OPENAI_API_KEY=NA

# Models
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct-AWQ
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

#### Ollama

``` .env
# Huggingface
HF_TOKEN=hf_...

# Inference provider
MODEL_PROVIDER=OpenAI-Compatible
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=NA

# Models
LLM_MODEL=qwen3.5:4b
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

#### Groq

``` .env
# Huggingface
HF_TOKEN=hf...

# Inference provider
MODEL_PROVIDER=OpenAI-Compatible
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY= Your Grok API Key

# Models
LLM_MODEL=openai/gpt-oss-120b
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

#### Gemini

``` .env
# Huggingface
HF_TOKEN=hf...

# Inference provider
MODEL_PROVIDER=Gemini
GEMINI_API_KEY=Your Gemini API Key

# Models
LLM_MODEL=gemini-flash-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2
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

#### Workspace

The workspace is the directory where the LLM does it's work.

The markdown files in the root of the `workspace/` directory make up the system prompt for the harness.
- `AGENT.md` describes agent orchestration & how to delegate complex tasks.
- `MANDATE.md` describes desired behavior, personality, and principles.
- `MEMORY.md` are snippets of information that either the model or user has deemed as important to remember.

The `memory/` directory contains a collection of daily notes. Each daily note contains a running context/recollection of the day. The current daily note is updated at the conclusion of each session.

#### Tools

All tools accessible to the model will be kept in the `tools/` directory.

All tools in `tools/` are loaded and passed to the agent by default. If a tool needs gating, use `@tool(approval_mode=...)` in the tool implementation.

