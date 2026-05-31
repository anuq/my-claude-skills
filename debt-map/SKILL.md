---
name: debt-map
description: Scans a codebase and generates an interactive tech debt heatmap as a self-contained HTML file. Use this skill whenever the user mentions "tech debt", "debt map", "code health", "hotspot analysis", "churn analysis", "code quality map", "complexity analysis", "find problem areas in the code", "which files need refactoring", or anything about visualizing code health, maintenance burden, or identifying the most problematic parts of a codebase. Also trigger when the user asks about which files change the most, which code is most complex, or where the TODOs/FIXMEs are concentrated.
---

# Tech Debt Heatmap

Generate an interactive treemap visualization showing tech debt hotspots across a codebase. The output is a single self-contained HTML file with no external dependencies.

## What it measures

For each source file, the tool computes a debt score (0-100) from four signals:

- **File size** (lines of code) — larger files are harder to maintain and understand
- **Nesting depth** (max and average indentation) — proxy for cyclomatic complexity
- **Debt markers** — density of TODO, FIXME, HACK, XXX, WORKAROUND, KLUDGE comments
- **Git churn** — how many commits touched the file recently (high-churn + high-complexity = real pain)

## How to use

Run the bundled Python script to generate the heatmap. The script only requires Python 3.6+ and git — no pip dependencies.

```bash
python <skill-path>/scripts/generate_debt_map.py <repo-path> --output debt-map.html
```

### Options

- `--output` / `-o`: Output HTML file path (default: `debt-map.html`)
- `--extensions`: Comma-separated file extensions to include (default: common source code extensions)
- `--max-commits`: How many commits to scan for churn data (default: 500, increase for longer history)

### Examples

Scan the current repo with defaults:
```bash
python <skill-path>/scripts/generate_debt_map.py .
```

Scan only Java and Kotlin files:
```bash
python <skill-path>/scripts/generate_debt_map.py . --extensions .java,.kt
```

After generating, open the HTML file in the user's browser. On macOS use `open`, on Linux `xdg-open`, on Windows `start`.

## Reading the output

The HTML treemap works like this:
- **Rectangle size** = lines of code (bigger = more code)
- **Color** = debt score (green = healthy, yellow = moderate, red = high debt)
- **Hover** over any rectangle to see detailed metrics
- **Click** a directory to drill into it
- **Breadcrumb** at the top lets you navigate back up

The script also prints the top 10 hotspot files to the console with their scores — mention these to the user as a quick summary.

## Interpreting scores

- **0-20**: Healthy — small, simple, rarely changed
- **20-40**: Normal — nothing alarming
- **40-60**: Moderate debt — worth keeping an eye on
- **60-80**: High debt — these files are maintenance magnets
- **80-100**: Critical — refactoring candidates, likely painful to work in

A file with high churn AND high complexity is worse than one with just high complexity — it means developers are frequently wrestling with hard-to-maintain code.

## After generating

Summarize the findings for the user:
1. Total files analyzed and average debt score
2. The top 5-10 hotspot files and what makes them problematic
3. Any directory-level patterns (e.g., "the `legacy/` directory averages 65 while `core/` averages 22")
4. Actionable suggestions: which files would benefit most from refactoring, splitting, or cleanup
