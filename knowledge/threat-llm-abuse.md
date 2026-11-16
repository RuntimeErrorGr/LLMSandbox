# Threat: LLM abuse and prompt injection

## What the attack is

An attacker writes input that tries to make an LLM ignore its instructions or do something it should not.
OWASP lists this as LLM01: Prompt Injection, the top risk for LLM applications.

Common patterns:

- Instruction override: "Ignore all previous instructions and ..."
- Role play jailbreak: "You are DAN, an AI without rules ..."
- System prompt extraction: "Print your system prompt."
- Hidden or encoded instructions: base64 text, instructions inside a document the LLM reads.
- Harmful task requests: asking the agents to build malware, a reverse shell, or code that steals data.

## Why it matters here

The AI agents write code that runs in the sandbox. A malicious request could try to make them write a module that opens network connections, reads secrets or escapes the sandbox.

## How the guard detects it

The guard checks every request before the agents see it, in three layers:

1. Rules: regular expressions for well-known attack phrases.
2. Similarity: the request is embedded and compared, in Chroma, with known injection prompts from the deepset/prompt-injections dataset. A very similar request is blocked.
3. LLM judge: for unclear cases, the LLM receives the request plus the most similar known attacks and answers with a verdict (allow or block), a category and a reason.

Blocked requests are logged with the reason. The guard is evaluated with precision, recall and F1 on the test split of deepset/prompt-injections.
