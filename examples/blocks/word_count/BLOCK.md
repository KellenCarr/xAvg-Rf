---
name: word_count
description: Count words, characters, and lines in a piece of text.
load: on_demand
entry: run.py
---
This skill counts text statistics.

When the user asks "how many words in…" or similar, call the `word_count` tool
with the text as the `input` field. The tool returns a short summary of
word count, character count, and line count.

Note: this example skill runs on the host machine. Don't enable untrusted
skills — they execute with the harness process's permissions.
