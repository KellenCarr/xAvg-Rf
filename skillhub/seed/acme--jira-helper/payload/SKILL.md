---
name: jira-helper
description: Reads a Jira ticket by key, summarizes acceptance criteria, and starts a branch + scoped commit message. Trigger on "start ticket ABC-123" or similar.
---

# jira-helper

## When to use
- User says "start ABC-123", "what's in ABC-123", "branch for ABC-123", etc.

## Inputs
- `JIRA_TOKEN` env var must be set; the skill reads it but never prints it.

## Procedure
1. GET `https://jira.acme.example/rest/api/3/issue/<KEY>` with `Authorization: Bearer $JIRA_TOKEN`.
2. Summarize: title, type, status, acceptance criteria.
3. Suggest a branch name `feat/<KEY>-<slugified-title>`.
4. If the user agrees, run `git switch -c <branch>` and prepare a commit-message scaffold with `Refs <KEY>`.

## Hard rules
- Never echo the token value.
- Never push without explicit user approval.
