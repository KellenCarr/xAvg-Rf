---
name: readme-writer
description: Generates a high-quality README from the repository structure. Trigger when the user asks to write/improve a README.
---

# readme-writer

## When to use
- User asks to write, generate, or improve a README.
- A repo lacks a README or has a stub.

## Procedure
1. Inspect the repo: top-level files, `package.json`/`pyproject.toml`/`Cargo.toml`, scripts, tests.
2. Draft sections: Overview, Quickstart, Usage, Configuration, Contributing, License.
3. Keep code blocks runnable. Verify any commands you suggest exist in scripts.
4. Produce a single `README.md` ready to commit.

## Avoid
- Fabricating features that aren't in the code.
- Adding badges that don't link to real CI.
