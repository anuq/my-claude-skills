# debt-map

> Scans a codebase and generates an interactive tech-debt heatmap as a single self-contained HTML file.

## What it does

Produces a zoomable **treemap** of your repository where every file is a rectangle:

- **Size** = lines of code
- **Color** = debt score, 0–100 (green → yellow → red)
- **Hover** = per-file metrics
- **Click** a directory to drill in; breadcrumb to navigate back out

The debt score blends four signals that together predict maintenance pain:

| Signal | Why it matters |
|--------|----------------|
| File size (LOC) | Large files are harder to hold in your head |
| Nesting depth | Proxy for cyclomatic complexity |
| Debt markers | Density of `TODO` / `FIXME` / `HACK` / `XXX` / `WORKAROUND` |
| Git churn | Files changed often *and* complex are the real hotspots |

The output HTML has **no external dependencies** (inline CSS/JS), so it works offline and can be shared as a single file.

## When it triggers

- "show me the tech debt in this repo"
- "generate a debt map / code health map"
- "which files need refactoring?"
- "hotspot analysis" / "churn analysis"
- "where are all the TODOs concentrated?"

## How to use

The skill runs the bundled script. You can also run it directly:

```bash
python scripts/generate_debt_map.py <repo-path> --output debt-map.html
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output` / `-o` | `debt-map.html` | Output file path |
| `--extensions` | common source types | Comma-separated list, e.g. `.java,.kt` |
| `--max-commits` | `500` | How far back to scan for churn |

### Examples

```bash
# Current repo, all common languages
python scripts/generate_debt_map.py .

# Only Java + Kotlin, deeper churn history
python scripts/generate_debt_map.py . --extensions .java,.kt --max-commits 1000
```

After generating, the skill opens the file in your browser and prints the **top 10 hotspots** to the console.

## Reading the scores

| Score | Meaning |
|-------|---------|
| 0–20  | Healthy — small, simple, stable |
| 20–40 | Normal |
| 40–60 | Moderate — worth watching |
| 60–80 | High debt — maintenance magnets |
| 80–100| Critical — refactor candidates |

A file that is **high churn AND high complexity** is the worst kind: developers keep wrestling with code that's hard to change safely.

## Requirements

- Python 3.6+ (standard library only — no `pip install` needed)
- `git` on the PATH, run inside a git repository
