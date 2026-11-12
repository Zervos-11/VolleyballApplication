"""Render the honours evidence handoff to shareable HTML for PDF printing."""

from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "DELIVERABLES/HONOURS_SHAREABLE_RESEARCH_HANDOFF_2026-11-11.md"
OUTPUT = ROOT / "DELIVERABLES/HONOURS_SHAREABLE_RESEARCH_HANDOFF_2026-11-11.html"


def main() -> None:
    md = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable("table")
    body = md.render(SOURCE.read_text(encoding="utf-8"))
    css = """
    @page{size:A4;margin:18mm 18mm 18mm 20mm}
    body{font:10pt/1.48 Georgia,'Times New Roman',serif;color:#17232d;max-width:780px;margin:0 auto}
    h1,h2,h3{font-family:Arial,sans-serif;line-height:1.24;break-after:avoid}
    h1{font-size:19pt;margin:0 0 7mm}h2{font-size:14pt;margin:8mm 0 3mm}h3{font-size:11pt}
    p{margin:0 0 3mm;orphans:3;widows:3}a{color:#165778;text-decoration:none}
    table{border-collapse:collapse;width:100%;font-size:8.4pt;margin:4mm 0;break-inside:avoid}
    th,td{border:1px solid #aab8c1;padding:1.5mm 1.9mm;vertical-align:top}
    th{background:#e7eef3}tr{break-inside:avoid}
    img{display:block;max-width:100%;max-height:165mm;margin:4mm auto;object-fit:contain}
    code{font-size:8.5pt;overflow-wrap:anywhere}li{margin:1mm 0}
    @media print{body{max-width:none}a{color:#17232d}}
    """
    OUTPUT.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Volleyball analytics research handoff</title><style>'
                      + css + '</style></head><body>' + body + '</body></html>', encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
