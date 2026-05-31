#!/usr/bin/env python3
"""
Generates an interactive tech debt heatmap as a self-contained HTML file.

Usage:
    python generate_debt_map.py <repo_path> [--output <output.html>] [--extensions .java,.py,.ts,.js,.go,.rs,.cpp,.c,.rb,.kt]

Scans a git repository and produces a treemap visualization where:
- Rectangle size = file size (lines of code)
- Color = debt score (green = healthy, yellow = moderate, red = high debt)
- Hover shows individual metrics
- Click to drill into directories
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_EXTENSIONS = {
    ".java", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".cpp", ".c", ".h", ".hpp", ".rb", ".kt", ".kts", ".cs",
    ".scala", ".swift", ".m", ".mm", ".php", ".lua", ".sh",
    ".sql", ".r", ".jl", ".ex", ".exs", ".erl", ".hs",
    ".ml", ".mli", ".clj", ".cljs", ".dart", ".v", ".sv",
    ".zig", ".nim", ".cr", ".pl", ".pm",
}

DEBT_MARKERS = re.compile(
    r"\b(TODO|FIXME|HACK|XXX|WORKAROUND|KLUDGE|TEMP|DEPRECATED)\b", re.IGNORECASE
)


def run_git(args, cwd):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout.strip()


def get_tracked_files(repo_path, extensions):
    raw = run_git(["ls-files"], repo_path)
    files = []
    for f in raw.splitlines():
        f = f.strip()
        if not f:
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in extensions:
            files.append(f)
    return files


def get_churn(repo_path, max_commits=500):
    """Count how many commits touched each file in the last N commits."""
    raw = run_git(
        ["log", f"--max-count={max_commits}", "--pretty=format:", "--name-only", "--diff-filter=AMRC"],
        repo_path,
    )
    churn = defaultdict(int)
    for line in raw.splitlines():
        line = line.strip()
        if line:
            churn[line] += 1
    return dict(churn)


def analyze_file(filepath, repo_path):
    full_path = os.path.join(repo_path, filepath)
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return None

    loc = len(lines)
    if loc == 0:
        return None

    debt_count = 0
    max_indent = 0
    total_indent = 0
    non_blank_lines = 0

    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        non_blank_lines += 1
        debt_count += len(DEBT_MARKERS.findall(stripped))
        leading = len(line) - len(line.lstrip())
        indent_level = leading // 4 if "\t" not in line[:leading] else line[:leading].count("\t")
        if indent_level > max_indent:
            max_indent = indent_level
        total_indent += indent_level

    avg_indent = total_indent / max(non_blank_lines, 1)

    return {
        "loc": loc,
        "debt_markers": debt_count,
        "max_nesting": max_indent,
        "avg_nesting": round(avg_indent, 2),
    }


def compute_debt_score(metrics, churn):
    """
    Debt score from 0 (healthy) to 100 (high debt).

    Factors:
    - File size (large files are harder to maintain)
    - Nesting depth (proxy for complexity)
    - Debt markers (TODO/FIXME/HACK density)
    - Churn (frequently changed files cost more attention)
    """
    loc = metrics["loc"]
    marker_density = metrics["debt_markers"] / max(loc, 1) * 1000
    max_nest = metrics["max_nesting"]
    avg_nest = metrics["avg_nesting"]

    # Size score: 0-25
    if loc < 100:
        size_score = 0
    elif loc < 300:
        size_score = 5
    elif loc < 500:
        size_score = 10
    elif loc < 1000:
        size_score = 18
    else:
        size_score = min(25, 18 + (loc - 1000) / 500)

    # Complexity score (nesting): 0-30
    nest_score = min(30, max_nest * 3 + avg_nest * 4)

    # Marker score: 0-20
    marker_score = min(20, marker_density * 5 + metrics["debt_markers"] * 0.5)

    # Churn score: 0-25
    if churn < 3:
        churn_score = 0
    elif churn < 10:
        churn_score = (churn - 3) * 1.5
    elif churn < 30:
        churn_score = 10 + (churn - 10) * 0.5
    else:
        churn_score = min(25, 20 + (churn - 30) * 0.2)

    return min(100, round(size_score + nest_score + marker_score + churn_score))


def build_tree(file_data):
    """Build nested dict structure for the treemap."""
    root = {"name": ".", "children": {}, "metrics": None}

    for entry in file_data:
        parts = entry["path"].replace("\\", "/").split("/")
        node = root
        for i, part in enumerate(parts[:-1]):
            if part not in node["children"]:
                node["children"][part] = {"name": part, "children": {}, "metrics": None}
            node = node["children"][part]
        filename = parts[-1]
        node["children"][filename] = {
            "name": filename,
            "children": {},
            "metrics": entry,
        }

    def to_list(node):
        if not node["children"]:
            return node
        result = {
            "name": node["name"],
            "children": [to_list(child) for child in sorted(node["children"].values(), key=lambda x: x["name"])],
        }
        if node["metrics"]:
            result["metrics"] = node["metrics"]
        return result

    return to_list(root)


def generate_html(tree_data, summary, output_path):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tech Debt Heatmap</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; }}
.header {{ padding: 20px 24px; border-bottom: 1px solid #21262d; }}
.header h1 {{ font-size: 20px; font-weight: 600; margin-bottom: 12px; color: #f0f6fc; }}
.stats {{ display: flex; gap: 24px; flex-wrap: wrap; }}
.stat {{ background: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 12px 16px; min-width: 140px; }}
.stat-value {{ font-size: 24px; font-weight: 700; color: #f0f6fc; }}
.stat-label {{ font-size: 12px; color: #8b949e; margin-top: 2px; }}
.breadcrumb {{ padding: 12px 24px; font-size: 13px; color: #8b949e; border-bottom: 1px solid #21262d; cursor: pointer; }}
.breadcrumb span {{ color: #58a6ff; cursor: pointer; }}
.breadcrumb span:hover {{ text-decoration: underline; }}
.treemap-container {{ padding: 16px 24px; }}
#treemap {{ position: relative; width: 100%; height: calc(100vh - 180px); background: #161b22; border-radius: 8px; overflow: hidden; }}
.treemap-node {{ position: absolute; overflow: hidden; border: 1px solid #0d1117; cursor: pointer; transition: opacity 0.15s; display: flex; align-items: center; justify-content: center; }}
.treemap-node:hover {{ opacity: 0.85; z-index: 10; }}
.treemap-label {{ font-size: 11px; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.8); padding: 2px 4px; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; pointer-events: none; }}
.tooltip {{ position: fixed; background: #1c2128; border: 1px solid #444c56; border-radius: 8px; padding: 12px 16px; font-size: 12px; pointer-events: none; z-index: 1000; max-width: 320px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); display: none; }}
.tooltip-title {{ font-weight: 600; color: #f0f6fc; margin-bottom: 8px; font-size: 13px; word-break: break-all; }}
.tooltip-row {{ display: flex; justify-content: space-between; gap: 16px; padding: 2px 0; }}
.tooltip-key {{ color: #8b949e; }}
.tooltip-val {{ color: #f0f6fc; font-weight: 500; }}
.legend {{ display: flex; align-items: center; gap: 8px; padding: 8px 24px; font-size: 12px; color: #8b949e; }}
.legend-bar {{ width: 200px; height: 12px; border-radius: 6px; background: linear-gradient(to right, #2ea043, #d29922, #f85149); }}
</style>
</head>
<body>
<div class="header">
  <h1>Tech Debt Heatmap</h1>
  <div class="stats">
    <div class="stat"><div class="stat-value">{summary['total_files']}</div><div class="stat-label">Files analyzed</div></div>
    <div class="stat"><div class="stat-value">{summary['total_loc']:,}</div><div class="stat-label">Lines of code</div></div>
    <div class="stat"><div class="stat-value">{summary['total_markers']}</div><div class="stat-label">Debt markers</div></div>
    <div class="stat"><div class="stat-value">{summary['avg_score']}</div><div class="stat-label">Avg debt score</div></div>
    <div class="stat"><div class="stat-value">{summary['hot_files']}</div><div class="stat-label">Hotspot files (score &ge; 50)</div></div>
  </div>
</div>
<div class="breadcrumb" id="breadcrumb"></div>
<div class="legend"><span>Healthy</span><div class="legend-bar"></div><span>High debt</span></div>
<div class="treemap-container"><div id="treemap"></div></div>
<div class="tooltip" id="tooltip"></div>

<script>
const DATA = {json.dumps(tree_data)};

function debtColor(score) {{
  if (score < 25) {{
    const t = score / 25;
    const r = Math.round(46 + t * (210 - 46));
    const g = Math.round(160 + t * (153 - 160));
    const b = Math.round(67 + t * (34 - 67));
    return `rgb(${{r}},${{g}},${{b}})`;
  }} else if (score < 60) {{
    const t = (score - 25) / 35;
    const r = Math.round(210 + t * (248 - 210));
    const g = Math.round(153 + t * (81 - 153));
    const b = Math.round(34 + t * (73 - 34));
    return `rgb(${{r}},${{g}},${{b}})`;
  }} else {{
    return `rgb(248, ${{Math.round(81 - (score - 60) / 40 * 40)}}, ${{Math.round(73 - (score - 60) / 40 * 30)}})`;
  }}
}}

function getLeaves(node) {{
  if (!node.children || node.children.length === 0) {{
    return node.metrics ? [node] : [];
  }}
  return node.children.flatMap(getLeaves);
}}

function squarify(items, x, y, w, h) {{
  if (items.length === 0) return [];
  const rects = [];
  const total = items.reduce((s, it) => s + it.value, 0);
  if (total === 0) return [];

  let remaining = [...items];
  let cx = x, cy = y, cw = w, ch = h;

  while (remaining.length > 0) {{
    const isWide = cw >= ch;
    const side = isWide ? ch : cw;
    const totalRemaining = remaining.reduce((s, it) => s + it.value, 0);

    let row = [remaining[0]];
    let rowSum = remaining[0].value;
    let bestRatio = Infinity;

    for (let i = 1; i < remaining.length; i++) {{
      const testSum = rowSum + remaining[i].value;
      const rowLen = (testSum / totalRemaining) * (isWide ? cw : ch);
      let worstRatio = 0;
      for (const it of [...row, remaining[i]]) {{
        const itSize = (it.value / testSum) * side;
        const ratio = Math.max(rowLen / itSize, itSize / rowLen);
        worstRatio = Math.max(worstRatio, ratio);
      }}
      const currentRowLen = (rowSum / totalRemaining) * (isWide ? cw : ch);
      let currentWorst = 0;
      for (const it of row) {{
        const itSize = (it.value / rowSum) * side;
        const ratio = Math.max(currentRowLen / itSize, itSize / currentRowLen);
        currentWorst = Math.max(currentWorst, ratio);
      }}
      if (worstRatio < currentWorst) {{
        row.push(remaining[i]);
        rowSum += remaining[i].value;
      }} else {{
        break;
      }}
    }}

    const rowFraction = rowSum / totalRemaining;
    const rowLen = rowFraction * (isWide ? cw : ch);
    let offset = 0;
    for (const it of row) {{
      const frac = it.value / rowSum;
      const itLen = frac * side;
      if (isWide) {{
        rects.push({{ ...it, x: cx, y: cy + offset, w: rowLen, h: itLen }});
      }} else {{
        rects.push({{ ...it, x: cx + offset, y: cy, w: itLen, h: rowLen }});
      }}
      offset += itLen;
    }}

    remaining = remaining.slice(row.length);
    if (isWide) {{
      cx += rowLen;
      cw -= rowLen;
    }} else {{
      cy += rowLen;
      ch -= rowLen;
    }}
  }}
  return rects;
}}

let currentPath = [];
const tooltip = document.getElementById('tooltip');
const treemapEl = document.getElementById('treemap');
const breadcrumbEl = document.getElementById('breadcrumb');

function getNode(path) {{
  let node = DATA;
  for (const p of path) {{
    node = node.children.find(c => c.name === p);
    if (!node) return null;
  }}
  return node;
}}

function renderBreadcrumb() {{
  let html = '<span data-idx="-1">root</span>';
  currentPath.forEach((p, i) => {{
    html += ` / <span data-idx="${{i}}">${{p}}</span>`;
  }});
  breadcrumbEl.innerHTML = html;
  breadcrumbEl.querySelectorAll('span').forEach(el => {{
    el.addEventListener('click', () => {{
      const idx = parseInt(el.dataset.idx);
      currentPath = currentPath.slice(0, idx + 1);
      render();
    }});
  }});
}}

function render() {{
  treemapEl.innerHTML = '';
  renderBreadcrumb();
  const node = currentPath.length === 0 ? DATA : getNode(currentPath);
  if (!node || !node.children) return;

  const items = node.children.map(child => {{
    const leaves = child.children ? getLeaves(child) : (child.metrics ? [child] : []);
    const totalLoc = leaves.reduce((s, l) => s + (l.metrics?.loc || 0), 0);
    const avgScore = leaves.length > 0
      ? Math.round(leaves.reduce((s, l) => s + (l.metrics?.debt_score || 0), 0) / leaves.length)
      : 0;
    return {{
      name: child.name,
      value: Math.max(totalLoc, 1),
      score: avgScore,
      isDir: !!(child.children && child.children.length > 0),
      metrics: child.metrics,
      childCount: leaves.length,
    }};
  }}).filter(it => it.value > 0).sort((a, b) => b.value - a.value);

  const rect = treemapEl.getBoundingClientRect();
  const rects = squarify(items, 0, 0, rect.width, rect.height);

  for (const r of rects) {{
    const div = document.createElement('div');
    div.className = 'treemap-node';
    div.style.left = r.x + 'px';
    div.style.top = r.y + 'px';
    div.style.width = r.w + 'px';
    div.style.height = r.h + 'px';
    div.style.backgroundColor = debtColor(r.score);

    if (r.w > 40 && r.h > 16) {{
      const label = document.createElement('span');
      label.className = 'treemap-label';
      label.textContent = r.name;
      div.appendChild(label);
    }}

    div.addEventListener('mouseenter', (e) => {{
      let html = `<div class="tooltip-title">${{r.name}}</div>`;
      if (r.isDir) {{
        html += `<div class="tooltip-row"><span class="tooltip-key">Files</span><span class="tooltip-val">${{r.childCount}}</span></div>`;
      }}
      html += `<div class="tooltip-row"><span class="tooltip-key">Lines</span><span class="tooltip-val">${{r.value.toLocaleString()}}</span></div>`;
      html += `<div class="tooltip-row"><span class="tooltip-key">Debt Score</span><span class="tooltip-val">${{r.score}}/100</span></div>`;
      if (r.metrics) {{
        html += `<div class="tooltip-row"><span class="tooltip-key">Markers</span><span class="tooltip-val">${{r.metrics.debt_markers}}</span></div>`;
        html += `<div class="tooltip-row"><span class="tooltip-key">Max Nesting</span><span class="tooltip-val">${{r.metrics.max_nesting}}</span></div>`;
        html += `<div class="tooltip-row"><span class="tooltip-key">Churn</span><span class="tooltip-val">${{r.metrics.churn}} commits</span></div>`;
      }}
      tooltip.innerHTML = html;
      tooltip.style.display = 'block';
    }});

    div.addEventListener('mousemove', (e) => {{
      tooltip.style.left = (e.clientX + 12) + 'px';
      tooltip.style.top = (e.clientY + 12) + 'px';
    }});

    div.addEventListener('mouseleave', () => {{
      tooltip.style.display = 'none';
    }});

    if (r.isDir) {{
      div.addEventListener('click', () => {{
        currentPath.push(r.name);
        render();
      }});
    }}

    treemapEl.appendChild(div);
  }}
}}

window.addEventListener('resize', render);
render();
</script>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description="Generate tech debt heatmap")
    parser.add_argument("repo_path", help="Path to git repository")
    parser.add_argument("--output", "-o", default="debt-map.html", help="Output HTML file path")
    parser.add_argument(
        "--extensions",
        default=None,
        help="Comma-separated file extensions to include (e.g., .java,.py,.ts)",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=500,
        help="Max commits to scan for churn data (default: 500)",
    )
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo_path)
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print(f"Error: {repo_path} is not a git repository", file=sys.stderr)
        sys.exit(1)

    extensions = DEFAULT_EXTENSIONS
    if args.extensions:
        extensions = {e.strip() if e.strip().startswith(".") else f".{e.strip()}" for e in args.extensions.split(",")}

    print(f"Scanning {repo_path}...")
    files = get_tracked_files(repo_path, extensions)
    print(f"Found {len(files)} source files")

    print("Analyzing git churn...")
    churn = get_churn(repo_path, args.max_commits)

    print("Analyzing files...")
    file_data = []
    for filepath in files:
        metrics = analyze_file(filepath, repo_path)
        if metrics is None:
            continue
        file_churn = churn.get(filepath, 0)
        score = compute_debt_score(metrics, file_churn)
        file_data.append({
            "path": filepath,
            "loc": metrics["loc"],
            "debt_markers": metrics["debt_markers"],
            "max_nesting": metrics["max_nesting"],
            "avg_nesting": metrics["avg_nesting"],
            "churn": file_churn,
            "debt_score": score,
        })

    total_loc = sum(f["loc"] for f in file_data)
    total_markers = sum(f["debt_markers"] for f in file_data)
    avg_score = round(sum(f["debt_score"] for f in file_data) / max(len(file_data), 1))
    hot_files = sum(1 for f in file_data if f["debt_score"] >= 50)

    summary = {
        "total_files": len(file_data),
        "total_loc": total_loc,
        "total_markers": total_markers,
        "avg_score": avg_score,
        "hot_files": hot_files,
    }

    print("Building treemap data...")
    tree = build_tree(file_data)

    print(f"Generating {args.output}...")
    generate_html(tree, summary, args.output)
    print(f"Done! Open {os.path.abspath(args.output)} in your browser.")

    # Print top hotspots
    top = sorted(file_data, key=lambda x: x["debt_score"], reverse=True)[:10]
    if top:
        print("\nTop 10 hotspots:")
        for i, f in enumerate(top, 1):
            print(f"  {i}. {f['path']} (score: {f['debt_score']}, loc: {f['loc']}, churn: {f['churn']}, markers: {f['debt_markers']})")


if __name__ == "__main__":
    main()
