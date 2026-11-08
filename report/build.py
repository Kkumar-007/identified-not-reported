"""Build report.docx (styled like the Apart Google Docs template) and report.pdf, then count pages and words.

  python build.py            # from the report/ directory

Template measurements (from the template PDF): US Letter, Old Standard TT, body 11 pt at ~1.15 line spacing,
section headings 14 pt bold, title 20 pt bold centred, left/right margins 0.8 in, top/bottom 1 in.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FONT = "Old Standard TT"


def set_font(style, size: float, bold: bool | None = None, italic: bool | None = None) -> None:
    style.font.name = FONT
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        rfonts.attrib.pop(qn(attr), None)
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic


def make_reference(out: Path) -> None:
    default = subprocess.run(["pandoc", "--print-default-data-file", "reference.docx"],
                             capture_output=True, check=True).stdout
    out.write_bytes(default)
    doc = Document(out)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = Inches(0.8)
    sec.top_margin = sec.bottom_margin = Inches(1.0)
    st = {s.name: s for s in doc.styles}
    for name in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text", "Footnote Text",
                 "Caption", "Table Caption", "Image Caption"):
        if name in st:
            s = st[name]
            set_font(s, 11 if name not in ("Footnote Text", "Caption", "Table Caption", "Image Caption") else 9.5)
            pf = s.paragraph_format
            pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
            pf.line_spacing = 1.15 if name != "Compact" else 1.0
            pf.space_before = Pt(0)
            pf.space_after = Pt(6 if name != "Compact" else 2)
    vc = st["Verbatim Char"]
    vc.font.name = "DejaVu Sans Mono"
    vc.font.size = Pt(7.5)
    for name, size in (("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 11)):
        s = st[name]
        set_font(s, size, bold=True, italic=False)
        s.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
        s.paragraph_format.space_after = Pt(4)
        s.paragraph_format.keep_with_next = True
    t = st["Title"]
    set_font(t, 20, bold=True)
    t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.paragraph_format.space_after = Pt(14)
    # Remove the theme border/colour pandoc's Title carries.
    ppr = t.element.get_or_add_pPr()
    for b in ppr.findall(qn("w:pBdr")):
        ppr.remove(b)
    a = st["Author"]
    set_font(a, 11)
    a.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for name in ("Image Caption", "Caption"):
        if name in st:
            st[name].font.italic = False
    doc.save(out)


def post_process(docx: Path) -> None:
    """Centre the abstract heading, indent the abstract, shade code blocks lightly, tighten tables."""
    doc = Document(docx)
    paras = doc.paragraphs
    for i, p in enumerate(paras):
        if p.style.name.startswith("Heading") and p.text.strip() == "Abstract":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            j = i + 1
            while j < len(paras) and not paras[j].style.name.startswith("Heading"):
                paras[j].paragraph_format.left_indent = Inches(1.0)
                paras[j].paragraph_format.right_indent = Inches(1.0)
                paras[j].alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                j += 1
    for p in doc.paragraphs:
        if p.text.startswith("Table ") and p.runs and p.runs[0].bold:
            p.paragraph_format.keep_with_next = True
        if p.style.name == "Source Code":
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(4)
    for tbl in doc.tables:
        for k, row in enumerate(tbl.rows):
            trpr = row._tr.get_or_add_trPr()
            trpr.append(trpr.makeelement(qn("w:cantSplit"), {}))
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = k < len(tbl.rows) - 1
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(1)
                    p.paragraph_format.line_spacing = 1.0
                    for r in p.runs:
                        r.font.size = Pt(9.5)
                        r.font.name = FONT
    doc.save(docx)


def main() -> None:
    ref = HERE / "reference.docx"
    make_reference(ref)
    docx = HERE / "report.docx"
    subprocess.run(["pandoc", "report.md", "-f", "markdown+pipe_tables+fenced_divs+raw_attribute-tex_math_dollars",
                    "-o", str(docx), "--reference-doc", str(ref), "--number-sections",
                    "--resource-path", str(HERE)], cwd=HERE, check=True)
    post_process(docx)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(HERE), str(docx)],
                   check=True, capture_output=True)
    print("built", docx.name, "report.pdf")


if __name__ == "__main__":
    main()
