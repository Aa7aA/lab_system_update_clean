# app/main.py
from __future__ import annotations

import sys
import win32event
import win32api
import winerror
from dataclasses import dataclass, asdict
from uuid import uuid4




from PySide6.QtGui import QPixmap, QAction, QColor
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QPoint

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QDateEdit,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
    QFrame,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QToolButton,
    QMenu,
    QGraphicsDropShadowEffect,
    QScrollArea,
)

from .db import get_conn, init_db, get_lab_setting, set_lab_setting
from .branding import LAB_BRANDING
from .version import APP_VERSION
from .lab_identity import get_lab_identity
from .updater import fetch_update_manifest, is_newer_version, is_lab_allowed
from .update_window import UpdateWindow
from .tests_window import TestsWindow as DbTestsWindow
from .module_window import ModuleWindow
from .ui_utils import (
    make_title,
    make_pdf_cbc_overlay,
    apply_global_theme,
    fit_window_to_screen,
    apply_round_corners,
    print_pdf_and_delete,
    save_pdf_via_dialog,
)







# ----------------------------
# Data model
# ----------------------------
@dataclass
class PatientData:
    name: str
    doctor: str
    age: int | None
    gender: str
    date_iso: str

# ----------------------------
# CBC Window (overlay only)
# ----------------------------
class CBCWindow(QMainWindow):
    def __init__(self, patient: PatientData, report_id: str):
        super().__init__()
        self.patient = patient
        self.report_id = report_id

        self.setWindowTitle("CBC")
        self.resize(1000, 520)
        apply_round_corners(self, 15)
   

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


        root = QWidget()
        root.setLayoutDirection(Qt.RightToLeft)  # keep your current layout direction
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QGroupBox("Patient Info")
        header.setLayoutDirection(Qt.RightToLeft)
        grid = QGridLayout(header)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        def row(label: str, value: str, r: int):
            grid.addWidget(make_title(label), r, 0)
            v = QLabel(value)
            v.setStyleSheet("font-size: 14px;")
            grid.addWidget(v, r, 1)

        row("Patient name:", patient.name or "-", 0)
        row("Doctor:", patient.doctor or "-", 1)
        row("Age:", (str(patient.age) if patient.age is not None else "-"), 2)
        row("Gender:", patient.gender or "-", 3)
        row("Date:", patient.date_iso, 5)
        layout.addWidget(header)

        info = QLabel(
            "ملاحظة: نتائج CBC تتم طباعتها من الجهاز.\n"
            "هذا القسم يطبع فقط الرأس والتذييل على ورقة CBC."
        )
        info.setStyleSheet("font-size: 14px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        toolbar_box = QGroupBox("الإجراءات")
        toolbar_box.setLayoutDirection(Qt.RightToLeft)
        toolbar = QHBoxLayout(toolbar_box)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(8)

        self.btn_back = QPushButton("رجوع")
        self.btn_print = QPushButton("طباعة")
        self.btn_pdf = QPushButton("PDF")

        self.btn_back.setMinimumHeight(34)
        self.btn_print.setMinimumHeight(34)
        self.btn_pdf.setMinimumHeight(34)

        self.btn_back.clicked.connect(self.close)
        self.btn_print.clicked.connect(self.on_print_clicked)
        self.btn_pdf.clicked.connect(self.on_pdf_clicked)

        toolbar.addWidget(self.btn_print)
        toolbar.addWidget(self.btn_pdf)
        toolbar.addStretch(1)
        toolbar.addWidget(self.btn_back)

        layout.addWidget(toolbar_box)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)

    def _build_overlay_pdf(self):
        with get_conn() as conn:
            footer_text = get_lab_setting(conn, "footer_text", "")

        return make_pdf_cbc_overlay(
            self.patient,
            self.report_id,
            footer_text=footer_text,
        )

    def on_print_clicked(self):
        try:
            pdf_path = self._build_overlay_pdf()
            print_pdf_and_delete(pdf_path)
        except Exception as e:
            QMessageBox.warning(self, "خطأ في الطباعة", f"فشلت طباعة ملف CBC:\n{e}")

    def on_pdf_clicked(self):
        try:
            pdf_path = self._build_overlay_pdf()
            suggested_name = f"CBC_{self.patient.name or 'patient'}_{self.report_id}.pdf"
            save_path = save_pdf_via_dialog(self, pdf_path, suggested_name=suggested_name)
            if save_path:
                QMessageBox.information(self, "PDF", f"تم حفظ الملف:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ في PDF", f"فشل حفظ ملف CBC:\n{e}")


# ----------------------------
# Search Window
# ----------------------------
class SearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("بحث التقارير")
        fit_window_to_screen(
            self,
            width_ratio=0.92,
            height_ratio=0.88,
            min_width=1000,
            min_height=620,
        )

        apply_round_corners(self, 15)

        self.is_dark_mode = False
        self._drag_pos: QPoint | None = None

        self._opened_windows: list[QMainWindow] = []

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


        root = QFrame()
        root.setObjectName("AppShell")
        root.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)


        # ---------------- Custom Header ----------------
        header = QFrame()
        header.setObjectName("HeaderBar")
    

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        header_layout.setSpacing(14)

        brand_logo = QLabel()
        brand_logo.setFixedSize(54, 54)
        brand_logo.setAlignment(Qt.AlignCenter)

        brand_logo_path = Path(LAB_BRANDING["logo_path"])
        if brand_logo_path.exists():
            brand_pixmap = QPixmap(str(brand_logo_path))
            brand_logo.setPixmap(
                brand_pixmap.scaled(
                    54, 54,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

        brand_text_wrap = QVBoxLayout()
        brand_text_wrap.setSpacing(0)

        brand_title = QLabel("بحث التقارير")
        brand_title.setObjectName("BrandTitle")

        brand_subtitle = QLabel(LAB_BRANDING["lab_name_en"])
        brand_subtitle.setObjectName("BrandSubtitle")

        brand_text_wrap.addWidget(brand_title)
        brand_text_wrap.addWidget(brand_subtitle)

        brand_wrap = QHBoxLayout()
        brand_wrap.setSpacing(12)
        brand_wrap.addWidget(brand_logo)
        brand_wrap.addLayout(brand_text_wrap)
        brand_wrap.addStretch(1)

        header_left = QWidget()
        header_left.setLayout(brand_wrap)

        header_buttons = QHBoxLayout()
        header_buttons.setSpacing(6)


        self.search_btn_minimize = QToolButton()
        self.search_btn_minimize.setObjectName("HeaderIconButton")
        self.search_btn_minimize.setText("—")
        self.search_btn_minimize.clicked.connect(self.showMinimized)

        self.search_btn_maximize = QToolButton()
        self.search_btn_maximize.setObjectName("HeaderIconButton")
        self.search_btn_maximize.setText("▢")
        self.search_btn_maximize.clicked.connect(self.toggle_max_restore)

        self.search_btn_close = QToolButton()
        self.search_btn_close.setObjectName("HeaderIconButton")
        self.search_btn_close.setText("✕")
        self.search_btn_close.clicked.connect(self.close)

        
        header_buttons.addWidget(self.search_btn_minimize)
        header_buttons.addWidget(self.search_btn_maximize)
        header_buttons.addWidget(self.search_btn_close)

        header_right = QWidget()
        header_right.setLayout(header_buttons)

        header_layout.addWidget(header_left, 1)
        header_layout.addWidget(header_right, 0)

        self.add_soft_shadow(header, blur=26, x=0, y=4, alpha=22)
        layout.addWidget(header)




        top = QGroupBox("البحث عن تقرير مريض")
        top.setLayoutDirection(Qt.RightToLeft)
        top.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: 800;
                border: 1px solid #dde6f0;
                border-radius: 18px;
                margin-top: 12px;
                padding-top: 16px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                right: 18px;
                padding: 0 10px;
                color: #1f3b57;
            }
        """)

        g = QGridLayout(top)
        g.setContentsMargins(18, 20, 18, 18)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(12)

        self.search_name = QLineEdit()
        self.search_name.setPlaceholderText("اكتب اسم المريض")
        self.search_name.setMinimumHeight(46)

        self.btn_search = QPushButton("بحث")

        self.btn_search.setStyleSheet("""
            QPushButton {
                background-color: #2f6fe4;
                color: white;
                border: none;
                border-radius: 14px;
                padding: 10px 22px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #2b63cb;
            }
            QPushButton:pressed {
                background-color: #244fa8;
            }
        """)




        self.btn_search.setMinimumHeight(46)
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.clicked.connect(self.run_search)

        g.addWidget(make_title("اسم المريض:"), 0, 0)
        g.addWidget(self.search_name, 0, 1)
        g.addWidget(self.btn_search, 0, 2)

        g.setColumnStretch(1, 1)

        self.add_soft_shadow(top, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(top)

        results_box = QGroupBox("نتائج البحث")
        results_box.setLayoutDirection(Qt.RightToLeft)
        results_box.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: 800;
                border: 1px solid #dde6f0;
                border-radius: 18px;
                margin-top: 12px;
                padding-top: 16px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                right: 18px;
                padding: 0 10px;
                color: #1f3b57;
            }
        """)

        mid = QVBoxLayout(results_box)
        mid.setContentsMargins(18, 18, 18, 18)
        mid.setSpacing(12)

        self.lbl_info = QLabel("اكتب اسم المريض ثم اضغط بحث.")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("font-size: 14px; color: #4f6f8f; background: transparent;")
        mid.addWidget(self.lbl_info)

        self.list_reports = QTableWidget()
        self.list_reports.verticalHeader().setDefaultSectionSize(40)
        self.list_reports.setColumnCount(7)
        self.list_reports.setHorizontalHeaderLabels([
            "اسم المريض",
            "القسم",
            "التاريخ",
            "الطبيب",
            "الجنس",
            "العمر",
            "رقم التقرير",
        ])
        self.list_reports.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.list_reports.verticalHeader().setVisible(False)
        self.list_reports.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.list_reports.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_reports.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_reports.setAlternatingRowColors(False)
        self.list_reports.setMinimumHeight(420)

        self.list_reports.setStyleSheet("""
            QTableWidget {
                font-size: 14px;
                border: 1px solid #e1e8f1;
                border-radius: 14px;
                background: #ffffff;
                alternate-background-color: #ffffff;
                gridline-color: #eef2f7;
            }
            QTableWidget::item {
                padding: 10px;
                background: #ffffff;
                color: #16324f;
            }
            QTableWidget::item:selected {
                background: #eaf3ff;
                color: #16324f;
            }
            QTableWidget::item:selected:active {
                background: #eaf3ff;
                color: #16324f;
            }
            QHeaderView::section {
                background: #f5f8fc;
                font-weight: 800;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #e6edf5;
            }
        """)

        self.list_reports.doubleClicked.connect(self.open_selected_report)

        mid.addWidget(self.list_reports, 1)

        self.add_soft_shadow(results_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(results_box, 1)

        bottom_box = QGroupBox("الإجراءات")
        bottom_box.setLayoutDirection(Qt.RightToLeft)
        bottom_box.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: 800;
                border: 1px solid #dde6f0;
                border-radius: 18px;
                margin-top: 12px;
                padding-top: 16px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                right: 18px;
                padding: 0 10px;
                color: #1f3b57;
            }
        """)

        bottom = QHBoxLayout(bottom_box)
        bottom.setContentsMargins(18, 18, 18, 18)
        bottom.setSpacing(12)

        self.btn_open = QPushButton("فتح التقرير")
        self.btn_open.setMinimumHeight(42)
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_selected_report)

        self.btn_delete = QPushButton("حذف التقرير")
        self.btn_delete.setMinimumHeight(42)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #a33232;
                border: 1px solid #f0c8c8;
                border-radius: 14px;
                padding: 10px 18px;
                font-size: 15px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #fff5f5;
                border: 1px solid #e6a8a8;
            }
            QPushButton:pressed {
                background-color: #ffeaea;
            }
        """)
        self.btn_delete.clicked.connect(self.delete_selected_report)

        back = QPushButton("إغلاق")
        back.setMinimumHeight(42)
        back.setCursor(Qt.PointingHandCursor)
        back.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #28415f;
                border: 1px solid #dfe7f1;
                border-radius: 14px;
                padding: 10px 18px;
                font-size: 15px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #f7fbff;
                border: 1px solid #8fc7ff;
            }
        """)
        back.clicked.connect(self.close)

        bottom.addStretch(1)
        bottom.addWidget(self.btn_open)
        bottom.addWidget(self.btn_delete)
        bottom.addWidget(back)

        self.add_soft_shadow(bottom_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(bottom_box)

        scroll.setWidget(root)
        self.setCentralWidget(scroll)

    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        apply_round_corners(self, 12)


    def run_search(self):
        name = self.search_name.text().strip()
        self.list_reports.setRowCount(0)

        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة اسم المريض أولاً.")
            return

        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    r.report_id,
                    r.patient_name,
                    r.report_date,
                    r.doctor_name,
                    r.gender,
                    r.age,
                    rr.module
                FROM reports r
                JOIN report_results rr
                    ON rr.report_id = r.report_id
                WHERE r.patient_name LIKE ?
                GROUP BY
                    r.report_id,
                    r.patient_name,
                    r.report_date,
                    r.doctor_name,
                    r.gender,
                    r.age,
                    rr.module
                ORDER BY r.updated_at DESC, rr.module ASC
                """,
                (f"%{name}%",),
            ).fetchall()

        if not rows:
            self.lbl_info.setText("لا توجد نتائج.")
            return

        self.lbl_info.setText(f"تم العثور على {len(rows)} نتيجة. انقر مرتين لفتح التقرير.")
        self.list_reports.setRowCount(len(rows))

        for row_index, (report_id, patient_name, report_date, doctor_name, gender, age, module) in enumerate(rows):
            short_id = report_id[:8]
            module = module or "?"
            age_text = str(age) if age is not None else "-"

            values = [
                patient_name or "-",
                module,
                report_date or "-",
                doctor_name or "-",
                gender or "-",
                age_text,
                short_id,
            ]

            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, {
                    "report_id": report_id,
                    "module": module,
                })
                self.list_reports.setItem(row_index, col_index, item)


    def delete_selected_report(self):
        item = self.list_reports.currentItem()
        if item is None:
            QMessageBox.information(self, "تنبيه", "يرجى اختيار تقرير أولاً.")
            return

        payload = item.data(Qt.UserRole) or {}
        report_id = payload.get("report_id", "")
        module = payload.get("module", "")

        if not report_id or not module:
            QMessageBox.warning(self, "خطأ", "تعذر تحديد التقرير المطلوب حذفه.")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف هذا التقرير نهائياً؟\n\n"
            f"القسم: {module}\n"
            f"رقم التقرير: {report_id[:8]}\n\n"
            f"لا يمكن التراجع عن هذا الإجراء.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        with get_conn() as conn:
            conn.execute(
                """
                DELETE FROM report_results
                WHERE report_id = ? AND module = ?
                """,
                (report_id, module),
            )

            remaining = conn.execute(
                """
                SELECT COUNT(*) 
                FROM report_results
                WHERE report_id = ?
                """,
                (report_id,),
            ).fetchone()

            remaining_count = int(remaining[0] if remaining else 0)

            if remaining_count == 0:
                conn.execute(
                    """
                    DELETE FROM reports
                    WHERE report_id = ?
                    """,
                    (report_id,),
                )

        self.run_search()
        QMessageBox.information(self, "تم", "تم حذف التقرير نهائياً.")







    def open_selected_report(self, item=None, mode=None):
        row = self.list_reports.currentRow()
        if row < 0:
            QMessageBox.information(self, "تنبيه", "يرجى اختيار تقرير أولاً.")
            return

        item = self.list_reports.item(row, 0)
        if item is None:
            QMessageBox.information(self, "تنبيه", "يرجى اختيار تقرير أولاً.")
            return

        payload = item.data(Qt.UserRole) or {}
        report_id = payload.get("report_id", "")
        selected_module = payload.get("module", "")

        with get_conn() as conn:
            r = conn.execute(
                """
                SELECT patient_name, doctor_name, gender, age, copies, report_date
                FROM reports
                WHERE report_id = ?
                """,
                (report_id,),
            ).fetchone()

            if not r:
                QMessageBox.warning(self, "خطأ", "لم يتم العثور على التقرير.")
                return

            patient = PatientData(
                name=r[0] or "",
                doctor=r[1] or "",
                gender=r[2] or "",
                age=r[3],
                date_iso=r[5] or "",
            )


            mod_row = conn.execute(
                """
                SELECT module
                FROM report_results
                WHERE report_id = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (report_id,),
            ).fetchone()

        detected_module = selected_module or (str(mod_row[0]).strip() if mod_row and mod_row[0] else "")
        if mode is not None:
            detected_module = mode

        if not detected_module:
            QMessageBox.warning(self, "خطأ", "تعذر تحديد القسم الخاص بهذا التقرير.")
            return

        # Open DB-only windows
        if detected_module == "Culture":
            from .culture_window import CultureWindow
            w = CultureWindow(patient, report_id=report_id)
        elif detected_module == "Tests":
            w = DbTestsWindow(patient=asdict(patient), report_id=report_id)
        elif detected_module == "CBC":
            w = CBCWindow(patient, report_id=report_id)
        else:
            w = ModuleWindow(module_code=detected_module, patient=patient, report_id=report_id)

        self._opened_windows.append(w)
        w.destroyed.connect(lambda: self._opened_windows.remove(w) if w in self._opened_windows else None)
        w.show()




    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)







# ----------------------------
# Main Window
# ----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._opened_windows = []
        self.setWindowTitle("Lab")
        fit_window_to_screen(
            self,
            width_ratio=0.94,
            height_ratio=0.9,
            min_width=1100,
            min_height=620,
        )
        apply_round_corners(self, 15)


        self.is_dark_mode = False
        self._drag_pos: QPoint | None = None

        # One report_id per "visit"
        self.report_id: str = ""

        self.search_window: SearchWindow | None = None
        self.settings_window = None

        #new
        self.range_selector_window = None
        self.test_admin_selector_window = None
        self.module_admin_window = None
        self.lab_print_settings_window = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root = QFrame()
        root.setObjectName("AppShell")

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        scroll.setWidget(root)


        # ---------------- Custom Header ----------------
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(88)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 10, 18, 10)
        header_layout.setSpacing(14)
        header_layout.setAlignment(Qt.AlignVCenter)


        brand_text_wrap = QVBoxLayout()
        brand_text_wrap.setSpacing(0)

        brand_title = QLabel(LAB_BRANDING["lab_name_ar"])
        brand_title.setObjectName("BrandTitle")
        brand_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        brand_subtitle = QLabel(LAB_BRANDING["lab_name_en"])
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        brand_text_wrap.addWidget(brand_title)
        brand_text_wrap.addWidget(brand_subtitle)

        brand_wrap = QHBoxLayout()
        brand_wrap.setSpacing(12)
        brand_wrap.setContentsMargins(0, 0, 0, 0)
        brand_wrap.addLayout(brand_text_wrap)
        brand_wrap.addStretch(1)

        header_left = QWidget()
        header_left.setLayout(brand_wrap)

        header_buttons = QHBoxLayout()
        header_buttons.setSpacing(8)


        self.btn_minimize = QToolButton()
        self.btn_minimize.setObjectName("HeaderIconButton")
        self.btn_minimize.setText("—")
        self.btn_minimize.clicked.connect(self.showMinimized)

        self.btn_maximize = QToolButton()
        self.btn_maximize.setObjectName("HeaderIconButton")
        self.btn_maximize.setText("▢")
        self.btn_maximize.clicked.connect(self.toggle_max_restore)

        self.btn_close = QToolButton()
        self.btn_close.setObjectName("HeaderIconButton")
        self.btn_close.setText("✕")
   #     self.btn_close.clicked.connect(False)


        self.btn_close.setStyleSheet("""
            QToolButton {
                background: #f3f5f8;
                border: 1px solid #d7dfe8;
                border-radius: 18px;
                color: #9aa8b8;
            }
        """)



        header_buttons.addWidget(self.btn_minimize)
        header_buttons.addWidget(self.btn_maximize)
        header_buttons.addWidget(self.btn_close)

        header_right = QWidget()
        header_right.setLayout(header_buttons)

        header_layout.addWidget(header_left, 1)
        header_layout.addWidget(header_right, 0)

        self.add_soft_shadow(header, blur=26, x=0, y=4, alpha=22)
        root_layout.addWidget(header)







        # ---------------- Top (logo + patient info) ----------------
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        logo_box = self.make_box_frame()
        logo_layout = QVBoxLayout(logo_box)
        logo_layout.setContentsMargins(10, 10, 10, 10)
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setMinimumSize(280, 120)  # keeps the box size stable

        logo_path = Path(LAB_BRANDING["logo_path"])

        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            logo.setPixmap(
                pixmap.scaled(
                    logo.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        else:
            logo.setText("Logo not found")

        logo_layout.addWidget(logo, 1)
        self.add_soft_shadow(logo_box, blur=30, x=0, y=6, alpha=24)
        top_row.addWidget(logo_box, 2)

        patient_box = QGroupBox("معلومات المريض")
        patient_box.setLayoutDirection(Qt.RightToLeft)
        patient_box.setStyleSheet(
            """
            QGroupBox { font-size: 14px; font-weight: 700; }
            QGroupBox::title { subcontrol-origin: margin; padding-right: 18px; padding-left: 6px; }
            """
        )

        pgrid = QGridLayout(patient_box)
        pgrid.setContentsMargins(14, 18, 14, 14)
        pgrid.setHorizontalSpacing(16)
        pgrid.setVerticalSpacing(14)

        self.patient_name = QLineEdit()
        self.patient_name.setPlaceholderText("اسم المريض")
        self.patient_name.setMinimumHeight(38)

        self.doctor = QComboBox()
        self.doctor.setMinimumHeight(38)

        self.age = QSpinBox()
        self.age.setRange(0, 120)
        self.age.setValue(0)
        self.age.setMinimumHeight(38)
        self.age.setButtonSymbols(QSpinBox.UpDownArrows)

        self.gender = QComboBox()
        self.gender.addItems(["", "ذكر", "أنثى"])
        self.gender.setMinimumHeight(38)

        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(QDate.currentDate())
        self.date.setMinimumHeight(38)

        # make inputs look balanced
        self.patient_name.setMinimumWidth(460)
        self.doctor.setMinimumWidth(460)
        self.age.setMinimumWidth(150)
        self.gender.setMinimumWidth(150)
        self.date.setMinimumWidth(150)

        # Row 1: patient name
        pgrid.addWidget(make_title("الاسم:"), 0, 0)
        pgrid.addWidget(self.patient_name, 0, 1, 1, 3)

        # Row 2: doctor
        pgrid.addWidget(make_title("الطبيب:"), 1, 0)
        pgrid.addWidget(self.doctor, 1, 1, 1, 3)

        # Row 3: gender + age
        pgrid.addWidget(make_title("الجنس:"), 2, 0)
        pgrid.addWidget(self.gender, 2, 1)

        pgrid.addWidget(make_title("العمر:"), 2, 2)
        pgrid.addWidget(self.age, 2, 3)

        # Row 4: date
        pgrid.addWidget(make_title("التاريخ:"), 3, 0)
        pgrid.addWidget(self.date, 3, 1)

        # stretch so fields stay in proper proportion
        pgrid.setColumnStretch(0, 0)
        pgrid.setColumnStretch(1, 4)
        pgrid.setColumnStretch(2, 0)
        pgrid.setColumnStretch(3, 3)

        self.add_soft_shadow(patient_box, blur=30, x=0, y=6, alpha=24)
        top_row.addWidget(patient_box, 5)
        root_layout.addLayout(top_row)

        # ---------------- Middle (modules + tools) ----------------
        mid = QHBoxLayout()
        mid.setSpacing(16)

        self.modules_box = QGroupBox("تحاليل المختبر")
        self.modules_box.setLayoutDirection(Qt.RightToLeft)
        self.modules_box.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: 800;
                border: 1px solid #dde2ea;
                border-radius: 18px;
                margin-top: 12px;
                padding-top: 16px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                right: 18px;
                padding: 0 10px;
                color: #1f3b57;
            }
        """)
        self.modules_grid = QGridLayout(self.modules_box)
        self.modules_grid.setContentsMargins(18, 22, 18, 18)
        self.modules_grid.setHorizontalSpacing(14)
        self.modules_grid.setVerticalSpacing(14)

        self.module_buttons = []
        self.refresh_module_buttons()

        self.add_soft_shadow(self.modules_box, blur=30, x=0, y=6, alpha=24)
        mid.addWidget(self.modules_box, 5)

        tools_box = QGroupBox("الأدوات")
        tools_box.setLayoutDirection(Qt.RightToLeft)
        tools_box.setStyleSheet("""
            QGroupBox {
                font-size: 15px;
                font-weight: 800;
                border: 1px solid #dde2ea;
                border-radius: 18px;
                margin-top: 12px;
                padding-top: 16px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                right: 18px;
                padding: 0 10px;
                color: #1f3b57;
            }
        """)
        av = QVBoxLayout(tools_box)
        av.setContentsMargins(16, 20, 16, 16)
        av.setSpacing(10)

        btn_search = self.make_tool_button("البحث في التقارير")
        btn_search.clicked.connect(self.open_search)
        av.addWidget(btn_search)

        btn_update = self.make_tool_button("التحقق من التحديثات")
        btn_update.clicked.connect(self.check_for_updates)
        av.addWidget(btn_update)

        btn_settings = self.make_tool_button("الإعدادات")
        btn_settings.clicked.connect(self.open_settings)
        av.addWidget(btn_settings)

        av.addStretch(1)

        btn_exit = QPushButton("خروج")
        btn_exit.setMinimumHeight(34)
        btn_exit.setCursor(Qt.PointingHandCursor)
        btn_exit.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #b3262e;
                border: 1px solid #e7b7bb;
                border-radius: 16px;
                padding: 12px 14px;
                font-size: 14px;
                font-weight: 700;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #fff4f5;
                border: 1px solid #d88b93;
            }
            QPushButton:pressed {
                background-color: #ffe8ea;
            }
        """)
        btn_exit.clicked.connect(self.close)
        av.addWidget(btn_exit)

        self.add_soft_shadow(tools_box, blur=30, x=0, y=6, alpha=24)
        mid.addWidget(tools_box, 1)

        root_layout.addLayout(mid, 1)


        self.setCentralWidget(scroll)
        self.load_doctors()

    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        apply_round_corners(self, 12)


    def make_box_frame(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.StyledPanel)
        f.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #dde2ea;
                border-radius: 18px;
            }
        """)
        return f


    def make_module_card(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setLayoutDirection(Qt.LeftToRight)
        btn.setText(text)
        btn.setMinimumHeight(64)
        btn.setCursor(Qt.PointingHandCursor)

        btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #16324f;
                border: 1px solid #c6d3e1;
                border-radius: 20px;
                padding: 14px;
                font-size: 17px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: #f7fbff;
                border: 1px solid #8fc7ff;
            }

            QPushButton:pressed {
                background-color: #eef5ff;
            }
        """)
        return btn



    def make_tool_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(34)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #28415f;
                border: 1px solid #c6d3e1;
                border-radius: 16px;
                padding: 12px 14px;
                font-size: 14px;
                font-weight: 700;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #f5f9ff;
                border: 1px solid #8fc7ff;
            }
            QPushButton:pressed {
                background-color: #eaf3ff;
            }
        """)
        return btn









    def load_doctors(self):
        self.doctor.clear()
        self.doctor.addItem("")
        with get_conn() as conn:
            rows = conn.execute("SELECT name FROM doctors ORDER BY name").fetchall()
        for (name,) in rows:
            self.doctor.addItem(name or "")
        self.doctor.setCurrentIndex(0)


    def _load_modules_for_home(self) -> list[tuple[str, str]]:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT code, display_name
                FROM modules
                ORDER BY sort_order, display_name
                """
            ).fetchall()

        out: list[tuple[str, str]] = []
        for row in rows:
            code = str(row[0] or "").strip()
            display_name = str(row[1] or "").strip()
            if not code:
                continue
            out.append((code, display_name or code))
        return out


    def refresh_module_buttons(self):
        # Remove old buttons/widgets from the grid
        while self.modules_grid.count():
            item = self.modules_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.module_buttons = []

        module_rows = self._load_modules_for_home()

        r = c = 0
        for module_code, display_name in module_rows:
            btn = self.make_module_card(display_name)
            btn.clicked.connect(lambda checked=False, code=module_code: self.on_module_clicked(code))

            self.modules_grid.addWidget(btn, r, c)
            self.module_buttons.append(btn)

            c += 1
            if c == 3:
                c = 0
                r += 1

        # Keep your "modules disabled until patient/doctor entered" logic working
        if hasattr(self, "_update_module_buttons_state"):
            self._update_module_buttons_state()



    def refresh_all_structure_views(self):
        self.refresh_module_buttons()

        # refresh windows opened from report search and any tracked windows
        for w in list(getattr(self, "_opened_windows", [])):
            try:
                if isinstance(w, ModuleWindow):
                    w.build_tabs_from_db()
                elif isinstance(w, DbTestsWindow):
                    w.build_tabs_from_db()
            except RuntimeError:
                pass
            except Exception:
                pass

        # refresh directly-open home windows too
        for attr_name in ("_module_win", "_db_tests_win"):
            w = getattr(self, attr_name, None)
            if w is None:
                continue
            try:
                if isinstance(w, ModuleWindow):
                    w.build_tabs_from_db()
                elif isinstance(w, DbTestsWindow):
                    w.build_tabs_from_db()
            except RuntimeError:
                pass
            except Exception:
                pass



    def open_doctor_manager(self):
        from .doctor_manager_window import DoctorManagerWindow
        self.doc_window = DoctorManagerWindow()
        self.doc_window.doctors_changed.connect(self.load_doctors)
        self.doc_window.show()
    
    def open_normal_range_editor(self):
        from .normal_range_editor import NormalRangeModuleSelectorWindow
        self.range_selector_window = NormalRangeModuleSelectorWindow(
            on_ranges_changed=self.refresh_all_structure_views
        )
        self.range_selector_window.show()

    def open_test_admin_editor(self):
        from .test_admin_editor import TestAdminModuleSelectorWindow
        self.test_admin_selector_window = TestAdminModuleSelectorWindow(
            on_tests_changed=self.refresh_all_structure_views
        )
        self.test_admin_selector_window.show()



    def open_module_admin_editor(self):
        from .module_admin_editor import ModuleAdminEditorWindow
        self.module_admin_window = ModuleAdminEditorWindow(
            on_modules_changed=self.refresh_all_structure_views
        )
        self.module_admin_window.destroyed.connect(lambda: self.refresh_all_structure_views())
        self.module_admin_window.show()


    def open_lab_print_settings(self):
        from .lab_print_settings_window import LabPrintSettingsWindow
        self.lab_print_settings_window = LabPrintSettingsWindow()
        self.lab_print_settings_window.show()



    def open_search(self):
        self.search_window = SearchWindow()
        self.search_window.show()



    def open_settings(self):
        from .settings_window import SettingsWindow
        self.settings_window = SettingsWindow(parent_main_window=self)
        self.settings_window.show()

    def check_for_updates(self):
        manifest_url = "https://aa7aa.github.io/lab_system_update_clean/manifest.json"

        try:
            identity = get_lab_identity()
            lab_id = identity["lab_id"]

            info = fetch_update_manifest(manifest_url)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Update Check",
                f"Failed to check for updates:\n{e}"
            )
            return

        if not is_lab_allowed(lab_id, info.allowed_labs):
            QMessageBox.information(
                self,
                "No Updates",
                "No updates are available for this lab right now."
            )
            return

        if is_newer_version(APP_VERSION, info.latest_version):
            notes_text = "\n".join(f"- {note}" for note in info.notes) if info.notes else "No release notes."

            reply = QMessageBox.question(
                self,
                "Update Available",
                f"Current version: {APP_VERSION}\n"
                f"Latest version: {info.latest_version}\n\n"
                f"Changes:\n{notes_text}\n\n"
                f"Do you want to download and install it now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                self.update_window = UpdateWindow(info=info, parent_main_window=self)
                self.update_window.show()
                self.update_window.raise_()
                self.update_window.activateWindow()
        else:
            QMessageBox.information(
                self,
                "No Updates",
                f"You are using the latest version ({APP_VERSION})."
            )


    def get_patient_data(self) -> PatientData:
        name = self.patient_name.text().strip()
        doctor = self.doctor.currentText().strip()
        gender = self.gender.currentText().strip()
        

        age_val = int(self.age.value())
        age = None if age_val == 0 else age_val

        date_iso = self.date.date().toString("yyyy-MM-dd")

        return PatientData(
            name=name,
            doctor=doctor,
            age=age,
            gender=gender,
            date_iso=date_iso,
        )

    def _can_open_modules(self) -> bool:
        patient_name = self.patient_name.text().strip()

        if not patient_name:
            QMessageBox.warning(
                self,
                "بيانات ناقصة",
                "يرجى إدخال اسم المريض أولاً."
            )
            self.patient_name.setFocus()
            return False

        return True



    def _ensure_report_id(self) -> str:
        if not self.report_id:
            self.report_id = str(uuid4())
        return self.report_id

    def on_module_clicked(self, module_code: str):
        if not self._can_open_modules():
            return

        patient = self.get_patient_data()
        report_id = self._ensure_report_id()

        if module_code == "Tests":
            self._db_tests_win = DbTestsWindow(patient=asdict(patient), report_id=report_id)
            self._opened_windows.append(self._db_tests_win)
            self._db_tests_win.destroyed.connect(
                lambda: self._opened_windows.remove(self._db_tests_win) if self._db_tests_win in self._opened_windows else None
            )
            self._db_tests_win.show()
            return

        if module_code == "Culture":
            from .culture_window import CultureWindow
            self._culture_win = CultureWindow(patient, report_id=report_id)
            self._culture_win.show()
            return

        if module_code == "CBC":
            self._cbc_win = CBCWindow(patient, report_id=report_id)
            self._cbc_win.show()
            return

        self._module_win = ModuleWindow(module_code=module_code, patient=patient, report_id=report_id)
        self._opened_windows.append(self._module_win)
        self._module_win.destroyed.connect(
            lambda: self._opened_windows.remove(self._module_win) if self._module_win in self._opened_windows else None
        )
        self._module_win.show()






    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)










# ----------------------------
# Entry point
# ----------------------------
def main():
    mutex = win32event.CreateMutex(None, False, "ALSHAFaqLabMutex")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        sys.exit(0)

    init_db()
    app = QApplication(sys.argv)

    apply_global_theme(app, dark=False)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()