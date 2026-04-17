# app/ui_utils.py
from __future__ import annotations
from .branding import LAB_BRANDING
import os
import shutil
import uuid
import win32api
import win32print
from pathlib import Path
from datetime import datetime
from typing import Union, Optional


from PySide6.QtGui import QRegion
from PySide6.QtCore import QRect

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display


from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

from .db import get_conn, get_lab_setting




from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QPushButton,
    QFileDialog,
    QWidget,
    QHBoxLayout,
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from .printing import get_temp_pdf_path
from reportlab.lib import colors


WidgetValue = Union[QLineEdit, QComboBox]






def apply_global_theme(app, dark: bool = False):
    app.setStyle("Fusion")

    
    app.setStyleSheet("""
            QWidget {
                font-family: "Cairo";
                font-size: 13px;
                color: #16324f;
                background-color: #e9eef5;
            }

            QMainWindow {
                background-color: #e9eef5;
            }

            QFrame#AppShell {
                background-color: transparent;
                border: 1px solid #dfe6ef;
                border-radius: 20px;
            }

            QFrame#HeaderBar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ffffff,
                    stop:1 #f6fbff
                );
                border: 1px solid #dbe6f2;
                border-radius: 18px;
            }

            QLabel#BrandTitle {
                font-size: 22px;
                font-weight: 800;
                color: #12385c;
                background: transparent;
            }

            QLabel#BrandSubtitle {
                font-size: 13px;
                font-weight: 800;
                color: #4f6f8f;
                background: transparent;
            }

            QToolButton#HeaderIconButton {
                background: #ffffff;
                border: 1px solid #cfd9e6;
                border-radius: 18px;
                padding: 6px 12px;
                font-size: 16px;
                font-weight: 700;
                color: #16324f;
                min-width: 30px;
                min-height: 30px;
            }

            QToolButton#HeaderIconButton:hover {
                background: #eef5ff;
                border: 1px solid #7aaef0;
            }

            QToolButton#HeaderIconButton:pressed {
                background: #dfeeff;
                border: 1px solid #5f98e6;
            }

            QMenu {
                background: #ffffff;
                border: 1px solid #dbe4f0;
                border-radius: 12px;
                padding: 8px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 8px;
            }

            QMenu::item:selected {
                background: #eef5ff;
            }

            QGroupBox {
                font-weight: 700;
                border: 1px solid #e6ebf2;
                border-radius: 16px;
                margin-top: 12px;
                padding-top: 12px;
                background: #ffffff;
                padding: 12px;
            }

            QGroupBox#TestColumnCard {
                background: #ffffff;
                border: 1px solid #e8eef6;
                border-radius: 18px;
                padding: 10px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background: transparent;
            }

            QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit {
                border: 1px solid #d9e2ec;
                border-radius: 10px;
                padding: 8px 10px;
                background: #ffffff;
                color: #0f172a;
                font-weight: 600;
                min-height: 34px;
            }

            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
                border: 1px solid #3a7afe;
                background: #ffffff;          
            }

            QPushButton {
                background-color: #3a7afe;
                color: white;
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 700;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #2f66d4;
            }

            QPushButton:pressed {
                background-color: #254fa5;
            }

            QTableWidget {
                border: 1px solid #d8dbe2;
                border-radius: 12px;
                gridline-color: #e4e6ec;
                background: #ffffff;
                font-size: 14px;
            }


            QTableWidget::item:selected {
                background-color: #e8f2ff;
                color: #16324f;
            }

            QTableWidget::item:selected:active {
                background-color: #e8f2ff;
                color: #16324f;
            }

            QHeaderView::section {
                background: #eef1f7;
                padding: 8px;
                border: none;
                font-weight: bold;
            }

            QTabWidget::pane {
                border: 1px solid #e1e8f1;
                border-radius: 14px;
                background: #ffffff;
                top: -1px;
            }

            QTabBar::tab {
                background: #f4f7fb;
                border: 1px solid #dfe7f1;
                border-bottom: none;
                padding: 10px 18px;
                margin-left: 4px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: 800;
                min-width: 110px;
            }

            QTabBar::tab:selected {
                background: #ffffff;
                color: #16324f;
            }

            QTabBar::tab:hover:!selected {
                background: #eef5ff;
            }

            /* Modern Scrollbar */

            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 6px 0 6px 0;
            }

            QScrollBar::handle:vertical {
                background: #c6d3e1;
                border-radius: 5px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background: #8fb4e8;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 0 6px 0 6px;
            }

            QScrollBar::handle:horizontal {
                background: #c6d3e1;
                border-radius: 5px;
                min-width: 30px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #8fb4e8;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }
            """)


        




# ----------------------------
# Small UI helpers
# ----------------------------

def make_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    lbl.setStyleSheet("""
        QLabel {
            font-size: 14px;
            font-weight: 700;
            color: #16324f;
            background: transparent;
            padding: 0px;
        }
    """)
    return lbl




def fit_window_to_screen(
    window,
    *,
    width_ratio: float = 0.92,
    height_ratio: float = 0.9,
    min_width: int = 1000,
    min_height: int = 650,
) -> None:
    app = QApplication.instance()
    if app is None:
        window.resize(min_width, min_height)
        return

    screen = app.primaryScreen()
    if screen is None:
        window.resize(min_width, min_height)
        return

    available = screen.availableGeometry()

    target_width = max(min_width, int(available.width() * width_ratio))
    target_height = max(min_height, int(available.height() * height_ratio))

    # Never exceed available screen size
    target_width = min(target_width, available.width())
    target_height = min(target_height, available.height())

    window.resize(target_width, target_height)

    # Center the window on screen
    frame = window.frameGeometry()
    frame.moveCenter(available.center())
    window.move(frame.topLeft())



def show_blocking_child(parent: QWidget | None, child: QWidget) -> QWidget:
    """
    Show a child window as a blocking modal window.

    Result:
    - user cannot go back to older windows until this one is closed
    - if parent closes, child closes too
    - child is deleted automatically when closed
    """
    if parent is not None:
        child.setParent(parent, child.windowFlags())

    child.setAttribute(Qt.WA_DeleteOnClose, True)
    child.setWindowModality(Qt.ApplicationModal)
    child.show()
    child.raise_()
    child.activateWindow()
    return child





def widget_set_value(w: WidgetValue, value: str) -> None:
    value = (value or "").strip()
    if isinstance(w, QLineEdit):
        w.setText(value)
        return
    if isinstance(w, QComboBox):
        idx = w.findText(value)
        if idx >= 0:
            w.setCurrentIndex(idx)
        else:
            w.setEditText(value)


def _safe_filename(name: str) -> str:
    raw = (name or "").strip()
    raw = " ".join(raw.split())
    return "".join(ch if ch.isalnum() or ch in " _-." else "_" for ch in raw)



def _pdf_tests_folder() -> Path:
    desktop = Path.home() / "Desktop"
    folder = desktop / "PDF Tests"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _build_unique_pdf_path(folder: Path, base_name: str) -> Path:
    safe_base = _safe_filename(base_name) or "patient"
    if safe_base.lower().endswith(".pdf"):
        safe_base = safe_base[:-4]

    candidate = folder / f"{safe_base}.pdf"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = folder / f"{safe_base} ({index}).pdf"
        if not candidate.exists():
            return candidate
        index += 1


def save_pdf_automatically(
    parent: Optional[QWidget],
    temp_pdf_path: Path,
    *,
    patient_name: str,
) -> Optional[Path]:
    """
    Automatically save the PDF into Desktop/PDF Tests using patient name.
    Keeps both files if the same name already exists.
    """
    try:
        folder = _pdf_tests_folder()
        out_path = _build_unique_pdf_path(folder, patient_name)

        shutil.copyfile(str(temp_pdf_path), str(out_path))

        try:
            temp_pdf_path.unlink(missing_ok=True)
        except Exception:
            pass

        return out_path
    except Exception as e:
        QMessageBox.warning(parent, "Save Error", f"Failed to save PDF:\n{e}")
        return None


# ----------------------------
# Printing + PDF save helpers
# ----------------------------

def print_pdf(pdf_path: Path) -> None:
    """
    Print a PDF on Windows.
    First tries the default PDF handler with 'print'.
    If that fails, falls back to opening the PDF.
    """
    try:
        # Create a safe ASCII copy because some Windows print handlers fail on Unicode paths
        safe_dir = pdf_path.parent
        safe_name = f"print_job_{uuid.uuid4().hex}.pdf"
        safe_pdf = safe_dir / safe_name
        shutil.copyfile(str(pdf_path), str(safe_pdf))

        try:
            # More compatible than "printto" on many Windows setups
            win32api.ShellExecute(
                0,
                "print",
                str(safe_pdf),
                None,
                ".",
                0,
            )
            return
        except Exception:
            # fallback: open the PDF if print verb is unsupported
            win32api.ShellExecute(
                0,
                "open",
                str(safe_pdf),
                None,
                ".",
                1,
            )

    except Exception as e:
        QMessageBox.warning(None, "Print Error", f"Failed to print:\n{e}")


def print_pdf_and_delete(pdf_path: Path, *, delay_s: float = 4.0, retries: int = 16) -> None:
    """Print then attempt to delete the original temp file safely."""
    print_pdf(pdf_path)
    try:
        import time

        time.sleep(max(0.0, delay_s))
        for _ in range(max(1, retries)):
            try:
                pdf_path.unlink(missing_ok=True)
                return
            except PermissionError:
                time.sleep(0.5)
    except Exception as e:
        try:
            QMessageBox.warning(None, "Cleanup Warning", f"Printed, but failed to delete temp PDF:\n{e}")
        except Exception:
            pass


def save_pdf_via_dialog(
    parent: Optional[QWidget],
    temp_pdf_path: Path,
    *,
    suggested_name: str = "report.pdf",
) -> Optional[Path]:
    """
    Let user choose where to save a PDF (no printing).
    Copies temp_pdf_path to user-chosen location, then deletes temp.
    """
    try:
        suggested_name = _safe_filename(suggested_name) or "report.pdf"
        if not suggested_name.lower().endswith(".pdf"):
            suggested_name += ".pdf"

        out_path_str, _ = QFileDialog.getSaveFileName(
            parent,
            "Save PDF",
            suggested_name,
            "PDF Files (*.pdf)",
        )
        if not out_path_str:
            return None

        out_path = Path(out_path_str)
        if out_path.suffix.lower() != ".pdf":
            out_path = out_path.with_suffix(".pdf")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(temp_pdf_path), str(out_path))

        # best-effort cleanup
        try:
            temp_pdf_path.unlink(missing_ok=True)
        except Exception:
            pass

        return out_path
    except Exception as e:
        QMessageBox.warning(parent, "Save Error", f"Failed to save PDF:\n{e}")
        return None


# ----------------------------
# Report PDF generation
# ----------------------------

def _patient_field(patient, attr: str, default: str = "-") -> str:
    v = getattr(patient, attr, None)
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def _draw_standard_footer(c: canvas.Canvas, left_x: float, right_x: float) -> None:
    c.setFont("Helvetica", 9)
    c.line(left_x, 2.2 * cm, right_x, 2.2 * cm)
    c.drawString(left_x, 1.6 * cm, "Generated by Lab Desktop App")
    c.drawRightString(right_x, 1.6 * cm, datetime.now().strftime("%Y-%m-%d %H:%M"))



def format_range_number(x):
    try:
        x = float(x)
        if x.is_integer():
            return str(int(x))
        return str(x)
    except Exception:
        return str(x)



def _lab_logo_path() -> Path:
    return Path(LAB_BRANDING["logo_path"])


def _footer_qr_image_path() -> Path:
    return Path(LAB_BRANDING["footer_qr_path"])

def _get_print_settings() -> dict[str, str]:
    with get_conn() as conn:
        footer_text = get_lab_setting(conn, "footer_text", "")
        lab_phone = get_lab_setting(conn, "lab_phone", "")
        whatsapp_number = get_lab_setting(conn, "whatsapp_number", "")
    return {
        "footer_text": footer_text,
        "lab_phone": lab_phone,
        "whatsapp_number": whatsapp_number,
    }


def _clean_whatsapp_number(number: str) -> str:
    raw = "".join(ch for ch in (number or "") if ch.isdigit())
    if raw.startswith("00"):
        raw = raw[2:]
    if raw.startswith("0"):
        # Iraqi local number to international example:
        # 07725017776 -> 9647725017776
        raw = "964" + raw[1:]
    return raw


def _draw_whatsapp_qr(c: canvas.Canvas, x: float, y: float, size: float, phone_number: str) -> None:
    wa_number = _clean_whatsapp_number(phone_number)
    if not wa_number:
        return

    wa_link = f"https://wa.me/{wa_number}"
    qr_code = qr.QrCodeWidget(wa_link)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]

    drawing = Drawing(size, size, transform=[size / width, 0, 0, size / height, 0, 0])
    drawing.add(qr_code)
    renderPDF.draw(drawing, c, x, y)






def _draw_lab_header(c: canvas.Canvas, patient, report_id: str, width: float, height: float) -> float:
    LEFT_X = 2.0 * cm
    RIGHT_X = width - 2.0 * cm
    CENTER_X = width / 2

    arabic_font = _ensure_arabic_font_registered()
    english_font = _ensure_english_header_font_registered()

    # -------------------------
    # Left side English
    # -------------------------
    # English header (left)
    c.setFillColorRGB(0.0, 0.35, 0.75)  # blue
    c.setFont(english_font, 28)
    c.drawString(
        LEFT_X + 0.4 * cm,
        height - 1.95 * cm,
        LAB_BRANDING["pdf_header_en_line1"],
    )

    c.setFont(english_font, 16)
    c.drawString(
        LEFT_X + 0.7 * cm,
        height - 2.90 * cm,
        LAB_BRANDING["pdf_header_en_line2"],
    )


    # -------------------------
    # Center logo (bigger and truly centered)
    # -------------------------
    # Center logo
    logo_path = _lab_logo_path()
    if logo_path.exists():
        try:
            c.drawImage(
                ImageReader(str(logo_path)),
                CENTER_X - 3.6 * cm,
                height - 5.8 * cm,   # lower than before
                width=7.6 * cm,       # bigger
                height=7.6 * cm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    # -------------------------
    # Right side Arabic
    # -------------------------
    # Arabic header (right)
    c.setFillColorRGB(0.85, 0.0, 0.55)

    # move slightly upward
    c.setFont(arabic_font, 17)
    c.drawRightString(RIGHT_X - 0.2 * cm, height - 1.30 * cm, _ar(LAB_BRANDING["pdf_header_ar_line1"]))

    # make this the dominant line
    c.setFont(arabic_font, 28)
    c.drawRightString(RIGHT_X - 0.2 * cm, height - 2.35 * cm, _ar(LAB_BRANDING["pdf_header_ar_line2"]))

    # keep bottom line separated
    c.setFillColorRGB(0.0, 0.0, 0.35)
    c.setFont(arabic_font, 14)
    c.drawRightString(RIGHT_X - 0.2 * cm, height - 3.35 * cm, _ar(LAB_BRANDING["pdf_header_ar_line3"]))


    # -------------------------
    # Centered patient info box
    # -------------------------
    box_w = width - 4.8 * cm
    box_h = 2.8 * cm
    box_x = (width - box_w) / 2
    box_y = height - 6.45 * cm

    c.setLineWidth(1.3)
    c.setStrokeColorRGB(0.0, 0.2, 0.55)
    c.roundRect(box_x, box_y, box_w, box_h, 0.35 * cm)

    name = _patient_field(patient, "name", "-")
    doctor = _patient_field(patient, "doctor", "-")
    gender = _patient_field(patient, "gender", "-")
    age = _patient_field(patient, "age", "-")
    date_iso = _patient_field(patient, "date_iso", "-")

    c.setFillColorRGB(0.0, 0.0, 0.2)

    # Arabic labels and values
    c.setFillColorRGB(0.0, 0.0, 0.2)
    c.setFont(arabic_font, 12)

    label_x = box_x + box_w - 0.6 * cm
    value_x = box_x + box_w - 4.2 * cm

    # Row 1: name + gender
    c.drawRightString(label_x, box_y + 1.95 * cm, _ar("الاسم :"))
    c.drawRightString(value_x, box_y + 1.95 * cm, _ar(name))

    c.drawRightString(box_x + box_w - 9.5 * cm, box_y + 1.95 * cm, _ar("الجنس :"))
    c.drawRightString(box_x + box_w - 12.0 * cm, box_y + 1.95 * cm, _ar(gender))


    # Row 2: doctor + age
    c.drawRightString(label_x, box_y + 1.15 * cm, _ar("اسم الطبيب :"))
    c.drawRightString(value_x, box_y + 1.15 * cm, _ar(doctor))

    c.drawRightString(box_x + box_w - 9.5 * cm, box_y + 1.15 * cm, _ar("العمر :"))
    c.drawRightString(box_x + box_w - 12.0 * cm, box_y + 1.15 * cm, _ar(str(age)))


    # Row 3: date alone
    c.drawRightString(label_x, box_y + 0.35 * cm, _ar("التاريخ :"))
    c.drawRightString(value_x, box_y + 0.35 * cm, _ar(date_iso))

    return box_y - 1.0 * cm


def _split_phone_footer_text(phone_text: str) -> tuple[str, str]:
    text = str(phone_text or "").strip()
    if not text:
        return "", ""

    # If user typed something like:
    # "رقم الهاتف للتواصل : 07725017776"
    # split label from number
    parts = text.split(":")
    if len(parts) >= 2:
        label = ":".join(parts[:-1]).strip()
        value = parts[-1].strip()
        return label, value

    # If no colon, treat full text as value only
    return "", text



def _draw_lab_footer(
    c: canvas.Canvas,
    width: float,
    settings: dict[str, str],
    footer_text_override: str = "",
) -> None:
    LEFT_X = 0.05 * cm
    RIGHT_X = width - 0.5 * cm

    # Layout zones
    qr_x = -2.0 * cm
    qr_y = -2.5 * cm
    qr_w = 8.0 * cm
    qr_h = 8.0 * cm

    text_left = 5.5 * cm
    text_right = width - 1.2 * cm
    text_center = (text_left + text_right) / 2


    # Blue line across whole footer width, including QR area
    c.setStrokeColorRGB(0.0, 0.15, 0.45)
    c.setLineWidth(1.0)





    # Draw QR card image on the LEFT
    qr_img_path = _footer_qr_image_path()
    if qr_img_path.exists():
        try:
            c.drawImage(
                ImageReader(str(qr_img_path)),
                qr_x,
                qr_y,
                width=qr_w,
                height=qr_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    c.line(0.8 * cm, 2.35 * cm, width - 0.8 * cm, 2.35 * cm)


  
    # Footer text block on the RIGHT
    c.setFillColorRGB(0.45, 0.0, 0.0)
    arabic_font = _ensure_arabic_font_registered()
    c.setFont(arabic_font, 11)

    footer_text = (footer_text_override or "").strip()
    if not footer_text:
        footer_text = settings.get("footer_text", "").strip()

    lab_phone = settings.get("lab_phone", "").strip()
    phone_label, phone_value = _split_phone_footer_text(lab_phone)

    y_main = 1.95 * cm
    y_second = 1.55 * cm
    y_phone = 1.12 * cm

    def draw_phone_line(y_pos: float):
        if not lab_phone:
            return

        y_pos = y_pos - 0.10 * cm

        if phone_label:
            # Arabic label on the right side of the text zone
            c.setFont(arabic_font, 11)
            c.drawRightString(text_center + 2.2 * cm, y_pos, _ar(phone_label + " :"))

            # Number to the left of the Arabic label
            c.setFont("Helvetica-Bold", 11)
            c.drawRightString(text_center - 0.6 * cm, y_pos, phone_value)

            c.setFont(arabic_font, 11)
        else:
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(text_center, y_pos, phone_value)
            c.setFont(arabic_font, 11)

    if footer_text:
        shaped_footer = _ar(footer_text)
        max_len = 62
        line1 = shaped_footer[:max_len]
        line2 = shaped_footer[max_len:max_len * 2].strip()

        c.drawCentredString(text_center, y_main, line1)
        if line2:
            c.drawCentredString(text_center, y_second, line2)
            draw_phone_line(y_phone)
        else:
            draw_phone_line(y_second)
    else:
        draw_phone_line(y_main)



def _arabic_font_path() -> Path:
    amiri_path = Path(__file__).resolve().parent / "assets" / "Amiri-Bold.ttf"
    if amiri_path.exists():
        return amiri_path
    return Path(__file__).resolve().parent / "assets" / "NotoNaskhArabic-Regular.ttf"

def _english_header_font_path() -> Path:
    return Path("C:/Windows/Fonts/timesbd.ttf")

def _ensure_arabic_font_registered() -> str:
    font_name = "ArabicLabFont"
    try:
        pdfmetrics.getFont(font_name)
        return font_name
    except Exception:
        pass

    font_path = _arabic_font_path()
    if font_path.exists():
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
        return font_name

    return "Helvetica"


def _ensure_english_header_font_registered() -> str:
    font_name = "EnglishHeaderFont"
    try:
        pdfmetrics.getFont(font_name)
        return font_name
    except Exception:
        pass

    font_path = _english_header_font_path()
    if font_path.exists():
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
        except Exception:
            return "Helvetica-Bold"

    return "Helvetica-Bold"


def _ar(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def make_pdf_report(
    patient,
    report_id: str,
    grouped_results: dict[str, list[dict]],
    footer_text: str = "",
    flag_header: str = "Flag",
) -> Path:
    date_iso = _patient_field(patient, "date_iso", "date")

    filename = f"report_{date_iso}_{report_id[:8]}.pdf"
    out_path = get_temp_pdf_path(_safe_filename(filename))

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    LEFT_X = 2.0 * cm
    RIGHT_X = width - 2.0 * cm

    X_TEST = LEFT_X
    X_RESULT = 9.0 * cm
    X_FLAG = 11.8 * cm
    X_RANGE = RIGHT_X

    settings = _get_print_settings()
    arabic_font = _ensure_arabic_font_registered()

    sfa_categories = {
        "physical examination",
        "microscopical examination",
        "motility",
    }
    report_categories = {str(k).strip().lower() for k in grouped_results.keys()}
    is_sfa_report = report_categories == sfa_categories

    def draw_header() -> float:
        return _draw_lab_header(c, patient, report_id, width, height)

    def draw_table_header(y: float) -> float:
        if is_sfa_report:
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 13)
            c.drawCentredString(width / 2, y, "Seminal Fluid Analysis")
            y -= 0.75 * cm
            c.setFont("Helvetica", 10)
            return y

        c.setFont("Helvetica-Bold", 11)
        c.drawString(X_TEST, y, "Test")
        c.drawString(X_RESULT, y, "Result")
        c.drawRightString(X_RANGE, y, "Normal Range")

        y -= 0.55 * cm
        c.setStrokeColorRGB(0.0, 0.2, 0.55)
        c.setLineWidth(1.0)
        c.line(LEFT_X, y, RIGHT_X, y)
        c.setStrokeColorRGB(0, 0, 0)

        y -= 0.45 * cm
        c.setFont("Helvetica", 10)
        return y

    def new_page() -> float:
        _draw_lab_footer(c, width, settings, footer_text)
        c.showPage()
        return draw_table_header(draw_header())

    def has_value(x) -> bool:
        return x is not None and str(x).strip() != ""

    def has_arabic(text: str) -> bool:
        return any("\u0600" <= ch <= "\u06FF" for ch in str(text or ""))

    def estimate_category_height(category: str, rows: list[dict]) -> float:
        """
        Estimate how much vertical space one whole category needs,
        so we can decide whether to move it to a new page before printing it.
        """
        total = 0.0

        # space before category title and title block
        total += 0.15 * cm
        total += 0.32 * cm
        total += 0.45 * cm
        total += 0.22 * cm
        total += 0.55 * cm

        # each row
        for r in rows:
            ranges = r.get("ranges", []) or []
            if not ranges:
                range_count = 1
            else:
                range_count = max(1, len(ranges))

            # first line of row
            row_height = 0.62 * cm

            # extra lines if multiple ranges are printed
            if range_count > 1:
                row_height += (range_count - 1) * 0.40 * cm

            # extra spacing for TORCH grouped rows
            if str(category).upper() == "TORCH" and str(r.get("test_name", "") or "") in {
                "CMV IgM-Ab",
                "HSV I -IgM- Ab",
                "HSV II -IgM- Ab",
                "Rubella IgM-Ab",
            }:
                row_height += 0.42 * cm

            total += row_height

        # bottom category line + spacing after category
        total += 0.35 * cm
        total += 0.35 * cm

        return total



    def format_one_range(row: dict) -> tuple[str, str]:
        label = str(row.get("label", "") or "").strip()
        mn = row.get("min", "")
        mx = row.get("max", "")
        normal_text = str(row.get("normal_text", "") or "").strip()

        if normal_text:
            range_txt = normal_text
        else:
            mn_txt = format_range_number(mn) if has_value(mn) else ""
            mx_txt = format_range_number(mx) if has_value(mx) else ""

            if mn_txt and mx_txt:
                range_txt = f"({mn_txt}–{mx_txt})"
            elif mn_txt:
                range_txt = f"> {mn_txt}"
            elif mx_txt:
                range_txt = f"< {mx_txt}"
            else:
                range_txt = ""

        return label, range_txt

    y = draw_header()
    y = draw_table_header(y)

    category_order = list(grouped_results.keys())

    if is_sfa_report:
        preferred_sfa_order = [
            "physical Examination",
            "Microscopical Examination",
            "Motility",
        ]
        remaining_categories = [c for c in category_order if c not in preferred_sfa_order]
        category_order = [c for c in preferred_sfa_order if c in grouped_results] + remaining_categories

    if "Culture" in category_order and "Antibiotics" in category_order:
        category_order = [c for c in category_order if c not in {"Culture", "Antibiotics"}]
        category_order = ["Culture", "Antibiotics"] + category_order

    for category in category_order:
        rows = grouped_results.get(category, [])

        needed_height = estimate_category_height(category, rows)

        # if the whole category cannot fit, move it to a fresh page
        if y - needed_height < 4.8 * cm:
            y = new_page()

        y -= 0.15 * cm

        # Special local header only for Titers category inside Tests module
        if str(category).strip().lower() == "titers":
            c.setFont("Helvetica-Bold", 11)
            c.setFillColorRGB(0.0, 0.2, 0.55)
            c.drawString(X_TEST, y, "Test")
            c.drawString(X_RESULT, y, "Result")
            c.drawString(X_FLAG, y, "Titer")
            c.drawRightString(X_RANGE, y, "Normal Range")

            y -= 0.45 * cm
            c.setStrokeColorRGB(0.0, 0.2, 0.55)
            c.setLineWidth(1.0)
            c.line(LEFT_X, y, RIGHT_X, y)
            c.setStrokeColorRGB(0, 0, 0)

            y -= 0.55 * cm

        y -= 0.32 * cm
        c.setFillColorRGB(0.85, 0.20, 0.20)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(LEFT_X, y, str(category).upper())

        # extra space after module title
        y -= 0.45 * cm

        y -= 0.22 * cm
        c.setStrokeColorRGB(0.80, 0.00, 0.00)
        c.setLineWidth(1.2)
        c.line(LEFT_X, y, RIGHT_X, y)
        c.setStrokeColorRGB(0, 0, 0)

        y -= 0.55 * cm

        for r in rows:

            test = str(r.get("test_name", "") or "")
            result = str(r.get("result", "") or "")
            unit = str(r.get("unit", "") or "").strip()
            flag = str(r.get("flag", "") or "").strip()
            titer = str(r.get("titer", "") or "").strip()

            if str(category).strip().lower() == "titers":
                result_display = result
            else:
                result_display = f"{result} {unit}".strip() if unit else result

            ranges = r.get("ranges", []) or []
            matched = r.get("matched_range")

            range_lines: list[tuple[str, str, bool]] = []
            for row in ranges:
                label_txt, value_txt = format_one_range(row)
                range_lines.append((label_txt, value_txt, row == matched))

            if not range_lines:
                range_lines = [("", "", False)]

            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(X_TEST, y, test[:45])

            if flag == "H":
                c.setFillColorRGB(0.75, 0.0, 0.12)
            elif flag == "L":
                c.setFillColorRGB(0.04, 0.34, 0.82)
            elif flag == "N":
                c.setFillColorRGB(0.00, 0.55, 0.20)
            else:
                c.setFillColorRGB(0, 0, 0)

            c.setFont("Helvetica-Bold", 11)
            c.drawString(X_RESULT, y, result_display[:22])

            c.setFont("Helvetica-Bold", 11)

            if str(category).strip().lower() == "titers":
                titer_unit = str(r.get("unit", "") or "").strip()

                titer_display = titer
                if titer and titer_unit:
                    titer_display = f"{titer} {titer_unit}"

                if titer_display and flag:
                    third_col_value = f"{titer_display} {flag}"
                else:
                    third_col_value = titer_display or flag
            else:
                third_col_value = flag

            c.drawString(X_FLAG, y, third_col_value)

            first = True

            for label_txt, value_txt, is_match in range_lines:
                if first:
                    ry = y
                    first = False
                else:
                    ry = y - 0.40 * cm
                    y = ry

                if is_match:
                    if flag == "H":
                        c.setFillColorRGB(0.80, 0.15, 0.15)   # red
                    elif flag == "L":
                        c.setFillColorRGB(0.04, 0.34, 0.82)   # blue
                    else:
                        c.setFillColorRGB(0.00, 0.55, 0.20)   # green
                else:
                    c.setFillColorRGB(0, 0, 0)

                if is_match:
                    range_font_name = "Helvetica-Bold"
                    range_font_size = 12
                else:
                    range_font_name = "Helvetica"
                    range_font_size = 10

                # draw numeric/text range value at the far right
                c.setFont(range_font_name, range_font_size)
                c.drawRightString(X_RANGE, ry, value_txt[:24])

                # draw label separately to the left of the value
                if label_txt:
                    value_width = pdfmetrics.stringWidth(
                        value_txt[:24],
                        range_font_name,
                        10,
                    )
                    label_right_x = X_RANGE - value_width - 0.18 * cm

                    if has_arabic(label_txt):
                        c.setFont(arabic_font, range_font_size)
                        c.drawRightString(label_right_x, ry, _ar(label_txt + " :"))
                    else:
                        c.setFont(range_font_name, range_font_size)
                        c.drawRightString(label_right_x, ry, (label_txt + ":")[:14])

            # separator line under current row
            y_line = y - 0.28 * cm
            c.setStrokeColorRGB(0.78, 0.86, 0.96)
            c.setLineWidth(0.6)
            c.line(X_TEST, y_line, RIGHT_X, y_line)
            c.setStrokeColorRGB(0, 0, 0)

            # normal spacing between rows
            y -= 0.72 * cm

            # extra spacing after each TORCH IgM row to separate pairs
            if str(category).upper() == "TORCH" and test in {
                "CMV IgM-Ab",
                "HSV I -IgM- Ab",
                "HSV II -IgM- Ab",
                "Rubella IgM-Ab",
            }:
                y -= 0.42 * cm

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1.6)
        c.line(LEFT_X, y, RIGHT_X, y)

        y -= 0.35 * cm

    _draw_lab_footer(c, width, settings, footer_text)
    c.save()
    return out_path





def make_pdf_gue_report(
    patient,
    report_id: str,
    rows: list[dict],
    footer_text: str = "",
) -> Path:
    date_iso = _patient_field(patient, "date_iso", "date")

    filename = f"gue_{date_iso}_{report_id[:8]}.pdf"
    out_path = get_temp_pdf_path(_safe_filename(filename))

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    settings = _get_print_settings()

    LEFT_X = 2.0 * cm
    RIGHT_X = width - 2.0 * cm
    TITLE_Y_GAP = 0.25 * cm

    def norm(name: str) -> str:
        return (name or "").strip().lower()

    def pretty_label(name: str) -> str:
        k = norm(name)
        if k == "rbc":
            return "R.B.C"
        if k == "sp_gravity":
            return "SP.Gravity"
        if k == "epith_cell":
            return "Epith Cell"
        if k == "pus_cell":
            return "Pus cell"
        if k == "bile_pigment":
            return "Bile Pigment"
        if k == "ketone_bodies":
            return "Ketone Bodies"
        if k in {"crystals_1", "crystals_2", "crystals"}:
            return "Crystals"
        if k in {"other_1", "other_2", "other"}:
            return "Other"
        return (name or "").replace("_", " ").strip().title()

    physical_order = [
        "color",
        "appearance",
        "reaction",
        "sp_gravity",
        "albumin",
        "sugar",
        "bile_pigment",
        "urobilinogen",
        "ketone_bodies",
        "protein",
    ]

    micro_order = [
        "pus_cell",
        "rbc",
        "epith_cell",
        "casts",
        "crystals",
        "crystals_1",
        "crystals_2",
        "bacteria",
        "other",
        "other_1",
        "other_2",
    ]

    physical_set = set(physical_order)
    micro_set = set(micro_order)

    by_name: dict[str, str] = {}
    for row in rows:
        test_name = str(row.get("test_name", "") or "").strip()
        result = str(row.get("result", "") or "").strip()
        if not test_name:
            continue
        by_name[norm(test_name)] = result

    physical_rows: list[tuple[str, str]] = []
    micro_rows: list[tuple[str, str]] = []

    for key in physical_order:
        if key in by_name:
            physical_rows.append((pretty_label(key), by_name[key]))

    for key in micro_order:
        if key in by_name:
            micro_rows.append((pretty_label(key), by_name[key]))

    for raw_name, result in list(by_name.items()):
        if raw_name not in physical_set and raw_name not in micro_set:
            micro_rows.append((pretty_label(raw_name), result))

    y = _draw_lab_header(c, patient, report_id, width, height)

    # main title lower than before
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-Bold", 15)
    c.drawCentredString(width / 2, y + TITLE_Y_GAP, "General Urine Examination")

    # extra space between main title and first section
    y -= 0.35 * cm

    def draw_section_header(y_pos: float, title: str) -> float:
        c.setStrokeColorRGB(0.75, 0.00, 0.00)
        c.setLineWidth(1.1)
        c.line(LEFT_X, y_pos, RIGHT_X, y_pos)

        c.setFillColorRGB(0.75, 0.00, 0.00)
        c.setFont("Times-Bold", 13)
        c.drawString(LEFT_X + 0.2 * cm, y_pos + 0.22 * cm, title)

        c.setFont("Times-Bold", 13)
        c.drawString(11.2 * cm, y_pos + 0.22 * cm, "Result")

        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)

        return y_pos - 0.70 * cm

    def draw_row(y_pos: float, label: str, value: str) -> float:
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-Bold", 12.5)
        c.drawString(5.1 * cm, y_pos, label)

        c.setFillColorRGB(0.18, 0.22, 0.58)
        c.setFont("Times-Bold", 12.5)
        c.drawString(11.2 * cm, y_pos, value)

        # darker, clearer separator between every row
        c.setStrokeColorRGB(0.72, 0.72, 0.72)
        c.setLineWidth(0.7)
        c.line(LEFT_X, y_pos - 0.24 * cm, RIGHT_X, y_pos - 0.24 * cm)

        return y_pos - 0.74 * cm

    y -= 0.45 * cm
    y = draw_section_header(y, "Physically Examination")

    for label, value in physical_rows:
        y = draw_row(y, label, value)

    # bigger gap between the two blocks
    y -= 0.42 * cm
    y = draw_section_header(y, "Microscopical Examination")

    for label, value in micro_rows:
        y = draw_row(y, label, value)

    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.2)
    c.line(LEFT_X, y - 0.08 * cm, RIGHT_X, y - 0.08 * cm)

    _draw_lab_footer(c, width, settings, footer_text)
    c.save()
    return out_path



def make_pdf_gse_report(patient, report_id: str, rows: list[dict], footer_text: str = "") -> Path:
    date_iso = _patient_field(patient, "date_iso", "date")
    filename = f"gse_{date_iso}_{report_id[:8]}.pdf"
    out_path = get_temp_pdf_path(_safe_filename(filename))

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    settings = _get_print_settings()

    y = _draw_lab_header(c, patient, report_id, width, height)

    # title
    y -= 1.2 * cm
    c.setFont("Times-Bold", 15)
    c.drawCentredString(width / 2, y, "General Stool Examination")

    physical = []
    micro = []

    for r in rows:
        name = str(r["test_name"]).lower()

        if name in ["color", "consistency", "ph"]:
            physical.append(r)
        else:
            micro.append(r)

    # -------------------
    # Physically section
    # -------------------
    y -= 1.2 * cm
    c.setFont("Times-BoldItalic", 13)
    c.setFillColorRGB(0.6, 0, 0)
    c.drawString(2 * cm, y, "physically Examination")

    c.setFillColorRGB(0.6, 0, 0)
    c.drawString(13 * cm, y, "Result")

    y -= 0.3 * cm
    c.setStrokeColorRGB(0, 0, 0)
    c.line(2 * cm, y, width - 2 * cm, y)

    y -= 0.9 * cm
    c.setFillColorRGB(0, 0, 0)

    for r in physical:
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-BoldItalic", 12)
        c.drawString(3 * cm, y, f"{r['test_name']} :")

        c.setFont("Times-Bold", 12)
        c.setFillColorRGB(0.1, 0.2, 0.6)
        c.drawString(13 * cm, y, r["result"])

        y -= 0.9 * cm

    # -------------------
    # Microscopical
    # -------------------
    y -= 0.5 * cm
    c.setFont("Times-BoldItalic", 13)
    c.setFillColorRGB(0.6, 0, 0)
    c.drawString(2 * cm, y, "Microscopical Examination")

    c.drawString(13 * cm, y, "Result")

    y -= 0.3 * cm
    c.setStrokeColorRGB(0, 0, 0)
    c.line(2 * cm, y, width - 2 * cm, y)

    y -= 0.9 * cm
    c.setFillColorRGB(0, 0, 0)

    for r in micro:
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-BoldItalic", 12)
        c.drawString(3 * cm, y, f"{r['test_name']} :")

        c.setFont("Times-Bold", 12)
        c.setFillColorRGB(0.1, 0.2, 0.6)
        c.drawString(13 * cm, y, r["result"])

        y -= 0.85 * cm

    _draw_lab_footer(c, width, settings, footer_text)
    c.save()

    return out_path



def make_pdf_hvs_report(
    patient,
    report_id: str,
    rows: list[dict],
    footer_text: str = "",
) -> Path:
    date_iso = _patient_field(patient, "date_iso", "date")

    filename = f"hvs_{date_iso}_{report_id[:8]}.pdf"
    out_path = get_temp_pdf_path(_safe_filename(filename))

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    settings = _get_print_settings()

    LEFT_X = 2.0 * cm
    RIGHT_X = width - 2.0 * cm
    CENTER_X = width / 2

    def norm(name: str) -> str:
        return (name or "").strip().lower()

    # collect results by test name
    by_name: dict[str, str] = {}
    for row in rows:
        test_name = str(row.get("test_name", "") or "").strip()
        result = str(row.get("result", "") or "").strip()
        if test_name:
            by_name[norm(test_name)] = result

    def get_value(*names: str) -> str:
        for name in names:
            key = norm(name)
            if key in by_name:
                return by_name[key]
        return ""

    # top values
    sample_value = get_value("Sample")
    method_value = get_value("Method")

    # body rows in the order shown in your target image
    body_rows = [
        ("R.B.Cs:", get_value("R.B.Cs", "RBC", "R.B.C")),
        ("Pus cells:", get_value("Pus cells", "Pus cell")),
        ("Epith cells:", get_value("Epith cells", "Epith cell")),
        ("Bacteria:", get_value("Bacteria")),
        ("Monilia:", get_value("Monilia")),
        ("Trichamonas vaginalis:", get_value("Trichamonas vaginalis")),
    ]

    # draw standard lab header
    y = _draw_lab_header(c, patient, report_id, width, height)

    # move a bit lower
    y -= 0.3 * cm

    # sample line
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-BoldItalic", 13)
    c.drawCentredString(CENTER_X - 1.7 * cm, y, "Sample:")
    c.setFillColorRGB(0.22, 0.25, 0.55)
    c.setFont("Times-Bold", 13.5)
    c.drawCentredString(CENTER_X + 2.0 * cm, y, sample_value or "")

    y -= 1.0 * cm

    # method line
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-BoldItalic", 13)
    c.drawCentredString(CENTER_X - 1.7 * cm, y, "Method:")
    c.setFillColorRGB(0.22, 0.25, 0.55)
    c.setFont("Times-Bold", 13.5)
    c.drawCentredString(CENTER_X + 2.0 * cm, y, method_value or "")

    y -= 1.3 * cm

    # Result (H.P.F):
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-Bold", 14)
    c.drawCentredString(CENTER_X, y, "Result (H.P.F):")
    c.setLineWidth(0.8)
    c.line(CENTER_X - 2.0 * cm, y - 0.10 * cm, CENTER_X + 2.0 * cm, y - 0.10 * cm)

    y -= 0.9 * cm

    # top line before rows
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(0.8)
    c.line(LEFT_X + 0.6 * cm, y, RIGHT_X - 0.6 * cm, y)

    y -= 0.7 * cm

    label_x = 8.3 * cm
    value_x = 13.0 * cm

    for label, value in body_rows:
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-BoldItalic", 13)
        c.drawRightString(label_x, y, label)

        c.setFillColorRGB(0.22, 0.25, 0.55)
        c.setFont("Times-Bold", 13.5)
        c.drawString(value_x, y, value or "")

        # row separator
        c.setStrokeColorRGB(0.75, 0.75, 0.75)
        c.setLineWidth(0.6)
        c.line(LEFT_X + 0.5 * cm, y - 0.25 * cm, RIGHT_X - 0.5 * cm, y - 0.25 * cm)

        y -= 0.75 * cm

    # bottom line
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.2)
    c.line(LEFT_X + 0.2 * cm, y + 0.1 * cm, RIGHT_X - 0.2 * cm, y + 0.1 * cm)

    _draw_lab_footer(c, width, settings, footer_text)
    c.save()
    return out_path




def make_pdf_sputum_report(
    patient,
    report_id: str,
    rows: list[dict],
    footer_text: str = "",
) -> Path:
    date_iso = _patient_field(patient, "date_iso", "date")

    filename = f"sputum_{date_iso}_{report_id[:8]}.pdf"
    out_path = get_temp_pdf_path(_safe_filename(filename))

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    settings = _get_print_settings()

    LEFT_X = 3.0 * cm
    RIGHT_X = width - 3.0 * cm
    CENTER_X = width / 2

    def norm(name: str) -> str:
        return (name or "").strip().lower()

    by_name: dict[str, str] = {}
    for row in rows:
        test_name = str(row.get("test_name", "") or "").strip()
        result = str(row.get("result", "") or "").strip()
        if test_name and result:
            by_name[norm(test_name)] = result

    def get_value(*names: str) -> str:
        for name in names:
            key = norm(name)
            if key in by_name:
                return by_name[key]
        return ""

    # -------------------------
    # Read values by role
    # -------------------------
    specimen = get_value("Specimen")

    afb_header = get_value("AFB Header")
    afb_results = [
        get_value("AFB Result 1"),
        get_value("AFB Result 2"),
        get_value("AFB Result 3"),
        get_value("AFB Result 4"),
        get_value("AFB Result 5"),
        get_value("AFB Result 6"),
    ]

    gram_header = get_value("Gram Header")
    gram_results = [
        get_value("Polymorph nuclear cell"),
        get_value("Diplococci"),
        get_value("Mouth flora"),
        get_value("Gram Extra 1"),
        get_value("Gram Extra 2"),
    ]

    # -------------------------
    # Draw header only
    # -------------------------
    y = _draw_lab_header(c, patient, report_id, width, height)

    # leave blank space after header/patient box
    y -= 1.4 * cm

    # -------------------------
    # Specimen value (centered, large, black)
    # -------------------------
    if specimen:
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-BoldItalic", 18)
        c.drawCentredString(CENTER_X, y, specimen)

        specimen_width = pdfmetrics.stringWidth(specimen, "Times-BoldItalic", 18)
        underline_y = y - 0.12 * cm
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.8)
        c.line(
            CENTER_X - specimen_width / 2,
            underline_y,
            CENTER_X + specimen_width / 2,
            underline_y,
        )

        y -= 1.6 * cm

    # -------------------------
    # AFB header (left, black)
    # -------------------------
    if afb_header:
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-BoldItalic", 17)
        c.drawString(LEFT_X, y, afb_header)
        y -= 1.2 * cm

    # -------------------------
    # AFB results (center, blue)
    # -------------------------
    afb_results = [x for x in afb_results if str(x).strip()]
    if afb_results:
        c.setFillColorRGB(0.18, 0.22, 0.58)
        c.setFont("Times-BoldItalic", 17)
        for line in afb_results:
            c.drawCentredString(CENTER_X, y, line)
            y -= 0.95 * cm

        y -= 0.6 * cm

    # -------------------------
    # Gram header (left, black)
    # -------------------------
    if gram_header:
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-BoldItalic", 17)
        c.drawString(LEFT_X, y, gram_header)
        y -= 1.2 * cm

    # -------------------------
    # Gram results (center, blue)
    # -------------------------
    gram_results = [x for x in gram_results if str(x).strip()]
    if gram_results:
        c.setFillColorRGB(0.18, 0.22, 0.58)
        c.setFont("Times-BoldItalic", 17)
        for line in gram_results:
            c.drawCentredString(CENTER_X, y, line)
            y -= 0.95 * cm

    _draw_lab_footer(c, width, settings, footer_text)
    c.save()
    return out_path


def make_pdf_culture_report(
    patient,
    report_id: str,
    grouped_results: dict[str, list[dict]],
    footer_text: str = "",
) -> Path:
    date_iso = _patient_field(patient, "date_iso", "date")
    filename = f"culture_{date_iso}_{report_id[:8]}.pdf"
    out_path = get_temp_pdf_path(_safe_filename(filename))

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    settings = _get_print_settings()

    LEFT_X = 2.0 * cm
    RIGHT_X = width - 2.0 * cm
    CENTER_X = width / 2

    y = _draw_lab_header(c, patient, report_id, width, height)

    culture_rows = grouped_results.get("Culture", [])
    antibiotics_rows = grouped_results.get("Antibiotics", [])

    sample_value = ""
    culture_value = ""

    for r in culture_rows:
        test_name = str(r.get("test_name", "") or "").strip().lower()
        if test_name == "sample":
            sample_value = str(r.get("result", "") or "").strip()
        elif test_name == "result":
            culture_value = str(r.get("result", "") or "").strip()

    if culture_value.lower().startswith("culture:"):
        culture_value = culture_value.split(":", 1)[1].strip()

    # -------------------------
    # Sample / Culture block
    # -------------------------
    y -= 1.3 * cm

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-BoldItalic", 14)
    c.drawString(LEFT_X, y, f"Sample: {sample_value}")

    y -= 0.95 * cm

    c.setFont("Times-BoldItalic", 14)
    c.drawString(LEFT_X, y, f"Culture: {culture_value}")

    # -------------------------
    # Main title
    # -------------------------
    y -= 1.35 * cm
    c.setFont("Times-Bold", 15)
    c.drawCentredString(CENTER_X, y, "Antibiotic sensitivity test")

    # -------------------------
    # Table geometry
    # -------------------------
    y -= 0.95 * cm

    table_x = LEFT_X
    table_width = RIGHT_X - LEFT_X

    left_ant_w = 6.0 * cm
    left_res_w = 2.1 * cm
    right_ant_w = 6.0 * cm
    right_res_w = 2.1 * cm

    x0 = table_x
    x1 = x0 + left_ant_w
    x2 = x1 + left_res_w
    x3 = x2 + right_ant_w
    x4 = x3 + right_res_w

    half = (len(antibiotics_rows) + 1) // 2
    left_rows = antibiotics_rows[:half]
    right_rows = antibiotics_rows[half:]

    row_count = max(len(left_rows), len(right_rows))
    header_h = 0.9 * cm
    row_h = 0.82 * cm
    table_top = y
    table_bottom = table_top - header_h - (row_count * row_h)

    # -------------------------
    # Table outer border
    # -------------------------
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.setLineWidth(0.8)
    c.rect(x0, table_bottom, x4 - x0, table_top - table_bottom, stroke=1, fill=0)

    # Vertical dividers
    c.line(x1, table_bottom, x1, table_top)
    c.line(x2, table_bottom, x2, table_top)
    c.line(x3, table_bottom, x3, table_top)

    # Header separator
    c.line(x0, table_top - header_h, x4, table_top - header_h)

    # Row separators
    current_y = table_top - header_h
    for _ in range(row_count):
        current_y -= row_h
        c.line(x0, current_y, x4, current_y)

    # -------------------------
    # Header labels
    # -------------------------
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Times-BoldItalic", 13)

    header_y = table_top - 0.62 * cm
    c.drawCentredString((x0 + x1) / 2, header_y, "Antibiotic")
    c.drawCentredString((x1 + x2) / 2, header_y, "Result")
    c.drawCentredString((x2 + x3) / 2, header_y, "Antibiotic")
    c.drawCentredString((x3 + x4) / 2, header_y, "Result")

    # -------------------------
    # Table data
    # -------------------------
    def draw_result_centered(x_left: float, x_right: float, y_pos: float, value: str) -> None:
        val = (value or "").strip()
        if not val:
            return

        upper = val.upper()
        if upper.startswith("R"):
            c.setFillColorRGB(0.70, 0.10, 0.10)
        elif upper.startswith("I"):
            c.setFillColorRGB(0.75, 0.45, 0.05)
        elif upper.startswith("S"):
            c.setFillColorRGB(0.10, 0.25, 0.65)
        else:
            c.setFillColorRGB(0, 0, 0)

        c.setFont("Times-Bold", 13)
        c.drawCentredString((x_left + x_right) / 2, y_pos, val)

    for i in range(row_count):
        row_y = table_top - header_h - (i * row_h) - 0.56 * cm

        if i < len(left_rows):
            ab = left_rows[i]
            ab_name = str(ab.get("test_name", "") or "").strip()
            ab_result = str(ab.get("result", "") or "").strip()

            c.setFillColorRGB(0, 0, 0)
            c.setFont("Times-BoldItalic", 12.5)
            c.drawString(x0 + 0.22 * cm, row_y, ab_name[:32])

            draw_result_centered(x1, x2, row_y, ab_result)

        if i < len(right_rows):
            ab = right_rows[i]
            ab_name = str(ab.get("test_name", "") or "").strip()
            ab_result = str(ab.get("result", "") or "").strip()

            c.setFillColorRGB(0, 0, 0)
            c.setFont("Times-BoldItalic", 12.5)
            c.drawString(x2 + 0.22 * cm, row_y, ab_name[:32])

            draw_result_centered(x3, x4, row_y, ab_result)

    _draw_lab_footer(c, width, settings, footer_text)
    c.save()
    return out_path



def make_pdf_cbc_overlay(patient, report_id: str, footer_text: str = "") -> Path:
    date_iso = _patient_field(patient, "date_iso", "date")

    filename = f"cbc_{date_iso}_{report_id[:8]}.pdf"
    out_path = get_temp_pdf_path(_safe_filename(filename))
    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    settings = _get_print_settings()

    _draw_lab_header(c, patient, report_id, width, height)
    _draw_lab_footer(c, width, settings,footer_text)

    c.save()
    return out_path


def group_results(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        category = str(r.get("category", "Uncategorized") or "Uncategorized")
        grouped.setdefault(category, []).append(r)
    return grouped


# ----------------------------
# Shared bottom buttons for ALL modules
# ----------------------------

def build_back_print_pdf_bar(
    parent: QWidget,
    *,
    on_back,
    on_print,
    on_pdf,
) -> QHBoxLayout:
    """
    Same 3 buttons everywhere: Back / Print / PDF
    """
    row = QHBoxLayout()
    row.setSpacing(10)

    btn_print = QPushButton("Print")
    btn_print.setMinimumHeight(42)
    btn_print.clicked.connect(on_print)

    btn_pdf = QPushButton("PDF")
    btn_pdf.setMinimumHeight(42)
    btn_pdf.clicked.connect(on_pdf)

    btn_back = QPushButton("Back")
    btn_back.setMinimumHeight(42)
    btn_back.clicked.connect(on_back)

    style = "QPushButton { font-size: 15px; font-weight: 800; }"
    btn_print.setStyleSheet(style)
    btn_pdf.setStyleSheet(style)
    btn_back.setStyleSheet(style)

    row.addWidget(btn_back)
    row.addStretch(1)
    row.addWidget(btn_print)
    row.addWidget(btn_pdf)
    return row





from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtCore import QRectF, Qt


def apply_round_corners(window, radius=12):
    # When maximized, remove the mask so the window fills normally
    if window.isMaximized():
        window.clearMask()
        return

    window.setAttribute(Qt.WA_TranslucentBackground, True)

    rect = QRectF(window.rect())
    if rect.width() <= 0 or rect.height() <= 0:
        return

    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)

    region = QRegion(path.toFillPolygon().toPolygon())
    window.setMask(region)







