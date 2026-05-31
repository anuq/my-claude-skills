---
name: bisect
description: Automated git bisect that uses Claude to find exactly which commit introduced a bug. Use this skill whenever the user mentions bisect, "find which commit broke", "when did this bug start", "which commit introduced", "regression", "worked before but now it doesn't", "find the breaking change", or any situation where something used to work and now doesn't and they want to trace it to a specific commit. Also trigger when the user describes a bug and mentions it's a regression or that it "used to work".
---

# Git Bisect

You are an automated git bisect assistant. Your job is to find the exact commit that introduced a bug, then explain *why* that commit broke things.

## Gathering information

Before starting, you need two things from the user:

1. **How to detect the bug** — one of:
   - A test command that exits 0 on success and non-zero on failure (e.g., `./gradlew test --tests MyTest`, `npm test`, `python -m pytest tests/test_foo.py`)
   - A description of the bug if no automated test exists (you'll evaluate each commit manually by reading the diff)

2. **A known-good commit** (optional) — a commit SHA, tag, or branch where the bug definitely didn't exist. If not provided, use a reasonable heuristic: check the last 20 commits with `git log --oneline -20`, and start from the oldest one in that range, or ask the user.

If the user doesn't provide these upfront, ask. Keep the question short — one message, not a form.

## Pre-flight checks

Before running bisect:

1. Check for uncommitted changes with `git status`. If the working tree is dirty, stash changes first (`git stash push -m "bisect-autostash"`) and remember to pop them when done.
2. Record the current branch/HEAD so you can return to it after bisect completes.
3. Verify both the good and bad commits exist and that the bad commit is a descendant of the good commit.

## Running bisect

### With a test command

```
git bisect start
git bisect bad <bad-commit>
git bisect good <good-commit>
git bisect run <test-command>
```

Let git do the heavy lifting. When `bisect run` completes, it reports the first bad commit. Read the output carefully — git prints the culprit SHA.

### Without a test command (manual mode)

When the user described the bug in words instead of giving a test command, you drive bisect manually:

```
git bisect start
git bisect bad <bad-commit>
git bisect good <good-commit>
```

Then at each step:
1. Note which commit git has checked out
2. Read the diff for that commit: `git show --stat <SHA>` first for an overview, then `git show <SHA>` for the full diff
3. Based on the bug description, judge whether this commit could have introduced the bug
4. Mark it: `git bisect good` or `git bisect bad`
5. Repeat until git identifies the culprit

Be methodical. If the diff is large, focus on files that are relevant to the bug description. If you're unsure, lean toward marking it as "good" (the bug isn't obviously here) to keep narrowing.

## When you find the culprit

Once the first bad commit is identified:

1. Show the commit: SHA, author, date, and message
2. Show the diff (`git show <SHA>`)
3. Explain **why** this commit introduced the bug:
   - What specific change caused the breakage
   - What the author likely intended vs. what actually happened
   - How the bug manifests from this change
4. If applicable, suggest a fix direction (but keep it brief — the user asked for bisect, not a fix)

## Cleanup

After bisect completes (success or failure):

1. Run `git bisect reset` to return to the original HEAD
2. If you stashed changes earlier, run `git stash pop`
3. Confirm you're back on the original branch

## Error handling

- If bisect encounters a commit that can't be built/tested, use `git bisect skip`
- If the test command is flaky (passes/fails inconsistently), mention this to the user and suggest they provide a more reliable test
- If the good and bad commits are reversed (the "good" commit has the bug), detect this from git's output and swap them
