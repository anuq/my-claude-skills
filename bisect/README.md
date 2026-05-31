# bisect

> Automated `git bisect` that finds the exact commit that introduced a bug — and explains *why* it broke.

## What it does

Drives `git bisect` from start to finish to pin down the first bad commit, then reads that commit's diff and explains the root cause in plain language. Works two ways:

- **Automated** — you give it a test command (exits 0 on pass, non-zero on fail). It runs `git bisect run` and lets git binary-search the history for you.
- **Manual** — you describe the bug in words. Claude reads each commit's diff at every bisect step and decides "good" or "bad" by reasoning about whether the change could have caused the symptom.

It also handles the annoying parts: stashing a dirty working tree before it starts, restoring your branch and stash afterward, and `git bisect skip` for commits that won't build.

## When it triggers

Say any of these and the skill activates:

- "bisect this" / "git bisect"
- "find which commit broke X"
- "when did this bug start?"
- "which commit introduced this regression?"
- "this worked last week but now it doesn't"

## How to use

Just describe the situation. The skill will ask for two things if you haven't already given them:

1. **How to detect the bug** — a test command, or a description of the symptom.
2. **A known-good commit** (optional) — a SHA, tag, or branch where the bug didn't exist. If you skip it, the skill picks a reasonable starting point from recent history.

### Example

```
You: The auth middleware started rejecting valid tokens sometime this week.
     It was fine at v2.3.0. Run: npm test -- auth.spec.ts

Claude: [stashes WIP, runs git bisect start / bad HEAD / good v2.3.0,
         then git bisect run npm test -- auth.spec.ts]

         Found it: commit a3f9c21 "refactor: simplify token clock skew check"

         Why it broke: this commit changed the skew comparison from `>=` to `>`
         on line 47 of auth.ts. Tokens issued exactly at the boundary now fail
         validation. The author intended to tighten the check but introduced an
         off-by-one on the expiry window.

         [restores your branch and pops the stash]
```

## Requirements

- A git repository with enough history between the good and bad commits.
- For automated mode: a command that reliably reproduces the bug (flaky tests will mislead the bisect).
