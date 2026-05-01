# app/culture_window.py
from __future__ import annotations

from uuid import uuid4

from PySide6.QtGui import QPixmap, QColor
from pathlib import Path


from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGroupBox,
    QGridLayout,
    QLabel,
    QComboBox,
    QMessageBox,
    QFrame,
    QToolButton,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
)

from .db import get_conn, get_lab_setting
from .ui_builders import build_antibiotics_table_three_columns
from .ui_utils import (
    make_pdf_culture_report,
    print_pdf_and_delete,
    save_pdf_automatically,
    widget_set_value,
    group_results,
    apply_global_theme,
    apply_round_corners,
)
from .branding import LAB_BRANDING



class CultureWindow(QMainWindow):
    report_finalized = Signal()
    def __init__(self, patient, report_id: str | None = None):
        super().__init__()
        self.patient = patient
        self.report_id: str | None = report_id
        self._report_finalized = False

        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setWindowTitle("Sensitivity")
        self.resize(1200, 720)
        apply_round_corners(self, 12)


        root = QFrame()
        root.setObjectName("AppShell")
        root.setLayoutDirection(Qt.LeftToRight)




        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)


        # -----------------------------
        # HEADER
        # -----------------------------
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(72)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 6, 14, 6)
        header_layout.setSpacing(12)

        brand_logo = QLabel()
        brand_logo.setFixedSize(36, 36)
        brand_logo.setAlignment(Qt.AlignCenter)

        brand_logo_path = Path(LAB_BRANDING["logo_path"])
        if brand_logo_path.exists():
            brand_pixmap = QPixmap(str(brand_logo_path))
            brand_logo.setPixmap(
                brand_pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        brand_text_wrap = QVBoxLayout()
        brand_text_wrap.setSpacing(0)

        brand_title = QLabel("Sensitivity")
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
        header_buttons.setSpacing(8)


        self.btn_minimize = QToolButton()
        self.btn_minimize.setObjectName("HeaderIconButton")
        self.btn_minimize.setText("—")
        self.btn_minimize.clicked.connect(self.showMinimized)

        self.btn_close = QToolButton()
        self.btn_close.setObjectName("HeaderIconButton")
        self.btn_close.setText("✕")
        self.btn_close.clicked.connect(self.close)


        header_buttons.addWidget(self.btn_minimize)
        header_buttons.addWidget(self.btn_close)

        header_right = QWidget()
        header_right.setLayout(header_buttons)

        header_layout.addWidget(header_left, 1)
        header_layout.addWidget(header_right, 0)

        self.add_soft_shadow(header, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(header)



        # -----------------------------
        # TOOLBAR
        # -----------------------------
        toolbar_box = QGroupBox("الإجراءات")
        toolbar_box.setLayoutDirection(Qt.RightToLeft)
        toolbar = QHBoxLayout(toolbar_box)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(8)

        self.btn_back = QPushButton("رجوع")
        self.btn_print = QPushButton("طباعة")
        self.btn_pdf = QPushButton("PDF")
        self.btn_paid = QPushButton("تم الدفع")
        self.btn_paid.setCheckable(True)

        self.btn_back.setMinimumHeight(34)
        self.btn_print.setMinimumHeight(34)
        self.btn_pdf.setMinimumHeight(34)
        self.btn_paid.setMinimumHeight(34)
        self.btn_paid.setCursor(Qt.PointingHandCursor)
        self.btn_paid.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #146c37;
                border: 1px solid #b7e4c7;
                border-radius: 16px;
                padding: 9px 18px;
                font-size: 14px;
                font-weight: 900;
            }

            QPushButton:hover {
                background-color: #f0fff4;
                border: 2px solid #52b788;
                color: #0f5132;
            }

            QPushButton:pressed {
                background-color: #d8f3dc;
                border: 2px solid #40916c;
                padding-top: 11px;
                padding-bottom: 7px;
            }

            QPushButton:checked {
                background-color: #d8f3dc;
                color: #0f5132;
                border: 2px solid #2d6a4f;
            }

            QPushButton:checked:hover {
                background-color: #b7e4c7;
                border: 2px solid #1b4332;
            }

            QPushButton:checked:pressed {
                background-color: #95d5b2;
                border: 2px solid #1b4332;
                padding-top: 11px;
                padding-bottom: 7px;
            }
        """)

        self.btn_paid.setMinimumWidth(110)

        self.btn_back.clicked.connect(self.close)
        self.btn_print.clicked.connect(self.on_print)
        self.btn_pdf.clicked.connect(self.on_pdf)
        

        toolbar.addWidget(self.btn_print)
        toolbar.addWidget(self.btn_pdf)
        toolbar.addWidget(self.btn_paid)
        toolbar.addStretch(1)
        toolbar.addWidget(self.btn_back)

        layout.addWidget(toolbar_box)







        # ----------------------------
        # Sample + Result
        # ----------------------------
        top = QGroupBox("")
        top.setLayoutDirection(Qt.LeftToRight)
        tg = QGridLayout(top)
        tg.setHorizontalSpacing(12)
        tg.setVerticalSpacing(10)

        self.culture_inputs: dict[str, QComboBox] = {}

        culture_rows = self._get_test_rows("Culture")
        culture_ids = [int(r["id"]) for r in culture_rows]
        culture_options = self._get_options_for_test_ids(culture_ids)

        self.sample = None
        self.result = None

        culture_row_index = 0
        for row in culture_rows:
            test_id = int(row["id"])
            test_name = str(row["test_name"] or "")
            options = culture_options.get(test_id, [""])

            combo = self._make_editable_combo(options)
            self.culture_inputs[test_name] = combo

            if test_name == "Sample":
                self.sample = combo
            elif test_name == "Result":
                self.result = combo

            tg.addWidget(self._make_bold_test_label(f"{test_name}:"), culture_row_index, 0)
            tg.addWidget(combo, culture_row_index, 1)
            culture_row_index += 1

        layout.addWidget(top)

        # ----------------------------
        # Antibiotics (3 columns)
        # ----------------------------
        abx_rows = self._get_test_rows("Antibiotics")
        abx_ids = [int(r["id"]) for r in abx_rows]
        abx_options_by_id = self._get_options_for_test_ids(abx_ids)

        antibiotics = [str(r["test_name"] or "") for r in abx_rows]

        merged_options: list[str] = [""]
        for row in abx_rows:
            opts = abx_options_by_id.get(int(row["id"]), [])
            for opt in opts:
                if opt not in merged_options:
                    merged_options.append(opt)

        abx_widget, self.abx_inputs = build_antibiotics_table_three_columns(
            antibiotics,
            options=merged_options,
            splits=(10, 20),
        )

        abx_box = QGroupBox("")
        abx_box.setLayoutDirection(Qt.LeftToRight)
        vb = QVBoxLayout(abx_box)
        vb.addWidget(abx_widget)
        layout.addWidget(abx_box, 1)





        scroll.setWidget(root)
        self.setCentralWidget(scroll)

        if self.report_id is not None:
            self.load_report_into_fields(self.report_id)




    def _get_test_rows(self, category_name: str):
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, test_name, COALESCE(input_type, 'text') AS input_type
                FROM tests
                WHERE module_code = 'Culture' AND category_name = ?
                ORDER BY sort_order, pos, test_name
                """,
                (category_name,),
            ).fetchall()
        return rows

    def _get_options_for_test_ids(self, test_ids: list[int]) -> dict[int, list[str]]:
        if not test_ids:
            return {}

        placeholders = ",".join("?" for _ in test_ids)
        with get_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT test_id, option_value
                FROM test_options
                WHERE test_id IN ({placeholders})
                ORDER BY sort_order, option_value
                """,
                test_ids,
            ).fetchall()

        out: dict[int, list[str]] = {}
        for test_id, option_value in rows:
            out.setdefault(int(test_id), []).append(str(option_value or ""))
        return out

    def _make_editable_combo(self, options: list[str]) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        cb.setInsertPolicy(QComboBox.NoInsert)

        seen: set[str] = set()
        for opt in options:
            text = str(opt or "")
            if text not in seen:
                cb.addItem(text)
                seen.add(text)

        if "" not in seen:
            cb.insertItem(0, "")

        return cb


    def _make_bold_test_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: 800; font-size: 14px;")
        return lbl



    # ---------------------------------
    # DB save/load
    # ---------------------------------

    def _collect_results(self) -> list[dict]:
        rows: list[dict] = []

        def add(category: str, test_name: str, value: str):
            rows.append(
                {
                    "category": category,
                    "test_name": test_name,
                    "result": (value or "").strip(),
                    "unit": "",
                    "min_value": "",
                    "max_value": "",
                    "flag": "",
                }
            )

        for test_name, combo in self.culture_inputs.items():
            value = (combo.currentText() or "").strip()
            if value:
                add("Culture", test_name, value)

        for ab, combo in self.abx_inputs.items():
            value = (combo.currentText() or "").strip()
            add("Antibiotics", ab, value)

        return rows

    def _ensure_report_id(self) -> str:
        if self.report_id:
            return self.report_id
        self.report_id = str(uuid4())
        return self.report_id

    def _upsert_header_and_results(self) -> tuple[str | None, int, list[dict]]:
        patient_name = (getattr(self.patient, "name", "") or "").strip()
        if patient_name == "":
            QMessageBox.warning(self, "Warning", "Please enter patient name before saving/printing.")
            return None, 0, []

        report_date = getattr(self.patient, "date_iso", "") or ""
        report_id = self._ensure_report_id()
        results = self._collect_results()

        # Always keep copies = 1 (UI removed)
        copies = 1

        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO reports (
                    report_id, patient_name, doctor_name, gender, age,
                    patient_code, copies, report_date, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(report_id) DO UPDATE SET
                    patient_name=excluded.patient_name,
                    doctor_name=excluded.doctor_name,
                    gender=excluded.gender,
                    age=excluded.age,
                    patient_code=excluded.patient_code,
                    copies=excluded.copies,
                    report_date=excluded.report_date,
                    updated_at=datetime('now');
                """,
                (
                    report_id,
                    patient_name,
                    getattr(self.patient, "doctor", "") or "",
                    getattr(self.patient, "gender", "") or "",
                    getattr(self.patient, "age", None),
                    getattr(self.patient, "patient_id", "") or "",
                    copies,
                    report_date,
                ),
            )

            for r in results:
                conn.execute(
                    """
                    INSERT INTO report_results (
                        report_id, module, category, test_name,
                        result, unit, min_value, max_value, flag
                    )
                    VALUES (?, 'Culture', ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(report_id, module, category, test_name)
                    DO UPDATE SET
                        result=excluded.result,
                        unit=excluded.unit,
                        min_value=excluded.min_value,
                        max_value=excluded.max_value,
                        flag=excluded.flag;
                    """,
                    (
                        report_id,
                        r["category"],
                        r["test_name"],
                        r["result"],
                        r["unit"],
                        r["min_value"],
                        r["max_value"],
                        r["flag"],
                    ),
                )

        return report_id, len(results), results

    # ---------------------------------
    # Button actions
    # ---------------------------------

    def on_print(self) -> None:
        report_id, count, results = self._upsert_header_and_results()
        if report_id is None:
            return

        grouped = group_results(results)

        with get_conn() as conn:
            footer_text = get_lab_setting(conn, "footer_text", "")

        pdf_path = make_pdf_culture_report(
            self.patient,
            report_id,
            grouped,
            footer_text=footer_text,
            paid_marker=self.btn_paid.isChecked(),
        )
        print_pdf_and_delete(pdf_path)
        self._report_finalized = True
        QMessageBox.information(self, "Done", f"Saved + printed.\nResults: {count}\nReportID: {report_id[:8]}")

    def on_pdf(self) -> None:
        report_id, count, results = self._upsert_header_and_results()
        if report_id is None:
            return

        grouped = group_results(results)

        with get_conn() as conn:
            footer_text = get_lab_setting(conn, "footer_text", "")

        pdf_path = make_pdf_culture_report(
            self.patient,
            report_id,
            grouped,
            footer_text=footer_text,
            paid_marker=self.btn_paid.isChecked(),
        )

        patient_name = getattr(self.patient, "name", "") or "patient"

        out = save_pdf_automatically(
            self,
            pdf_path,
            patient_name=patient_name,
        )

        if out:
            self._report_finalized = True
            QMessageBox.information(self, "Saved", f"PDF saved.\nResults: {count}\nFile:\n{out}")

    # ---------------------------------
    # Load existing
    # ---------------------------------

    def load_report_into_fields(self, report_id: str):
        for combo in self.culture_inputs.values():
            combo.setCurrentIndex(0)
        for combo in self.abx_inputs.values():
            combo.setCurrentIndex(0)

        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT category, test_name, result
                FROM report_results
                WHERE report_id = ? AND module = 'Culture'
                """,
                (report_id,),
            ).fetchall()

        for category, test_name, result in rows:
            if category == "Culture":
                if test_name in self.culture_inputs:
                    widget_set_value(self.culture_inputs[test_name], result)
            elif category == "Antibiotics":
                if test_name in self.abx_inputs:
                    widget_set_value(self.abx_inputs[test_name], result)



    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)



    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


    def closeEvent(self, event):
        if self._report_finalized:
            self.report_finalized.emit()
        super().closeEvent(event)


                    