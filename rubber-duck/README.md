# rubber-duck

> A Socratic debugging partner that helps you find the bug *yourself* — it never just hands you the answer.

## What it does

Classic [rubber duck debugging](https://en.wikipedia.org/wiki/Rubber_duck_debugging), but the duck asks questions back. The skill reads your code to understand it fully, then — instead of explaining the bug — asks precise, pointed questions that steer your attention to where the problem lives. You get the *aha* moment; it just nudges.

The cardinal rule: **it never states the bug, the cause, or the fix.** That's the point — working it out yourself builds the debugging instincts that a handed-over answer doesn't.

## When it triggers

- "rubber duck this with me"
- "help me think through this bug"
- "be Socratic about it" / "don't tell me the answer"
- "I want to figure this out myself"

## How it works

Questions move from broad to narrow as you answer:

1. **Symptom** — "What did you expect vs. what happened? Is it consistent?"
2. **Locate** — "Which function is running when it breaks? Where's the last point you trust the data?"
3. **Assumptions** — "What do you expect `users.get(id)` to return when `id` isn't there?"
4. **The nudge** — "Read the condition on line 42 out loud. Is that what you meant?"

Responses stay short — 1–2 questions, never more than three sentences — because you're debugging, not reading an essay.

### If you get stuck

Ask it to "just tell me" and it gives **one** hint, still framed as a question. Push a second time and it gets more pointed. Ask a third time and it relents — you've earned the answer, and it explains its reasoning in full.

## Example

```
You: rubber duck — my pagination returns duplicate rows on page 2.
     It's in fetchPage() in repo.ts.

Duck: When you build the OFFSET, what are you sorting by — and is that
      sort key guaranteed unique across rows?

You: ...it's sorted by created_at. Which isn't unique.

Duck: So if two rows share the same created_at and they straddle the
      page boundary, what happens to them across page 1 and page 2?

You: Oh. One of them shows up on both pages. I need a tiebreaker on id.

Duck: 🦆
```

## Requirements

None — works in any codebase. Best for bugs where understanding *why* matters more than a fast fix.
