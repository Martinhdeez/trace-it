"""Conservative native layout enrichment. Quotes, IDs and glyph positions stay intact."""

import re
from collections import defaultdict

import pymupdf

from app.common.extraction import TablePosition, TextLine


def suspect_spacing(lines: list[TextLine]) -> bool:
    # Latin prose only: unspaced scripts, IBANs, URLs and digit-bearing IDs are not damage.
    tokens = " ".join(line.text for line in lines).split()
    broken = sum(bool(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ]{30,}", token)) for token in tokens)
    return broken >= 2 and broken / max(1, len(tokens)) > 0.02


def table_membership(page, lines: list[TextLine]) -> tuple[list[TextLine], list[str]]:
    """Annotate complete, ruled grids using existing lines, including their exact quotes.

    A grid that cuts through a line, has merged cells, or overlaps another grid is left
    untouched. In particular, text beside a table is never dropped as a horizontal band.
    Coordinates are always in the unrotated frame used by native TextLine.bbox.
    """
    if not lines:
        return lines, []
    rotation = page.rotation
    try:
        page.set_rotation(0)
        paths = page.get_drawings()
        if not paths:
            return lines, []
        # Bound the optional work on CAD/vector-heavy pages; retain the ordinary read.
        if len(paths) > 2000:
            return lines, ["NATIVE_TABLE_LIMIT"]
        tables = page.find_tables(strategy="lines_strict", paths=paths).tables
        assigned = {}
        for index, table in enumerate(tables):
            rows, columns = table.row_count, table.col_count
            if not (2 <= rows <= 100 and 2 <= columns <= 20):
                continue
            cells = [
                (r, c, box) for r, row in enumerate(table.rows) for c, box in enumerate(row.cells)
            ]
            if any(box is None for _, _, box in cells):
                continue
            bounds = pymupdf.Rect(table.bbox)
            members = {}
            for line in lines:
                rect = pymupdf.Rect(line.bbox)
                if not rect.intersects(bounds):
                    continue
                owners = [
                    (r, c)
                    for r, c, box in cells
                    if (pymupdf.Rect(box) + (-1, -1, 1, 1)).contains(rect)
                ]
                if len(owners) != 1 or line.id in assigned:
                    members = {}
                    break
                r, c = owners[0]
                members[line.id] = TablePosition(
                    id=f"p{line.page}:table:{index}",
                    row=r,
                    column=c,
                    rows=rows,
                    columns=columns,
                )
            if len({(p.row, p.column) for p in members.values()}) >= 3:
                assigned.update(members)
        return [
            line.model_copy(update={"table": assigned[line.id]}) if line.id in assigned else line
            for line in lines
        ], []
    except Exception:
        # Layout is optional. A parser failure must not turn a readable PDF into a failure.
        return lines, ["NATIVE_TABLE_UNAVAILABLE"]
    finally:
        page.set_rotation(rotation)


def reading_order(lines: list[TextLine], width: float, depth: int = 0) -> list[TextLine]:
    """Read well-separated prose columns, leaving sparse forms and tables in native order.

    Require several prose lines on BOTH sides and a shared vertical extent. Spanning
    headings/footers stay outside the column band; spanning text inside it vetoes a split.
    Unlike a page-wide word histogram, this also handles short CVs without treating a
    label/value form or a totals block as two independent paragraphs.
    """
    if not 8 <= len(lines) <= 2000 or depth >= 2:
        return lines
    gap = max(18, width * 0.03)
    candidates = sorted({round(line.bbox[0], 1) for line in lines})
    best = None
    for edge in candidates:
        left = [line for line in lines if line.bbox[2] <= edge - gap]
        right = [line for line in lines if line.bbox[0] >= edge - 0.1]
        if min(len(left), len(right)) < 4:
            continue
        if any(
            sum(len(line.text.split()) >= 4 for line in side) < 4
            or sum(len(line.text.split()) for line in side) < 24
            for side in (left, right)
        ):
            continue
        top = max(min(item.bbox[1] for item in left), min(item.bbox[1] for item in right))
        bottom = min(max(item.bbox[3] for item in left), max(item.bbox[3] for item in right))
        if bottom - top < 36:
            continue
        selected = {line.id for line in left + right}
        spanning = [line for line in lines if line.id not in selected]
        if any(line.bbox[3] > top and line.bbox[1] < bottom for line in spanning):
            continue
        band_top = min(item.bbox[1] for item in left + right)
        band_bottom = max(item.bbox[3] for item in left + right)
        if any(line.bbox[3] > band_top and line.bbox[1] < band_bottom for line in spanning):
            continue
        if any(line.table is not None for line in left + right):
            continue
        score = min(len(left), len(right))
        if best is None or score > best[0]:
            best = (score, left, right, spanning, band_top)
    if best is None:
        return lines
    _, left, right, spanning, top = best
    before = [line for line in spanning if line.bbox[3] <= top]
    after = [line for line in spanning if line.bbox[3] > top]
    return (
        before
        + reading_order(left, width, depth + 1)
        + reading_order(right, width, depth + 1)
        + after
    )


def table_cells(lines: list[TextLine]) -> dict:
    tables = defaultdict(lambda: defaultdict(list))
    for line in lines:
        if line.table is not None:
            tables[line.table.id][line.table.row, line.table.column].append(line)
    return dict(tables)


def structured_text(lines: list[TextLine]) -> str:
    """Render tables once, with every cell (including empty cells) in its original column.

    No Markdown header is invented: a plain delimited grid represents data rows as data.
    Lines beside or between tables remain present, and reader streams stay separate in
    the caller. These display delimiters never become extraction candidates.
    """
    tables, emitted, result = table_cells(lines), set(), []
    for line in lines:
        position = line.table
        if position is None:
            result.append(line.text)
        elif position.id not in emitted:
            emitted.add(position.id)
            result.append("[Table; rows in document order]")
            cells = tables[position.id]
            for row in range(position.rows):
                values = []
                for column in range(position.columns):
                    text = " ".join(item.text for item in cells.get((row, column), []))
                    values.append(re.sub(r"\s+", " ", text).replace("|", "\\|"))
                result.append("| " + " | ".join(values) + " |")
            result.append("[End table]")
    return "\n".join(result)
