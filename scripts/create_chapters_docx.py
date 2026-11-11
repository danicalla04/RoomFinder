"""Build the editable Chapters 1 and 3 Word file using Python's standard library."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "CHAPTERS_1_AND_3.md"
OUTPUT = ROOT / "docs" / "RoomFinder_Chapters_1_and_3.docx"


def paragraph(content: str, style: str, page_break: bool = False) -> str:
    properties = f'<w:pStyle w:val="{style}"/>'
    if page_break:
        properties += '<w:pageBreakBefore/>'
    text = escape(content)
    return (
        f'<w:p><w:pPr>{properties}</w:pPr><w:r><w:t xml:space="preserve">'
        f"{text}</w:t></w:r></w:p>"
    )


def document_xml(lines: list[str]) -> str:
    blocks: list[str] = []
    first_chapter = True
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            title = line[2:]
            if title.startswith("CHAPTER "):
                blocks.append(paragraph(title, "Chapter", page_break=not first_chapter))
                first_chapter = False
            else:
                blocks.append(paragraph(title, "Title"))
        elif line.startswith("## "):
            blocks.append(paragraph(line[3:], "Heading1"))
        elif line.startswith("### "):
            blocks.append(paragraph(line[4:], "Heading2"))
        elif re.match(r"^\d+\. ", line):
            blocks.append(paragraph(line, "List"))
        elif line.startswith("Draft Chapters "):
            blocks.append(paragraph(line, "Note"))
        else:
            blocks.append(paragraph(line, "Body"))

    body = "".join(blocks)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{body}<w:sectPr>'
        '<w:footerReference w:type="default" r:id="rId2" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1800" '
        'w:header="720" w:footer="720" w:gutter="0"/>'
        '</w:sectPr></w:body></w:document>'
    )


def styles_xml() -> str:
    def style(name: str, style_id: str, ppr: str = "", rpr: str = "") -> str:
        return (
            f'<w:style w:type="paragraph" w:styleId="{style_id}">'
            f'<w:name w:val="{name}"/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr>'
            '</w:style>'
        )

    font = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
    base = font + '<w:sz w:val="24"/>'
    body = '<w:jc w:val="both"/><w:spacing w:line="360" w:lineRule="auto" w:after="120"/>'
    headings = '<w:keepNext/><w:spacing w:before="240" w:after="120" w:line="300"/>'
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults><w:rPrDefault><w:rPr>' + base + '</w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/>'
        '</w:pPr></w:pPrDefault></w:docDefaults>'
        + style("Body Text", "Body", body, base)
        + style("Title", "Title", '<w:jc w:val="center"/><w:spacing w:after="240"/>',
                font + '<w:b/><w:sz w:val="28"/>')
        + style("Chapter", "Chapter", '<w:jc w:val="center"/><w:spacing w:before="240" w:after="300"/>',
                font + '<w:b/><w:sz w:val="28"/>')
        + style("Heading 1", "Heading1", headings, base + '<w:b/>')
        + style("Heading 2", "Heading2", headings, base + '<w:b/><w:i/>')
        + style("List", "List", body + '<w:ind w:left="540" w:hanging="360"/>', base)
        + style("Note", "Note", '<w:spacing w:after="240"/>',
                font + '<w:i/><w:color w:val="555555"/><w:sz w:val="20"/>')
        + '</w:styles>'
    )


def footer_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:t>RoomFinder — Chapters 1 and 3  |  Page </w:t></w:r>'
        '<w:fldSimple w:instr="PAGE"/></w:p></w:ftr>'
    )


def main() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>'
        ),
        "word/_rels/document.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
            '</Relationships>'
        ),
        "docProps/core.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>RoomFinder: Chapters 1 and 3</dc:title>'
            '<dc:creator>RoomFinder project draft</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
            '</cp:coreProperties>'
        ),
        "word/document.xml": document_xml(lines),
        "word/styles.xml": styles_xml(),
        "word/footer1.xml": footer_xml(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content.encode("utf-8"))
    print(OUTPUT)


if __name__ == "__main__":
    main()
