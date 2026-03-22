from __future__ import annotations

import tempfile
from pathlib import Path
from datetime import datetime
from typing import Any, List, Tuple

from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QFileDialog, QMessageBox


# -------------------------------------------------------
# TEMP PDF PATH (your original function kept)
# -------------------------------------------------------

def get_temp_pdf_path(filename: str) -> Path:
    """Return a writable temp path for a PDF report."""
    safe = (filename or "report").replace("/", "_").replace("\\", "_")
    temp_dir = Path(tempfile.gettempdir()) / "lab_print_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir / f"{safe}.pdf"


# -------------------------------------------------------
# HTML ESCAPE
# -------------------------------------------------------

def _escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# -------------------------------------------------------
# BUILD HTML REPORT (used by Print + PDF)
# -------------------------------------------------------

def build_html_report(
    module_title: str,
    patient: dict[str, Any] | None,
    results: List[Tuple[str, str, str]],
) -> str:
    """
    results format:
    [(category, test_name, result_value), ...]
    """

    patient = patient or {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # group results by category
    by_category: dict[str, list[tuple[str, str]]] = {}

    for cat, test, value in results:
        by_category.setdefault(cat, []).append((test, value))

    html = f"""
    <html>
    <head>
        <meta charset="utf-8"/>
        <style>
            body {{
                font-family: Arial, Helvetica, sans-serif;
                font-size: 12px;
            }}

            h1 {{
                font-size: 18px;
                margin-bottom: 10px;
            }}

            .meta {{
                margin-bottom: 12px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 16px;
            }}

            th, td {{
                border: 1px solid #444;
                padding: 6px;
                text-align: left;
            }}

            th {{
                background: #f0f0f0;
            }}

            .category {{
                font-weight: bold;
                margin-top: 10px;
            }}
        </style>
    </head>

    <body>

        <h1>{_escape(module_title)} Report</h1>

        <div class="meta">
            <div><b>Date:</b> {_escape(now)}</div>
            <div><b>Patient:</b> {_escape(str(patient.get("name", "")))}</div>
            <div><b>Doctor:</b> {_escape(str(patient.get("doctor", "")))}</div>
            <div><b>Gender:</b> {_escape(str(patient.get("gender", "")))}</div>
            <div><b>Age:</b> {_escape(str(patient.get("age", "")))}</div>
        </div>
    """

    for category, items in by_category.items():

        html += f"<div class='category'>{_escape(category)}</div>"
        html += "<table>"
        html += "<tr><th>Test</th><th>Result</th></tr>"

        for test, value in items:
            html += f"""
            <tr>
                <td>{_escape(test)}</td>
                <td>{_escape(value)}</td>
            </tr>
            """

        html += "</table>"

    html += "</body></html>"

    return html


# -------------------------------------------------------
# PRINT TO PRINTER
# -------------------------------------------------------

def print_html(parent, html: str) -> None:
    """Send report to printer."""

    printer = QPrinter(QPrinter.HighResolution)

    dialog = QPrintDialog(printer, parent)
    if dialog.exec() != QPrintDialog.Accepted:
        return

    document = QTextDocument()
    document.setHtml(html)
    document.print_(printer)


# -------------------------------------------------------
# SAVE AS PDF
# -------------------------------------------------------

def save_pdf_html(
    parent,
    html: str,
    default_name: str = "report.pdf",
) -> None:

    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save PDF",
        default_name,
        "PDF Files (*.pdf)",
    )

    if not file_path:
        return

    if not file_path.lower().endswith(".pdf"):
        file_path += ".pdf"

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(file_path)

    document = QTextDocument()
    document.setHtml(html)
    document.print_(printer)

    QMessageBox.information(
        parent,
        "PDF Saved",
        f"PDF saved successfully:\n{file_path}",
    )