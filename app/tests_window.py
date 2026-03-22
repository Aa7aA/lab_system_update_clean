from __future__ import annotations

from collections import defaultdict
from typing import Any
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4
import shutil

from PySide6.QtWidgets import (
    QGroupBox,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QMessageBox,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QFileDialog,
    QFrame,
    QToolButton,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt

from .db import get_conn, get_lab_setting
from .ui_builders import (
    build_three_panel_form_with_flags,
    build_single_column_form_with_flags,
    build_two_column_form_with_flags,
    build_two_panel_dropdowns_with_titer,
    build_widal_test_table,
)
from .ui_utils import make_pdf_report, group_results, print_pdf, apply_global_theme, fit_window_to_screen, apply_round_corners
from .branding import LAB_BRANDING

class TestsWindow(QWidget):
    def __init__(self, patient: dict | Any | None = None, report_id: str = ""):
        super().__init__()
        self.patient = patient or {}
        self.report_id = report_id

        self.setWindowTitle("تحاليل المختبر")
        fit_window_to_screen(
            self,
            width_ratio=0.94,
            height_ratio=0.9,
            min_width=1050,
            min_height=600,
        )

        apply_round_corners(self, 12)

        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root_frame = QFrame(self)
        root_frame.setObjectName("AppShell")

        layout = QVBoxLayout(root_frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        scroll.setWidget(root_frame)

        # -----------------------------
        # HEADER
        # -----------------------------
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(80)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(14)

        brand_logo = QLabel()
        brand_logo.setFixedSize(42, 42)
        brand_logo.setAlignment(Qt.AlignCenter)

        brand_logo_path = Path(LAB_BRANDING["logo_path"])
        if brand_logo_path.exists():
            brand_pixmap = QPixmap(str(brand_logo_path))
            brand_logo.setPixmap(
                brand_pixmap.scaled(
                    42, 42,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

        brand_text_wrap = QVBoxLayout()
        brand_text_wrap.setSpacing(0)

        brand_title = QLabel("تحاليل المختبر")
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
        # TOOLBAR (Back / Print / PDF)
        # -----------------------------
        toolbar_box = QGroupBox("الإجراءات")
        toolbar_box.setLayoutDirection(Qt.RightToLeft)
        toolbar = QHBoxLayout(toolbar_box)
        toolbar.setContentsMargins(14, 10, 14, 10)
        toolbar.setSpacing(8)

        self.btn_back = QPushButton("رجوع")
        self.btn_print = QPushButton("طباعة")
        self.btn_pdf = QPushButton("PDF")

        self.btn_back.setMinimumHeight(38)
        self.btn_print.setMinimumHeight(38)
        self.btn_pdf.setMinimumHeight(38)

        self.btn_back.clicked.connect(self.close)
        self.btn_print.clicked.connect(self.on_print_clicked)
        self.btn_pdf.clicked.connect(self.on_pdf_clicked)

        toolbar.addWidget(self.btn_print)
        toolbar.addWidget(self.btn_pdf)
        toolbar.addStretch(1)
        toolbar.addWidget(self.btn_back)

        self.add_soft_shadow(toolbar_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(toolbar_box)

        # -----------------------------
        # TABS
        # -----------------------------
        tabs_box = QGroupBox("الأقسام")
        tabs_box.setLayoutDirection(Qt.RightToLeft)
        tabs_layout = QVBoxLayout(tabs_box)
        tabs_layout.setContentsMargins(8, 8, 8, 8)
        tabs_layout.setSpacing(6)

        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.LeftToRight)        
        tabs_layout.addWidget(self.tabs)

        self.add_soft_shadow(tabs_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(tabs_box, 1)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

        # Store widgets so you can save/load later
        self.inputs_by_category: dict[str, dict[str, Any]] = {}
        self.flags_by_test: dict[str, QLabel] = {}
        self.ranges_by_test: dict[str, QLabel] = {}

        # Cache ranges: one test can now have multiple range rows
        self._range_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}

        self.build_tabs_from_db()





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











    # --------------------------------------------------
    # PATIENT
    # --------------------------------------------------
    def _patient_obj(self):
        p = self.patient
        if isinstance(p, dict):
            dd = dict(p)
            if "date_iso" not in dd:
                dd["date_iso"] = dd.get("report_date") or dd.get("date") or ""
            if "doctor" not in dd:
                dd["doctor"] = dd.get("doctor_name") or ""
            if "name" not in dd:
                dd["name"] = dd.get("patient_name") or ""
            return SimpleNamespace(**dd)
        return p

    def _ensure_report_id(self) -> str:
        if self.report_id:
            return self.report_id
        self.report_id = str(uuid4())
        return self.report_id

    def _upsert_report_header(self, conn) -> str | None:
        patient = self._patient_obj()

        patient_name = (getattr(patient, "name", "") or "").strip()
        if not patient_name:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم المريض قبل الحفظ أو الطباعة.")
            return None

        report_id = self._ensure_report_id()
        report_date = getattr(patient, "date_iso", "") or ""
        doctor_name = getattr(patient, "doctor", "") or ""
        gender = getattr(patient, "gender", "") or ""

        age = getattr(patient, "age", None)
        try:
            age = None if age in ("", None) else int(age)
        except Exception:
            age = None

        patient_code = getattr(patient, "patient_id", "") or ""

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
                doctor_name,
                gender,
                age,
                patient_code,
                1,
                report_date,
            ),
        )

        return report_id

    # --------------------------------------------------
    # RANGES + FLAGS
    # --------------------------------------------------
    def _load_ranges_cache(self, conn):
        self._range_cache.clear()
        rows = conn.execute(
            """
            SELECT
                category_name,
                test_name,
                COALESCE(range_mode, 'none') AS range_mode,
                COALESCE(gender, '') AS gender,
                age_min,
                age_max,
                COALESCE(label, '') AS label,
                COALESCE(min_value, '') AS min_value,
                COALESCE(max_value, '') AS max_value,
                COALESCE(unit, '') AS unit,
                COALESCE(normal_text, '') AS normal_text,
                COALESCE(sort_order, 0) AS sort_order
            FROM normal_ranges
            WHERE module_code = 'Tests'
            ORDER BY category_name, test_name, sort_order
            """
        ).fetchall()

        for row in rows:
            category_name = str(row["category_name"] or "")
            test_name = str(row["test_name"] or "")
            key = (category_name, test_name)

            self._range_cache.setdefault(key, []).append(
                {
                    "range_mode": str(row["range_mode"] or "none"),
                    "gender": str(row["gender"] or ""),
                    "age_min": row["age_min"],
                    "age_max": row["age_max"],
                    "label": str(row["label"] or ""),
                    "min": str(row["min_value"] or ""),
                    "max": str(row["max_value"] or ""),
                    "unit": str(row["unit"] or ""),
                    "normal_text": str(row["normal_text"] or ""),
                    "sort_order": int(row["sort_order"] or 0),
                }
            )


    def _range_rows(self, category_name: str, test_name: str) -> list[dict[str, Any]]:
        return self._range_cache.get((category_name, test_name), [])

    def _parse_float(self, value) -> float | None:
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return None




    def _patient_gender(self) -> str:
        patient = self._patient_obj()
        return str(getattr(patient, "gender", "") or "").strip()

    def _patient_age(self) -> int | None:
        patient = self._patient_obj()
        age = getattr(patient, "age", None)
        try:
            return None if age in ("", None) else int(age)
        except Exception:
            return None

    def _age_matches(self, age: int, age_min: Any, age_max: Any) -> bool:
        try:
            mn = None if age_min in ("", None) else int(age_min)
        except Exception:
            mn = None

        try:
            mx = None if age_max in ("", None) else int(age_max)
        except Exception:
            mx = None

        if mn is not None and age < mn:
            return False
        if mx is not None and age > mx:
            return False
        return True

    def _matching_range_row(self, category_name: str, test_name: str) -> dict[str, Any] | None:
        rows = self._range_rows(category_name, test_name)
        if not rows:
            return None

        patient_gender = self._patient_gender()
        patient_age = self._patient_age()

        for row in rows:
            mode = str(row.get("range_mode", "none") or "none").strip()

            if mode == "none":
                return row

            if mode == "gender":
                if not patient_gender:
                    return None
                if str(row.get("gender", "") or "").strip() == patient_gender:
                    return row

            elif mode == "age":
                if patient_age is None:
                    return None
                if self._age_matches(patient_age, row.get("age_min"), row.get("age_max")):
                    return row

            elif mode == "multiple":
                return None

        return None











    def _format_range(self, row: dict[str, Any] | None) -> str:
        if not row:
            return ""

        mode = str(row.get("range_mode", "none") or "none").strip()
        if mode != "none":
            return ""

        normal_text = str(row.get("normal_text", "") or "").strip()
        if normal_text:
            return normal_text

        mn = str(row.get("min", "") or "").strip()
        mx = str(row.get("max", "") or "").strip()
        unit = str(row.get("unit", "") or "").strip()

        if mn and mx:
            base = f"{mn} - {mx}"
        elif mn:
            base = mn
        elif mx:
            base = mx
        else:
            return ""

        return f"{base} {unit}".strip()

    def _update_one_flag(self, category_name: str, test_name: str, edit: QLineEdit, flag_lbl: QLabel):
        matched = self._matching_range_row(category_name, test_name)

        edit.setStyleSheet("")
        flag_lbl.setText("")
        flag_lbl.setStyleSheet("font-weight: 900; font-size: 14px;")

        if not matched:
            return

        mode = str(matched.get("range_mode", "none") or "none").strip()
        if mode == "multiple":
            return

        if str(matched.get("normal_text", "") or "").strip():
            return

        txt = (edit.text() or "").strip()
        if not txt:
            return

        val = self._parse_float(txt)
        mn = self._parse_float(matched.get("min", ""))
        mx = self._parse_float(matched.get("max", ""))

        if val is None or mn is None or mx is None:
            return

        if val < mn:
            flag_lbl.setText("L")
            flag_lbl.setStyleSheet("font-weight: 900; font-size: 14px; color: #1d6fe8;")
            edit.setStyleSheet("""
                background-color: #eef5ff;
                color: #124a9c;
                font-weight: 700;
                border: 1px solid #7fb2ff;
                border-radius: 10px;
            """)
        elif val > mx:
            flag_lbl.setText("H")
            flag_lbl.setStyleSheet("font-weight: 900; font-size: 14px; color: #c43737;")
            edit.setStyleSheet("""
                background-color: #fff1f1;
                color: #9a1f1f;
                font-weight: 700;
                border: 1px solid #f0a3a3;
                border-radius: 10px;
            """)




            
    def _wire_live_flags(
        self,
        category_name: str,
        inputs: dict[str, QLineEdit],
        flags: dict[str, QLabel],
        ranges: dict[str, QLabel],
    ):
        for test_name, range_lbl in ranges.items():
            matched = self._matching_range_row(category_name, test_name)
            range_lbl.setText(self._format_range(matched))

        for test_name, edit in inputs.items():
            flag_lbl = flags.get(test_name)
            if not flag_lbl:
                continue

            self._update_one_flag(category_name, test_name, edit, flag_lbl)

            edit.textChanged.connect(
                lambda _=None, cat=category_name, tn=test_name, e=edit, fl=flag_lbl:
                    self._update_one_flag(cat, tn, e, fl)
            )

    # --------------------------------------------------
    # LOAD/SAVE RESULTS
    # --------------------------------------------------
    def _load_existing_results(self, conn) -> dict[tuple[str, str], str]:
        if not self.report_id:
            return {}
        rows = conn.execute(
            """
            SELECT category, test_name, COALESCE(result,'')
            FROM report_results
            WHERE report_id = ? AND module = ?
            """,
            (self.report_id, "Tests"),
        ).fetchall()
        return {(str(cat), str(tn)): (res or "") for (cat, tn, res) in rows}

    def _read_widget_value(self, w: Any) -> str:
        if isinstance(w, QLineEdit):
            return (w.text() or "").strip()
        if isinstance(w, QComboBox):
            return (w.currentText() or "").strip()
        return ""

    def save_results(self) -> None:
        with get_conn() as conn:
            report_id = self._upsert_report_header(conn)
            if report_id is None:
                return

            for cat_name, widgets in self.inputs_by_category.items():
                for test_name, widget in widgets.items():
                    value = self._read_widget_value(widget).strip()

                    if not value:
                        conn.execute(
                            """
                            DELETE FROM report_results
                            WHERE report_id = ? AND module = ? AND category = ? AND test_name = ?
                            """,
                            (report_id, "Tests", cat_name, test_name),
                        )
                        continue

                    matched = self._matching_range_row(cat_name, test_name)

                    unit = ""
                    flag = ""

                    if isinstance(widget, QLineEdit) and matched:
                        mode = str(matched.get("range_mode", "none") or "none").strip()
                        normal_text = str(matched.get("normal_text", "") or "").strip()

                        if mode != "multiple" and not normal_text:
                            unit = str(matched.get("unit", "") or "").strip()

                            val = self._parse_float(value)
                            mn = self._parse_float(matched.get("min", ""))
                            mx = self._parse_float(matched.get("max", ""))

                            if val is not None and mn is not None and mx is not None:
                                if val < mn:
                                    flag = "L"
                                elif val > mx:
                                    flag = "H"

                    conn.execute(
                        """
                        INSERT INTO report_results(report_id, module, category, test_name, result, unit, flag)
                        VALUES(?,?,?,?,?,?,?)
                        ON CONFLICT(report_id, module, category, test_name)
                        DO UPDATE SET
                            result = excluded.result,
                            unit = excluded.unit,
                            flag = excluded.flag
                        """,
                        (report_id, "Tests", cat_name, test_name, value, unit, flag),
                    )


    def closeEvent(self, event):  # type: ignore[override]
        return super().closeEvent(event)
    # --------------------------------------------------
    # PRINT / PDF
    # --------------------------------------------------
    def _fetch_rows_for_pdf(self) -> list[dict]:
        if not self.report_id:
            return []

        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    rr.category AS category,
                    rr.test_name AS test_name,
                    COALESCE(rr.result, '') AS result,
                    COALESCE(rr.unit, '') AS unit,
                    COALESCE(rr.flag, '') AS flag
                FROM report_results rr
                WHERE rr.report_id = ? AND rr.module = 'Tests'
                AND TRIM(COALESCE(rr.result, '')) <> ''
                ORDER BY rr.category, rr.test_name
                """,
                (self.report_id,),
            ).fetchall()

        out: list[dict] = []

        for r in rows:
            category = str(r["category"] or "")
            test_name = str(r["test_name"] or "")

            all_ranges = self._range_rows(category, test_name)
            matched = self._matching_range_row(category, test_name)

            out.append(
                {
                    "category": category,
                    "test_name": test_name,
                    "result": str(r["result"] or ""),
                    "unit": str(r["unit"] or ""),
                    "flag": str(r["flag"] or ""),
                    "ranges": all_ranges,
                    "matched_range": matched,
                }
            )

        return out


    def _merge_titers_rows_for_pdf(self, rows: list[dict]) -> list[dict]:
        """
        Merge only Titers category __titer rows into the visible base rows,
        exactly like Torch behavior, while leaving all other categories unchanged.
        """
        merged: list[dict] = []
        base_rows: dict[tuple[str, str], dict] = {}
        titer_rows: dict[tuple[str, str], dict] = {}

        for row in rows:
            category = str(row.get("category", "") or "")
            test_name = str(row.get("test_name", "") or "")

            if category == "Titers" and test_name.endswith("__titer"):
                base_name = test_name[:-7]
                titer_rows[(category, base_name)] = row
            else:
                copied = dict(row)
                base_rows[(category, test_name)] = copied
                merged.append(copied)

        for key, base_row in base_rows.items():
            titer_row = titer_rows.get(key)
            if not titer_row:
                continue

            # put titer value into the 3rd printed column
            base_row["flag"] = str(titer_row.get("result", "") or "")

            # use titer ranges for Normal Range, just like Torch
            base_row["ranges"] = titer_row.get("ranges", []) or []
            base_row["matched_range"] = titer_row.get("matched_range")

        return merged






    def on_print_clicked(self) -> None:
        try:
            self.save_results()
            rows = self._fetch_rows_for_pdf()
            rows = self._merge_titers_rows_for_pdf(rows)
            if not rows:
                QMessageBox.information(self, "الطباعة", "لا توجد نتائج للطباعة.")
                return

            grouped = group_results(rows)

            with get_conn() as conn:
                footer_text = get_lab_setting(conn, "footer_text", "")

            pdf_path = make_pdf_report(
                self._patient_obj(),
                self.report_id,
                grouped,
                footer_text=footer_text,
            )
            print_pdf(pdf_path)

            QMessageBox.information(self, "الطباعة", "تم إرسال التقرير إلى الطابعة.")
        except Exception as e:
            QMessageBox.warning(self, "خطأ في الطباعة", f"فشلت عملية الطباعة:\n{e}")

    def on_pdf_clicked(self) -> None:
        try:
            self.save_results()
            rows = self._fetch_rows_for_pdf()
            rows = self._merge_titers_rows_for_pdf(rows)
            if not rows:
                QMessageBox.information(self, "PDF", "لا توجد نتائج لتصديرها.")
                return

            grouped = group_results(rows)

            with get_conn() as conn:
                footer_text = get_lab_setting(conn, "footer_text", "")

            temp_pdf = make_pdf_report(
                self._patient_obj(),
                self.report_id,
                grouped,
                footer_text=footer_text,
            )

            default_name = f"Tests_{(self.report_id or '')[:8]}.pdf"
            save_path_str, _ = QFileDialog.getSaveFileName(
                self,
                "Save PDF",
                default_name,
                "PDF Files (*.pdf)",
            )
            if not save_path_str:
                return

            save_path = Path(save_path_str)
            shutil.copyfile(temp_pdf, save_path)

            QMessageBox.information(self, "PDF", f"تم حفظ الملف:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ في PDF", f"فشل حفظ ملف PDF:\n{e}")

    # --------------------------------------------------
    # BUILD UI FROM DB
    # --------------------------------------------------
    def build_tabs_from_db(self):
        self.tabs.clear()
        self.inputs_by_category.clear()
        self.flags_by_test.clear()
        self.ranges_by_test.clear()

        with get_conn() as conn:
            self._load_ranges_cache(conn)
            existing = self._load_existing_results(conn)

            categories = conn.execute(
                """
                SELECT name, COALESCE(layout_type,''), COALESCE(layout_meta,'')
                FROM categories
                WHERE module_code = ?
                ORDER BY sort_order, name
                """,
                ("Tests",),
            ).fetchall()

            if not categories:
                lbl = QLabel("No categories found in DB for module: Tests")
                lbl.setAlignment(Qt.AlignCenter)
                self.tabs.addTab(lbl, "Empty")
                return

            legacy_layout_map = {
                "Chemical test": "three_col",
                "Thyroid test": "single_col",
                "Hematology test": "two_col",
                "Lipid Profile": "single_col",
                "Liver fun. test": "single_col",
                "Hormones test": "single_col",
                "Special": "widal",
                "Lab test": "form",
                "Titers": "titers_two_col",
            }

            for cat_name, layout_type, layout_meta in categories:
                cat_name = str(cat_name)
                lt = (layout_type or "").strip() or legacy_layout_map.get(cat_name, "form")

                tests = conn.execute(
                    """
                    SELECT id, test_name, input_type, unit_default, col, pos, sort_order
                    FROM tests
                    WHERE module_code = ? AND category_name = ?
                    ORDER BY sort_order, pos, test_name
                    """,
                    ("Tests", cat_name),
                ).fetchall()

                self.inputs_by_category[cat_name] = {}

                if lt == "widal" or cat_name.strip().lower() == "special":
                    widal_rows = [
                        "Sal.Typhi",
                        "Sal.Paratyphi B",
                        "Sal.Paratyphi C",
                        "Sal.Paratyphi D",
                    ]
                    widal_options = ["","Negative(-ve)","Positive(+ve)", "1 / 80", "1 / 160", "1 / 320"]

                    tab, widal_widgets = build_widal_test_table(
                        rows=widal_rows,
                        options=widal_options,
                        title="Widal Test",
                    )

                    for key, cb in widal_widgets.items():
                        saved_value = existing.get((cat_name, key), "")
                        cb.setCurrentText(saved_value)
                        self.inputs_by_category[cat_name][key] = cb

                    self.tabs.addTab(tab, cat_name)
                    continue

                if lt == "three_col":
                    col1, col2, col3 = [], [], []
                    for _id, test_name, _input_type, _unit, col, pos, so in tests:
                        if col == 1:
                            col1.append(test_name)
                        elif col == 2:
                            col2.append(test_name)
                        elif col == 3:
                            col3.append(test_name)

                    tab, inputs, flags, ranges = build_three_panel_form_with_flags(col1, col2, col3)

                    for tname, w in inputs.items():
                        if (cat_name, tname) in existing:
                            w.setText(existing[(cat_name, tname)])

                    self._wire_live_flags(cat_name, inputs, flags, ranges)

                    self.inputs_by_category[cat_name].update(inputs)
                    self.flags_by_test.update(flags)
                    self.ranges_by_test.update(ranges)

                    self.tabs.addTab(tab, cat_name)
                    continue

                if lt == "two_col":
                    col1, col2 = [], []
                    for _id, test_name, _input_type, _unit, col, pos, so in tests:
                        if col == 2:
                            col2.append(test_name)
                        else:
                            col1.append(test_name)

                    tab, inputs, flags, ranges = build_two_column_form_with_flags(col1, col2, cat_name)

                    for tname, w in inputs.items():
                        if (cat_name, tname) in existing:
                            w.setText(existing[(cat_name, tname)])

                    self._wire_live_flags(cat_name, inputs, flags, ranges)

                    self.inputs_by_category[cat_name].update(inputs)
                    self.flags_by_test.update(flags)
                    self.ranges_by_test.update(ranges)

                    self.tabs.addTab(tab, cat_name)
                    continue

                if lt == "single_col":
                    names = [t[1] for t in tests]
                    tab, inputs, flags, ranges = build_single_column_form_with_flags(names, cat_name)

                    for tname, w in inputs.items():
                        if (cat_name, tname) in existing:
                            w.setText(existing[(cat_name, tname)])

                    self._wire_live_flags(cat_name, inputs, flags, ranges)

                    self.inputs_by_category[cat_name].update(inputs)
                    self.flags_by_test.update(flags)
                    self.ranges_by_test.update(ranges)

                    self.tabs.addTab(tab, cat_name)
                    continue

                if lt == "titers_two_col":
                    dropdown_ids = [t[0] for t in tests if (t[2] or "") == "dropdown"]
                    options_by_test_id: dict[int, list[str]] = defaultdict(list)

                    if dropdown_ids:
                        placeholders = ",".join("?" for _ in dropdown_ids)
                        opt_rows = conn.execute(
                            f"""
                            SELECT test_id, option_value
                            FROM test_options
                            WHERE test_id IN ({placeholders})
                            ORDER BY sort_order, option_value
                            """,
                            dropdown_ids,
                        ).fetchall()
                        for test_id, val in opt_rows:
                            options_by_test_id[int(test_id)].append(val)

                    left_items: list[tuple[str, list[str]]] = []
                    right_items: list[tuple[str, list[str]]] = []

                    total_tests = len(tests)
                    split_index = max(total_tests - 10, 0)

                    for i, (test_id, test_name, input_type, unit_default, col, pos, sort_order) in enumerate(tests):
                        options = options_by_test_id.get(int(test_id), [])
                        if i >= split_index:
                            right_items.append((test_name, options))
                        else:
                            left_items.append((test_name, options))

                    tab, result_widgets, titer_widgets = build_two_panel_dropdowns_with_titer(
                        left_items,
                        right_items,
                        left_title="",
                        right_title="",
                        editable=True,
                    )

                    for test_name, cb in result_widgets.items():
                        saved_value = existing.get((cat_name, test_name), "")
                        cb.setCurrentText(saved_value)
                        self.inputs_by_category[cat_name][test_name] = cb

                    for test_name, titer_edit in titer_widgets.items():
                        titer_key = f"{test_name}__titer"
                        saved_titer = existing.get((cat_name, titer_key), "")
                        titer_edit.setText(saved_titer)
                        self.inputs_by_category[cat_name][titer_key] = titer_edit

                    self.tabs.addTab(tab, cat_name)
                    continue

                page = QWidget()
                form = QFormLayout(page)

                dropdown_ids = [t[0] for t in tests if (t[2] or "") == "dropdown"]
                options_by_test_id: dict[int, list[str]] = defaultdict(list)

                if dropdown_ids:
                    placeholders = ",".join("?" for _ in dropdown_ids)
                    opt_rows = conn.execute(
                        f"""
                        SELECT test_id, option_value
                        FROM test_options
                        WHERE test_id IN ({placeholders})
                        ORDER BY sort_order, option_value
                        """,
                        dropdown_ids,
                    ).fetchall()

                    for test_id, val in opt_rows:
                        options_by_test_id[int(test_id)].append(val)

                for test_id, test_name, input_type, unit_default, col, pos, sort_order in tests:
                    if input_type == "dropdown":
                        w = QComboBox()
                        w.setEditable(True)
                        w.setInsertPolicy(QComboBox.NoInsert)
                        w.addItem("")
                        for opt in options_by_test_id.get(int(test_id), []):
                            w.addItem(str(opt))
                        w.setCurrentText(existing.get((cat_name, test_name), ""))
                    else:
                        w = QLineEdit()
                        w.setText(existing.get((cat_name, test_name), ""))

                    form.addRow(QLabel(test_name), w)
                    self.inputs_by_category[cat_name][test_name] = w

                self.tabs.addTab(page, cat_name)