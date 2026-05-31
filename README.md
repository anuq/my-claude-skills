# my-claude-skills

A collection of [Claude Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) for Claude Code — focused on developer workflows that aren't well covered out of the box.

## Skills

| Skill | What it does | Trigger it with |
|-------|--------------|-----------------|
| [**bisect**](bisect/) | Automated `git bisect` that finds the commit that introduced a bug and explains *why*. | "find which commit broke X", "when did this regression start?" |
| [**debt-map**](debt-map/) | Generates an interactive tech-debt heatmap (treemap) as a self-contained HTML file. | "show me the tech debt", "hotspot analysis", "which files need refactoring?" |
| [**rubber-duck**](rubber-duck/) | A Socratic debugging partner that guides you to the bug with questions — never gives the answer. | "rubber duck this", "help me think through it", "don't tell me the answer" |

## Installing

Each skill is a directory containing a `SKILL.md` (the instructions Claude reads) plus any bundled scripts. To make them available in Claude Code, point your settings at the skill directories:

```jsonc
// ~/.claude/settings.json
{
  "skills": [
    "/absolute/path/to/my-claude-skills/bisect",
    "/absolute/path/to/my-claude-skills/debt-map",
    "/absolute/path/to/my-claude-skills/rubber-duck"
  ]
}
```

Restart Claude Code and the skills will activate automatically when your request matches their description. You can also invoke one explicitly, e.g. `/bisect`.

## Anatomy of a skill

Each follows the standard skill layout:

```
skill-name/
├── SKILL.md        # YAML frontmatter (name + description) + instructions for Claude
├── README.md       # Human-facing docs (this is for you, not Claude)
└── scripts/        # Optional bundled code the skill runs (debt-map has one)
```

The `description` in each `SKILL.md` frontmatter is what determines when Claude reaches for the skill, so it lists concrete trigger phrases. The body holds the actual workflow, kept lean via [progressive disclosure](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) — heavy, deterministic work (like generating the debt-map HTML) lives in a bundled script rather than bloating the prompt.

## License

[Apache 2.0](LICENSE)
