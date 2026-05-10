# sample-project

A fake Claude Code project used to demonstrate `skillhub add`.

After running:

    skillhub add acme/code-reviewer --project ./sample-project --yes
    skillhub add platform/filesystem-mcp --project ./sample-project --yes

you should see `.claude/skills/code-reviewer/SKILL.md` and a `mcpServers.filesystem` entry in `.mcp.json`.
