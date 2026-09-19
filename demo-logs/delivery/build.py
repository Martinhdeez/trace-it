"""Build the jury plan and the key-decision diagrams.

    uv run --with markdown python demo-logs/delivery/build.py [PREVIEW_HTML]

- albertitos_plan.md -> albertitos_plan.html (mermaid rendered to inline SVG, also saved as
  img/plan-N.svg) -> albertitos_plan.pdf (headless Chrome, A4).
- The mermaid of docs/key-decisions.md and docs/adr/A-E -> docs/img/key-*.svg.
- With PREVIEW_HTML: section 2 of the plan as a standalone page (mermaid from the CDN).
Needs npx (@mermaid-js/mermaid-cli) and Google Chrome.
"""

import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MERMAID = re.compile(r"```mermaid\n(.*?)```", re.S)
CONFIG = '{"flowchart":{"htmlLabels":false},"themeVariables":{"fontFamily":"Helvetica, Arial, sans-serif"}}'

PLAN_HEAD = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>albertitos_plan — trace-it</title>
<style>
@page { size: A4; margin: 14mm 14mm 14mm 14mm;
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt Helvetica, Arial, sans-serif; color: #777; } }
:root { color-scheme: light; }
html { background: #fff; }
body { font: 9.4pt/1.42 "Helvetica Neue", Helvetica, Arial, sans-serif; color: #1a1a1a; background: #fff; margin: 0 auto; max-width: 182mm; padding: 0 4mm; }
h1 { font-size: 19pt; margin: 0 0 4pt; letter-spacing: -.2pt; border-bottom: 2.5pt solid #1f4e79; padding-bottom: 4pt; }
h2 { font-size: 14pt; color: #1f4e79; margin: 14pt 0 5pt; border-bottom: .8pt solid #c9d6e3; padding-bottom: 2pt; break-after: avoid; }
h3 { font-size: 10.8pt; margin: 10pt 0 3pt; color: #13324f; break-after: avoid; }
p { margin: 3pt 0 5pt; }
ul { margin: 3pt 0 6pt; padding-left: 14pt; }
li { margin: 1.5pt 0; }
code { font: 8.2pt Menlo, Consolas, monospace; background: #f1f3f5; padding: 0 2pt; border-radius: 2pt; }
pre { background: #f6f7f9; border: .6pt solid #dde1e6; padding: 5pt 7pt; border-radius: 3pt; break-inside: avoid; margin: 4pt 0 6pt; }
pre code { background: none; padding: 0; font-size: 8.2pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 8pt; font-size: 8.2pt; line-height: 1.32; }
th, td { border: .5pt solid #cfd6de; padding: 2.5pt 4pt; vertical-align: top; text-align: left; }
th { background: #eaf0f6; color: #13324f; }
tr { break-inside: avoid; }
figure { margin: 6pt 0 8pt; break-inside: avoid; }
figure svg { width: 100%; height: auto; display: block; margin: 0 auto; }
h3 + ul { break-before: avoid; }
h2 + p strong:first-child { color: #13324f; }
</style></head><body>
"""

PREVIEW_HEAD = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decisiones clave trace-it</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
:root { --bg: #ffffff; --fg: #1a1f2b; --muted: #5b6474; --line: #d9dee7; --head: #f1f4f9;
  --code: #eef1f6; --accent: #1f4e79; --a: #2563eb; --b: #d97706; --c: #7c3aed; --d: #059669; --e: #db2777; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg: #10141b; --fg: #e6e9ef; --muted: #9aa3b2; --line: #2b3240;
    --head: #1a202b; --code: #1d2330; --accent: #8cb8e8; } }
:root[data-theme="dark"] { --bg: #10141b; --fg: #e6e9ef; --muted: #9aa3b2; --line: #2b3240;
  --head: #1a202b; --code: #1d2330; --accent: #8cb8e8; }
* { box-sizing: border-box; }
html, body { background: var(--bg); color: var(--fg); margin: 0; }
body { font: 16px/1.55 Inter, system-ui, sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 24px 16px 64px; }
h2 { font-size: 1.6rem; color: var(--accent); margin: 0 0 .5rem; }
h3 { font-size: 1.2rem; margin: 2.5rem 0 .6rem; padding-left: .6rem; border-left: 5px solid var(--k, var(--accent)); }
h3:nth-of-type(1) { --k: var(--a); } h3:nth-of-type(2) { --k: var(--b); } h3:nth-of-type(3) { --k: var(--c); }
h3:nth-of-type(4) { --k: var(--d); } h3:nth-of-type(5) { --k: var(--e); }
p, li { overflow-wrap: anywhere; }
code { font: .85em "JetBrains Mono", monospace; background: var(--code); padding: 0 .25em; border-radius: 4px; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--line); padding: .4rem .5rem; text-align: left; vertical-align: top; }
th { background: var(--head); }
figure { margin: 1rem 0; overflow-x: auto; background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 8px; }
figure pre.mermaid { margin: 0; background: none; text-align: center; }
figure svg { max-width: 100%; max-height: 560px; height: auto; }
</style></head><body><main>
"""

PREVIEW_TAIL = """</main>
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
mermaid.initialize({ startOnLoad: false, theme: "default", flowchart: { htmlLabels: false } });
let n = 0;
for (const el of document.querySelectorAll("pre.mermaid")) {
  const { svg } = await mermaid.render(`key${n++}`, el.textContent);
  el.innerHTML = svg;
}
</script>
</body></html>
"""


def render(src: str, out: Path, svg_id: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "in.mmd").write_text(src)
        (Path(tmp) / "cfg.json").write_text(CONFIG)
        subprocess.run(
            ["npx", "-y", "@mermaid-js/mermaid-cli", "-q", "-c", f"{tmp}/cfg.json", "-I", svg_id,
             "-b", "transparent", "-i", f"{tmp}/in.mmd", "-o", str(out)],
            check=True,
        )
    return out.read_text()


def sized(svg: str, max_w: float = 690, max_h: float = 300) -> str:
    """Fix the width so a tall diagram does not fill a page."""
    w, h = map(float, re.search(r'viewBox="[\d.-]+ [\d.-]+ ([\d.]+) ([\d.]+)"', svg).groups())
    width = min(max_w, w, max_h * w / h)
    svg = re.sub(r'<svg([^>]*?) width="100%"', r"<svg\1", svg, count=1)
    return re.sub(r'max-width: [\d.]+px;', f'width:{width:.0f}px;max-width:100%;', svg, count=1)


def plan() -> None:
    md = (HERE / "albertitos_plan.md").read_text()
    (HERE / "img").mkdir(exist_ok=True)
    figures = []

    def mermaid(m: re.Match) -> str:
        n = len(figures)
        figures.append(sized(render(m.group(1), HERE / "img" / f"plan-{n}.svg", f"mmd{n}")))
        return f"\n@@FIG{n}@@\n"

    md = MERMAID.sub(mermaid, md)
    md = re.sub(r"!\[[^\]]*\]\(architecture\.svg\)", "@@ARCH@@", md)
    body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    arch = re.sub(r"<\?xml[^>]*>", "", (HERE / "architecture.svg").read_text())
    body = body.replace("<p>@@ARCH@@</p>", f"<figure>{arch}</figure>")
    for n, svg in enumerate(figures):
        body = body.replace(f"<p>@@FIG{n}@@</p>", f"<figure>{svg}</figure>")
    (HERE / "albertitos_plan.html").write_text(PLAN_HEAD + body + "\n</body></html>\n")
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={HERE / 'albertitos_plan.pdf'}", (HERE / "albertitos_plan.html").as_uri()],
        check=True, capture_output=True,
    )


def repo_svgs() -> None:
    img = ROOT / "docs" / "img"
    img.mkdir(exist_ok=True)
    sources = {"key-overview": ROOT / "docs" / "key-decisions.md"}
    sources |= {f"key-{p.name[0].lower()}": p for p in sorted((ROOT / "docs" / "adr").glob("[A-E]-*.md"))}
    for name, path in sources.items():
        render(MERMAID.search(path.read_text()).group(1), img / f"{name}.svg", name)


def preview(out: Path) -> None:
    md = (HERE / "albertitos_plan.md").read_text()
    blocks = []
    section = MERMAID.sub(lambda m: blocks.append(m.group(1)) or f"\n@@M{len(blocks) - 1}@@\n",
                          md[md.index("## 2. ADRs"):])
    body = markdown.markdown(section, extensions=["tables", "fenced_code"])
    for n, src in enumerate(blocks):
        body = body.replace(f"<p>@@M{n}@@</p>", f'<figure><pre class="mermaid">\n{html.escape(src)}</pre></figure>')
    out.write_text(PREVIEW_HEAD + body + PREVIEW_TAIL)


if __name__ == "__main__":
    plan()
    repo_svgs()
    if len(sys.argv) > 1:
        preview(Path(sys.argv[1]))
