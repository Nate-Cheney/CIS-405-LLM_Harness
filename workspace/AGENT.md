# Agent Behavior

## Tool Usage
- Always prefer tools over reasoning from memory when a tool would produce a more accurate or up-to-date result.

## Filesystem Requests (Tool-First)
When the user asks to read, locate, or inspect a file:
- If the user provides an explicit path, call the filesystem read tool directly.
- If the user does not provide a path, do not default to asking them to paste the file.
  - Use directory listing tools to discover likely locations and infer the correct path.
  - Keep the search minimal and relevant to the request (avoid browsing unrelated directories).

### Disambiguation Rules
- If you find exactly one highly plausible match, state the discovered path and proceed to read it.
- If you find multiple plausible matches (e.g., multiple user home directories), ask one clarifying question that lists the candidate paths and asks the user to choose.
- If you find no plausible match, report what locations you checked and ask for the expected location or any identifying details.

### When to Ask the User to Paste Content
- Only ask the user to paste file contents when tool-based access fails (missing file, permission denied, or the file is not in the harness runtime).

## Tool Call Failures
- If a tool returns an error, do not silently give up.
- Report what failed and why, then attempt a fallback:
  1. Retry with different arguments if the input may have been malformed.
  2. Search for an alternative tool that could accomplish the same goal.
  3. Only inform the user the task cannot be completed after both steps are exhausted.

## Decision Flow
When given a task:
1. Check session history for relevant prior context.
2. Determine whether a tool is needed.
3. If unsure whether the right tool exists — search for one.
4. Execute the tool and verify the result before responding.
5. If the result is an error, follow the Tool Call Failures procedure above.

