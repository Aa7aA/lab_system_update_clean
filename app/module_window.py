from __future__ import annotations

from typing import Any, cast
from collections import defaultdict
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4
import shutil

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QTextEdit,
    QMessageBox,
    QGroupBox,
    QSpacerItem,
    QSizePolicy,
    QPushButton,
    QFileDialog,
    QFrame,
    QToolButton,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
)

from .db import get_conn, get_lab_setting
from .ui_builders import (
    build_three_panel_form_with_flags,
    build_single_column_form_with_flags,
    build_two_column_form_with_flags,
    build_three_panel_mixed_form_with_flags,
    build_single_column_mixed_form_with_flags,
    build_two_column_mixed_form_with_flags,
    build_dropdown_pairs,
    build_two_panel_dropdowns,
    build_notes_tab,
    build_two_panel_keylabel_dropdowns,
    build_torch_two_panel_dropdowns,
)

# Uses your reportlab-based PDF code from ui_utils.py
from .ui_utils import (
    make_pdf_report,
    make_pdf_gue_report,
    make_pdf_gse_report,
    make_pdf_hvs_report,
    group_results,
    print_pdf,
    apply_global_theme,
    fit_window_to_screen,
    apply_round_corners,
    make_pdf_sputum_report,
)

from .branding import LAB_BRANDING



class ModuleWindow(QWidget):
    report_finalized = Signal()
    """
    Generic DB-driven module window.

    - Tabs come from DB table `categories` for a module_code.
    - Each tab builds inputs based on DB table `tests`.
    - Saves results into `report_results` on close (UPSERT).
    - Adds live H/L flags for numeric QLineEdit fields using `normal_ranges`.
    """

    def __init__(self, module_code: str, patient: Any | None = None, report_id: str = ""):
        super().__init__()
        self.module_code = (module_code or "").strip()
        self.patient = patient
        self.report_id = report_id
        self._report_finalized = False

        self.setWindowTitle(self.module_code)
        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        fit_window_to_screen(
            self,
            width_ratio=0.94,
            height_ratio=0.9,
            min_width=1050,
            min_height=600,
        )
        apply_round_corners(self, 12)


        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root_frame = QFrame(self)
        root_frame.setObjectName("AppShell")

        layout = QVBoxLayout(root_frame)
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

        brand_title = QLabel(self.module_code)
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

        self.add_soft_shadow(toolbar_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(toolbar_box)

        # -----------------------------
        # TABS
        # -----------------------------
        tabs_box = QGroupBox("الأقسام")
        tabs_box.setLayoutDirection(Qt.RightToLeft)
        tabs_layout = QVBoxLayout(tabs_box)
        tabs_layout.setContentsMargins(6, 6, 6, 6)
        tabs_layout.setSpacing(4)

        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.LeftToRight)
        tabs_layout.addWidget(self.tabs)

        self.add_soft_shadow(tabs_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(tabs_box, 1)

        scroll.setWidget(root_frame)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

        # Cache ranges for flags
        self._range_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}

        # Widget registry for saving/loading: (category, test_name, widget, unit)
        self._registry: list[tuple[str, str, Any, str]] = []

        self.build_tabs_from_db()
        

    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)

    def _make_bold_test_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: 800; font-size: 14px;")
        return lbl

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






    # --------------------------------------------------
    # PATIENT (ui_utils uses getattr(patient, "..."))
    # --------------------------------------------------
    def _patient_obj(self):
        """
        ui_utils.make_pdf_report() uses getattr(patient, "name"/"doctor"/"date_iso"...)
        Your patient sometimes comes as dict, so we convert it to SimpleNamespace.
        """
        p = self.patient
        if isinstance(p, dict):
            dd = dict(p)
            # common fallbacks
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
    # PRINT / PDF helpers
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
                LEFT JOIN categories c
                    ON c.module_code = rr.module
                AND c.name = rr.category
                LEFT JOIN tests t
                    ON t.module_code = rr.module
                AND t.category_name = rr.category
                AND t.test_name = rr.test_name
                WHERE rr.report_id = ? AND rr.module = ?
                AND TRIM(COALESCE(rr.result, '')) <> ''
                ORDER BY
                    COALESCE(c.sort_order, 999999),
                    rr.category,
                    COALESCE(t.sort_order, 999999),
                    COALESCE(t.pos, 999999),
                    rr.test_name
                """,
                (self.report_id, self.module_code),
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



    def _merge_torch_rows_for_pdf(self, rows: list[dict]) -> list[dict]:
        merged: list[dict] = []
        base_rows: dict[tuple[str, str], dict] = {}
        titer_rows: dict[tuple[str, str], dict] = {}

        for row in rows:
            category = str(row.get("category", "") or "")
            test_name = str(row.get("test_name", "") or "")

            if test_name.endswith("__titer"):
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

            base_row["flag"] = str(titer_row.get("result", "") or "")
            base_row["ranges"] = titer_row.get("ranges", []) or []
            base_row["matched_range"] = titer_row.get("matched_range")

        return merged





    def on_print_clicked(self) -> None:
        try:
            self.save_results()

            rows = self._fetch_rows_for_pdf()
            if not rows:
                QMessageBox.information(self, "الطباعة", "لا توجد نتائج للطباعة.")
                return

            with get_conn() as conn:
                footer_text = get_lab_setting(conn, "footer_text", "")

            if self.module_code.strip().lower() == "gue":
                temp_pdf = make_pdf_gue_report(
                    self._patient_obj(),
                    self.report_id,
                    rows,
                    footer_text=footer_text,
                )
            elif self.module_code.strip().lower() == "gse":
                temp_pdf = make_pdf_gse_report(
                    self._patient_obj(),
                    self.report_id,
                    rows,
                    footer_text=footer_text,
                )
            elif self.module_code.strip().lower() in {"sputum", "sputum+"}:
                temp_pdf = make_pdf_sputum_report(
                    self._patient_obj(),
                    self.report_id,
                    rows,
                    footer_text=footer_text,
                )
            elif self.module_code.strip().lower() == "torch":
                merged_rows = self._merge_torch_rows_for_pdf(rows)
                grouped = group_results(merged_rows)
                temp_pdf = make_pdf_report(
                    self._patient_obj(),
                    self.report_id,
                    grouped,
                    footer_text=footer_text,
                    flag_header="Titer",
                )
            else:
                grouped = group_results(rows)
                temp_pdf = make_pdf_report(
                    self._patient_obj(),
                    self.report_id,
                    grouped,
                    footer_text=footer_text,
                )

            print_pdf(temp_pdf)
            self._report_finalized = True
            QMessageBox.information(self, "الطباعة", "تم إرسال التقرير إلى الطابعة.")
        except Exception as e:
            QMessageBox.warning(self, "خطأ في الطباعة", f"فشلت عملية الطباعة:\n{e}")

    def on_pdf_clicked(self) -> None:
        try:
            self.save_results()

            rows = self._fetch_rows_for_pdf()
            if not rows:
                QMessageBox.information(self, "PDF", "لا توجد نتائج لتصديرها.")
                return

            with get_conn() as conn:
                footer_text = get_lab_setting(conn, "footer_text", "")

                if self.module_code.strip().lower() == "gue":
                    temp_pdf = make_pdf_gue_report(
                        self._patient_obj(),
                        self.report_id,
                        rows,
                        footer_text=footer_text,
                    )
                elif self.module_code.strip().lower() == "gse":
                    temp_pdf = make_pdf_gse_report(
                        self._patient_obj(),
                        self.report_id,
                        rows,
                        footer_text=footer_text,
                    )
                elif self.module_code.strip().lower() == "torch":
                    merged_rows = self._merge_torch_rows_for_pdf(rows)
                    grouped = group_results(merged_rows)
                    temp_pdf = make_pdf_report(
                        self._patient_obj(),
                        self.report_id,
                        grouped,
                        footer_text=footer_text,
                        flag_header="Titer",
                    )
                elif self.module_code.strip().lower() in {"sputum", "sputum+"}:
                    temp_pdf = make_pdf_sputum_report(
                        self._patient_obj(),
                        self.report_id,
                        rows,
                        footer_text=footer_text,
                    )
                else:
                    grouped = group_results(rows)
                    temp_pdf = make_pdf_report(
                        self._patient_obj(),
                        self.report_id,
                        grouped,
                        footer_text=footer_text,
                    )

            default_name = f"{self.module_code}_{(self.report_id or '')[:8]}.pdf"
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
            self._report_finalized = True
            QMessageBox.information(self, "PDF", f"تم حفظ الملف:\n{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "خطأ في PDF", f"فشل حفظ ملف PDF:\n{e}")

    # --------------------------------------------------
    # RANGES + FLAGS
    # --------------------------------------------------
    def _load_ranges_cache(self) -> None:
        self._range_cache.clear()

        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    category_name,
                    test_name,
                    COALESCE(range_mode,'none') AS range_mode,
                    COALESCE(gender,'') AS gender,
                    age_min,
                    age_max,
                    COALESCE(label,'') AS label,
                    COALESCE(min_value,'') AS min_value,
                    COALESCE(max_value,'') AS max_value,
                    COALESCE(unit,'') AS unit,
                    COALESCE(normal_text,'') AS normal_text,
                    COALESCE(sort_order,0) AS sort_order
                FROM normal_ranges
                WHERE module_code = ?
                ORDER BY category_name, test_name, sort_order
                """,
                (self.module_code,),
            ).fetchall()

        for r in rows:
            key = (str(r["category_name"] or ""), str(r["test_name"] or ""))

            self._range_cache.setdefault(key, []).append(
                {
                    "range_mode": str(r["range_mode"] or "none"),
                    "gender": str(r["gender"] or ""),
                    "age_min": r["age_min"],
                    "age_max": r["age_max"],
                    "label": str(r["label"] or ""),
                    "min": str(r["min_value"] or ""),
                    "max": str(r["max_value"] or ""),
                    "unit": str(r["unit"] or ""),
                    "normal_text": str(r["normal_text"] or ""),
                    "sort_order": int(r["sort_order"] or 0),
                }
            )

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

    def _calc_flag(self, category_name: str, test_name: str, value_text: str) -> str:
        matched = self._matching_range_row(category_name, test_name)

        if not matched:
            return ""

        mode = str(matched.get("range_mode", "none") or "none").strip()
        if mode == "multiple":
            return ""

        if str(matched.get("normal_text", "") or "").strip():
            return ""

        v = self._parse_float(value_text)
        mn = self._parse_float(matched.get("min", ""))
        mx = self._parse_float(matched.get("max", ""))

        if v is None or mn is None or mx is None:
            return ""

        if v < mn:
            return "L"
        if v > mx:
            return "H"
        return "N"

    def _update_one_flag(self, category_name: str, test_name: str, edit: QLineEdit, flag_lbl: QLabel) -> None:
        matched = self._matching_range_row(category_name, test_name)

        flag_lbl.setText("")
        flag_lbl.setStyleSheet("font-weight: 900; font-size: 14px;")
        edit.setStyleSheet("")

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

        flag = self._calc_flag(category_name, test_name, txt)

        if flag == "L":
            flag_lbl.setText("L")
            flag_lbl.setStyleSheet("font-weight: 900; font-size: 14px; color: #1d6fe8;")
            edit.setStyleSheet("""
                background-color: #eef5ff;
                color: #124a9c;
                font-weight: 700;
                border: 1px solid #7fb2ff;
                border-radius: 10px;
            """)
        elif flag == "H":
            flag_lbl.setText("H")
            flag_lbl.setStyleSheet("font-weight: 900; font-size: 14px; color: #c43737;")
            edit.setStyleSheet("""
                background-color: #fff1f1;
                color: #9a1f1f;
                font-weight: 700;
                border: 1px solid #f0a3a3;
                border-radius: 10px;
            """)
        elif flag == "N":
            flag_lbl.setText("N")
            flag_lbl.setStyleSheet("font-weight: 900; font-size: 14px; color: #178a45;")
            edit.setStyleSheet("""
                background-color: #eefaf1;
                color: #146c37;
                font-weight: 700;
                border: 1px solid #8fd1a6;
                border-radius: 10px;
            """)


    def _wire_live_flags(
        self,
        category_name: str,
        inputs: dict[str, Any],
        flags: dict[str, QLabel],
        ranges: dict[str, QLabel],
    ) -> None:
        if not self._range_cache:
            self._load_ranges_cache()

        for test_name, range_lbl in ranges.items():
            matched = self._matching_range_row(category_name, test_name)
            range_lbl.setText(self._format_range(matched))

        for test_name, widget in inputs.items():
            flag_lbl = flags.get(test_name)
            if not flag_lbl:
                continue

            # Flags only apply to numeric text inputs, not dropdowns
            if not isinstance(widget, QLineEdit):
                flag_lbl.setText("")
                widget.setStyleSheet("")
                continue

            self._update_one_flag(category_name, test_name, widget, flag_lbl)
            widget.textChanged.connect(
                lambda _=None, cat=category_name, tn=test_name, e=widget, fl=flag_lbl:
                    self._update_one_flag(cat, tn, e, fl)
            )

    # --------------------------------------------------
    # MODULE OVERRIDES
    # --------------------------------------------------
    def _build_torch_override(self) -> None:
        left = [
            "TOXO IgM-Ab",
            "TOXO IgG-Ab",
            ".",
            "Rubella IgM-Ab",
            "Rubella IgG-Ab",
            ".",
            "CMV IgM-Ab",
            "CMV IgG-Ab",
            ".",
        ]
        right = [
            "HSV I -IgM- Ab",
            "HSV I -IgG- Ab",
            ".",
            "HSV II -IgM- Ab",
            "HSV II -IgG- Ab",
        ]
        options = ["", "Negative", "Positive"]

        tab, result_widgets, titer_widgets = build_torch_two_panel_dropdowns(
            left_tests=left,
            right_tests=right,
            options=options,
            left_title="",
            right_title="",
        )

        existing = self._load_existing_results()
        cat_name = "Torch"
        self._registry.clear()

        for test_name, cb in result_widgets.items():
            cb.setCurrentText(existing.get((cat_name, test_name), ""))
            self._registry.append((cat_name, test_name, cb, ""))

        for test_name, te in titer_widgets.items():
            titer_key = f"{test_name}__titer"
            te.setText(existing.get((cat_name, titer_key), ""))
            self._registry.append((cat_name, titer_key, te, ""))

        self.tabs.addTab(tab, "Torch")

    def _build_gue_override(self) -> None:
        physical_keys = {
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
        }

        micro_keys = {
            "pus_cell",
            "rbc",
            "epith_cell",
            "casts",
            "crystals_1",
            "crystals_2",
            "bacteria",
            "other_1",
            "other_2",
        }

        def norm(name: str) -> str:
            return (name or "").strip().lower()

        def pretty_label(name: str) -> str:
            n = name.replace("_", " ").strip()
            if norm(name) == "rbc":
                return "R.B.C"
            if norm(name) == "sp_gravity":
                return "SP.Gravity"
            if norm(name) == "epith_cell":
                return "Epith Cell"
            if norm(name) == "pus_cell":
                return "Pus cell"
            if norm(name) == "bile_pigment":
                return "Bile Pigment"
            if norm(name) == "ketone_bodies":
                return "Ketone Bodies"
            if norm(name) in {"crystals_1", "crystals_2"}:
                return "Crystals"
            if norm(name) in {"other_1", "other_2"}:
                return "Other"
            return n

        with get_conn() as conn:
            cats = conn.execute(
                """
                SELECT name
                FROM categories
                WHERE module_code=?
                ORDER BY sort_order
                """,
                (self.module_code,),
            ).fetchall()

            if not cats:
                lbl = QLabel("No categories found for GUE in DB.")
                lbl.setAlignment(Qt.AlignCenter)
                self.tabs.addTab(lbl, "GUE")
                return

            real_cat = str(cats[0][0])

            tests = conn.execute(
                """
                SELECT id, test_name, input_type
                FROM tests
                WHERE module_code=? AND category_name=?
                ORDER BY sort_order, pos, test_name
                """,
                (self.module_code, real_cat),
            ).fetchall()

            all_ids = [int(t[0]) for t in tests]
            options_by_test_id: dict[int, list[str]] = defaultdict(list)

            if all_ids:
                placeholders = ",".join("?" for _ in all_ids)
                opt_rows = conn.execute(
                    f"""
                    SELECT test_id, option_value
                    FROM test_options
                    WHERE test_id IN ({placeholders})
                    ORDER BY sort_order, option_value
                    """,
                    all_ids,
                ).fetchall()

                for tid, val in opt_rows:
                    options_by_test_id[int(tid)].append(str(val))

            existing: dict[tuple[str, str], str] = {}
            if getattr(self, "report_id", ""):
                rows = conn.execute(
                    """
                    SELECT category, test_name, COALESCE(result,'')
                    FROM report_results
                    WHERE report_id=? AND module=?
                    """,
                    (self.report_id, self.module_code),
                ).fetchall()
                existing = {(str(c), str(tn)): (r or "") for (c, tn, r) in rows}

        physical_tests = []
        micro_tests = []
        unknown_tests = []

        for test_id, test_name, input_type in tests:
            k = norm(test_name)
            if k in physical_keys:
                physical_tests.append((test_id, test_name, input_type))
            elif k in micro_keys:
                micro_tests.append((test_id, test_name, input_type))
            else:
                unknown_tests.append((test_id, test_name, input_type))

        micro_tests.extend(unknown_tests)

        tab = QWidget()
        tab.setLayoutDirection(Qt.LeftToRight)
        outer = QHBoxLayout(tab)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(26)

        def make_panel(title: str, tests_rows):
            box = QGroupBox(title)
            form = QFormLayout(box)
            form.setLabelAlignment(Qt.AlignLeft)
            form.setFormAlignment(Qt.AlignTop)
            form.setHorizontalSpacing(18)
            form.setVerticalSpacing(10)

            widgets = []
            for test_id, test_name, _input_type in tests_rows:
                cb = QComboBox()
                cb.setEditable(True)
                cb.setInsertPolicy(QComboBox.NoInsert)
                cb.addItem("")
                for opt in options_by_test_id.get(int(test_id), []):
                    cb.addItem(opt)
                saved_value = existing.get((real_cat, test_name), "")

                if saved_value:
                    cb.setCurrentText(saved_value)
                elif title == "Physically Examination" and cb.count() > 1:
                    cb.setCurrentIndex(1)
                elif title == "Microscopical Examination" and norm(test_name) in {"casts", "bacteria", "epith_cell", "other_1"} and cb.count() > 1:
                    cb.setCurrentIndex(1)

                form.addRow(self._make_bold_test_label(pretty_label(test_name)), cb)
                widgets.append((test_name, cb))

            form.addRow(QLabel(""), QLabel(""))
            return box, widgets

        left_box, left_widgets = make_panel("Physically Examination", physical_tests)
        right_box, right_widgets = make_panel("Microscopical Examination", micro_tests)

        outer.addWidget(left_box, 1)
        outer.addWidget(right_box, 1)

        self._registry.clear()
        for test_name, w in left_widgets:
            self._registry.append((real_cat, test_name, w, ""))
        for test_name, w in right_widgets:
            self._registry.append((real_cat, test_name, w, ""))

        self.tabs.addTab(tab, "GUE")


    def _build_gse_override(self) -> None:
        with get_conn() as conn:
            cats = conn.execute(
                """
                SELECT name
                FROM categories
                WHERE module_code=?
                ORDER BY sort_order
                """,
                (self.module_code,),
            ).fetchall()

            if not cats:
                lbl = QLabel("No categories found for GSE in DB.")
                lbl.setAlignment(Qt.AlignCenter)
                self.tabs.addTab(lbl, "GSE")
                return

            real_cat = str(cats[0][0])

            tests = conn.execute(
                """
                SELECT id, test_name, input_type
                FROM tests
                WHERE module_code=? AND category_name=?
                ORDER BY sort_order, pos, test_name
                """,
                (self.module_code, real_cat),
            ).fetchall()

            all_ids = [int(t[0]) for t in tests]
            options_by_test_id: dict[int, list[str]] = defaultdict(list)

            if all_ids:
                placeholders = ",".join("?" for _ in all_ids)
                opt_rows = conn.execute(
                    f"""
                    SELECT test_id, option_value
                    FROM test_options
                    WHERE test_id IN ({placeholders})
                    ORDER BY sort_order, option_value
                    """,
                    all_ids,
                ).fetchall()

                for tid, val in opt_rows:
                    options_by_test_id[int(tid)].append(str(val))

            existing: dict[tuple[str, str], str] = {}
            if getattr(self, "report_id", ""):
                rows = conn.execute(
                    """
                    SELECT category, test_name, COALESCE(result,'')
                    FROM report_results
                    WHERE report_id=? AND module=?
                    """,
                    (self.report_id, self.module_code),
                ).fetchall()
                existing = {(str(c), str(tn)): (r or "") for (c, tn, r) in rows}

        physical_names = [
            "Color",
            "Consistency",
            "pH",
        ]

        micro_names = [
            "R.b.cs",
            "Pus cell",
            "Cyst",
            "Trophzoite",
            "Ova",
            "Monilia",
            "Fatty droplt",
            "Undigested food",
            "Other",
        ]

        def norm(name: str) -> str:
            return (name or "").strip().lower()

        physical_set = {norm(x) for x in physical_names}
        micro_set = {norm(x) for x in micro_names}

        left_items: list[tuple[str, str, list[str]]] = []
        right_items: list[tuple[str, str, list[str]]] = []

        tests_by_name = {norm(str(name)): (int(tid), str(name)) for tid, name, _input_type in tests}

        for display_name in physical_names:
            key = norm(display_name)
            if key in tests_by_name:
                tid, real_name = tests_by_name[key]
                left_items.append((real_name, display_name, options_by_test_id.get(tid, [])))

        for display_name in micro_names:
            key = norm(display_name)
            if key in tests_by_name:
                tid, real_name = tests_by_name[key]
                right_items.append((real_name, display_name, options_by_test_id.get(tid, [])))

        for tid, test_name, _input_type in tests:
            key = norm(test_name)
            if key not in physical_set and key not in micro_set:
                right_items.append((str(test_name), str(test_name), options_by_test_id.get(int(tid), [])))

        tab, widgets = build_two_panel_keylabel_dropdowns(
            left_items,
            right_items,
            left_title="physically Examination",
            right_title="Microscopical Examination",
            editable=True,
        )

        self._registry.clear()

        for test_name, cb in widgets.items():
            cb.setCurrentText(existing.get((real_cat, test_name), ""))
            self._registry.append((real_cat, test_name, cb, ""))

        self.tabs.addTab(tab, "GSE")













    # NOTE: keep your other overrides exactly as you already wrote them:
    # _build_sfa_override, _build_sputum_plus_override, _build_gse_override,
    # _build_stone_override, _build_hvs_override
    #
    # If you already have them below in your file, keep them as-is.
    #
    # --------------------------------------------------
    # DB UI BUILD
    # --------------------------------------------------

    def _get_categories(self):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT name, COALESCE(layout_type, ''), COALESCE(layout_meta, ''), sort_order
                FROM categories
                WHERE module_code = ?
                ORDER BY sort_order, name
                """,
                (self.module_code,),
            ).fetchall()

    def _get_tests_for_category(self, category_name: str):
        with get_conn() as conn:
            return conn.execute(
                """
                SELECT id, test_name, input_type, unit_default, sort_order, col, pos
                FROM tests
                WHERE module_code = ? AND category_name = ?
                ORDER BY sort_order, pos, test_name
                """,
                (self.module_code, category_name),
            ).fetchall()

    def _get_options_for_test_ids(self, test_ids: list[int]):
        if not test_ids:
            return {}
        placeholders = ",".join(["?"] * len(test_ids))
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
        opts: dict[int, list[str]] = {}
        for tid, v in rows:
            opts.setdefault(int(tid), []).append(str(v))
        return opts

    def _load_existing_results(self) -> dict[tuple[str, str], str]:
        if not self.report_id:
            return {}
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT category, test_name, COALESCE(result,'')
                FROM report_results
                WHERE report_id = ? AND module = ?
                """,
                (self.report_id, self.module_code),
            ).fetchall()
        return {(str(cat), str(tn)): (res or "") for (cat, tn, res) in rows}

    def build_tabs_from_db(self) -> None:
        self.tabs.clear()
        self._registry.clear()

        code = self.module_code.strip().lower()

        # Your custom overrides (keep your existing ones)
        if code == "torch":
            self._build_torch_override()
            return
        if code == "gue":
            self._build_gue_override()
            return

        # If you already implemented these overrides in your current file,
        # keep them below and these will call them:
        if hasattr(self, "_build_sfa_override") and code == "sfa":
            self._build_sfa_override()
            return
        if hasattr(self, "_build_sputum_plus_override") and code == "sputum":
            self._build_sputum_plus_override()
            return
        if hasattr(self, "_build_gse_override") and code == "gse":
            self._build_gse_override()
            return
        if hasattr(self, "_build_stone_override") and code == "stone":
            self._build_stone_override()
            return
        if hasattr(self, "_build_hvs_override") and code == "hvs":
            self._build_hvs_override()
            return

        cats = self._get_categories()
        if not cats:
            w = QWidget()
            lay = QVBoxLayout(w)
            msg = QLabel(
                f"No categories/tests found in DB for module code: {self.module_code}\n"
                f"Add rows to `modules`, `categories`, `tests` tables."
            )
            msg.setWordWrap(True)
            msg.setAlignment(Qt.AlignCenter)
            lay.addWidget(msg)
            self.tabs.addTab(w, "Empty")
            return

        existing = self._load_existing_results()

        for (cat_name, layout_type, layout_meta, _sort) in cats:
            cat_name = str(cat_name)
            layout_type = (str(layout_type) or "").strip().lower()

            tests = self._get_tests_for_category(cat_name)
            if not tests:
                empty = QWidget()
                lay = QVBoxLayout(empty)
                lab = QLabel("No tests configured for this category.")
                lab.setAlignment(Qt.AlignCenter)
                lay.addWidget(lab)
                self.tabs.addTab(empty, cat_name)
                continue

            text_tests: list[tuple[int, str, str, str, int, int | None, int | None]] = []
            dd_tests: list[tuple[int, str, str, str, int, int | None, int | None]] = []
            ta_tests: list[tuple[int, str, str, str, int, int | None, int | None]] = []

            for row in tests:
                tid, tname, itype, unit, sort_order, col, pos = row
                itype = (str(itype) or "text").strip().lower()
                tup = (
                    int(tid),
                    str(tname),
                    itype,
                    str(unit or ""),
                    int(sort_order or 0),
                    cast(int | None, col),
                    cast(int | None, pos),
                )
                if itype == "dropdown":
                    dd_tests.append(tup)
                elif itype == "textarea":
                    ta_tests.append(tup)
                else:
                    text_tests.append(tup)

            options_by_id = self._get_options_for_test_ids([t[0] for t in dd_tests])

            if dd_tests and not text_tests and not ta_tests and layout_type in {"dropdown_pairs", "pairs"}:
                pairs = [(t[1], options_by_id.get(t[0], [])) for t in dd_tests]
                tab, widgets = build_dropdown_pairs(pairs, title=cat_name, editable=True)
                for t in dd_tests:
                    test_name = t[1]
                    cb = widgets.get(test_name)
                    if cb:
                        cb.setCurrentText(existing.get((cat_name, test_name), ""))
                        self._registry.append((cat_name, test_name, cb, ""))
                self.tabs.addTab(tab, cat_name)
                continue

            if dd_tests and not text_tests and not ta_tests and layout_type in {"two_panel_dropdowns", "2panel_dropdowns"}:
                pairs = [(t[1], options_by_id.get(t[0], [])) for t in dd_tests]
                tab, widgets = build_two_panel_dropdowns(
                    pairs, left_title="Left", right_title="Right", editable=True
                )
                for t in dd_tests:
                    test_name = t[1]
                    cb = widgets.get(test_name)
                    if cb:
                        cb.setCurrentText(existing.get((cat_name, test_name), ""))
                        self._registry.append((cat_name, test_name, cb, ""))
                self.tabs.addTab(tab, cat_name)
                continue

            if ta_tests and not text_tests and not dd_tests and layout_type in {"notes", "note"}:
                tab, te = build_notes_tab(title=cat_name)
                first_name = ta_tests[0][1]
                te.setPlainText(existing.get((cat_name, first_name), ""))
                self._registry.append((cat_name, first_name, te, ""))
                self.tabs.addTab(tab, cat_name)
                continue

            if layout_type in {"three_panel", "three_col", "three_column"}:
                col1, col2, col3 = [], [], []

                for t in tests:
                    tid, tname, itype, unit, so, col, pos = t
                    row_def = (str(tname), str(itype or "text"), options_by_id.get(int(tid), []))

                    if col == 1:
                        col1.append(row_def)
                    elif col == 2:
                        col2.append(row_def)
                    elif col == 3:
                        col3.append(row_def)
                    else:
                        col1.append(row_def)

                tab, inputs, flags, ranges = build_three_panel_mixed_form_with_flags(col1, col2, col3)

                for tname, w in inputs.items():
                    saved = existing.get((cat_name, tname), "")
                    if isinstance(w, QComboBox):
                        w.setCurrentText(saved)
                    else:
                        w.setText(saved)

                self._wire_live_flags(cat_name, inputs, flags, ranges)

                for tname, w in inputs.items():
                    self._registry.append((cat_name, tname, w, ""))

                self.tabs.addTab(tab, cat_name)
                continue

            if layout_type in {"two_col", "two_column", "2col"}:
                col1, col2 = [], []

                for t in tests:
                    tid, tname, itype, unit, so, col, pos = t
                    row_def = (str(tname), str(itype or "text"), options_by_id.get(int(tid), []))

                    if col == 2:
                        col2.append(row_def)
                    else:
                        col1.append(row_def)

                tab, inputs, flags, ranges = build_two_column_mixed_form_with_flags(col1, col2, cat_name)

                for tname, w in inputs.items():
                    saved = existing.get((cat_name, tname), "")
                    if isinstance(w, QComboBox):
                        w.setCurrentText(saved)
                    else:
                        w.setText(saved)

                self._wire_live_flags(cat_name, inputs, flags, ranges)

                for tname, w in inputs.items():
                    self._registry.append((cat_name, tname, w, ""))

                self.tabs.addTab(tab, cat_name)
                continue

            if text_tests and layout_type in {"keylabel_dropdowns"} and dd_tests:
                left_items = [(t[1], t[1], options_by_id.get(t[0], [])) for t in dd_tests if (t[5] or 1) == 1]
                right_items = [(t[1], t[1], options_by_id.get(t[0], [])) for t in dd_tests if (t[5] or 2) == 2]
                tab, widgets = build_two_panel_keylabel_dropdowns(
                    left_items, right_items, left_title="", right_title="", editable=True
                )
                for t in dd_tests:
                    test_name = t[1]
                    cb = widgets.get(test_name)
                    if cb:
                        cb.setCurrentText(existing.get((cat_name, test_name), ""))
                        self._registry.append((cat_name, test_name, cb, ""))
                self.tabs.addTab(tab, cat_name)
                continue

            if layout_type in {"single_col", "single_column", "form"}:
                row_defs = [
                    (str(t[1]), str(t[2] or "text"), options_by_id.get(int(t[0]), []))
                    for t in tests
                ]

                tab, inputs, flags, ranges = build_single_column_mixed_form_with_flags(row_defs, cat_name)

                for tname, w in inputs.items():
                    saved = existing.get((cat_name, tname), "")
                    if isinstance(w, QComboBox):
                        w.setCurrentText(saved)
                    else:
                        w.setText(saved)

                self._wire_live_flags(cat_name, inputs, flags, ranges)

                for tname, w in inputs.items():
                    self._registry.append((cat_name, tname, w, ""))

                self.tabs.addTab(tab, cat_name)
                continue

            tab = QWidget()
            tab.setLayoutDirection(Qt.LeftToRight)
            outer = QVBoxLayout(tab)
            form = QFormLayout()
            form.setLabelAlignment(Qt.AlignLeft)
            outer.addLayout(form)

            for (tid, test_name, itype, unit, _so, _col, _pos) in (text_tests + dd_tests + ta_tests):
                if itype == "dropdown":
                    cb = QComboBox()
                    cb.setEditable(True)
                    cb.setInsertPolicy(QComboBox.NoInsert)
                    cb.addItem("")
                    for opt in options_by_id.get(tid, []):
                        cb.addItem(opt)
                    cb.setCurrentText(existing.get((cat_name, test_name), ""))
                    form.addRow(self._make_bold_test_label(test_name), cb)
                    self._registry.append((cat_name, test_name, cb, ""))
                elif itype == "textarea":
                    te = QTextEdit()
                    te.setMinimumHeight(120)
                    te.setPlainText(existing.get((cat_name, test_name), ""))
                    form.addRow(self._make_bold_test_label(test_name), te)
                    self._registry.append((cat_name, test_name, te, ""))
                else:
                    ed = QLineEdit()
                    ed.setText(existing.get((cat_name, test_name), ""))
                    form.addRow(self._make_bold_test_label(test_name), ed)
                    self._registry.append((cat_name, test_name, ed, unit or ""))

            self.tabs.addTab(tab, cat_name)

    # --------------------------------------------------
    # SAVE / CLOSE
    # --------------------------------------------------
    def _read_widget_value(self, w: Any) -> str:
        if isinstance(w, QLineEdit):
            return (w.text() or "").strip()
        if isinstance(w, QComboBox):
            return (w.currentText() or "").strip()
        if isinstance(w, QTextEdit):
            return (w.toPlainText() or "").strip()
        return ""

    def save_results(self) -> None:
        if not self._range_cache:
            self._load_ranges_cache()

        with get_conn() as conn:
            report_id = self._upsert_report_header(conn)
            if report_id is None:
                return

            for (category, test_name, widget, unit) in self._registry:
                value = self._read_widget_value(widget).strip()

                if not value:
                    conn.execute(
                        """
                        DELETE FROM report_results
                        WHERE report_id = ? AND module = ? AND category = ? AND test_name = ?
                        """,
                        (report_id, self.module_code, category, test_name),
                    )
                    continue

                matched = self._matching_range_row(category, test_name)

                unit = ""
                flag = ""

                if isinstance(widget, QLineEdit) and matched:
                    mode = str(matched.get("range_mode", "none") or "none").strip()
                    normal_text = str(matched.get("normal_text", "") or "").strip()

                    if mode != "multiple" and not normal_text:
                        unit = str(matched.get("unit", "") or "").strip()
                        flag = self._calc_flag(category, test_name, value)

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
                    (report_id, self.module_code, category, test_name, value, unit, flag),
                )


    def closeEvent(self, event):  # type: ignore[override]
        if self._report_finalized:
            self.report_finalized.emit()
        return super().closeEvent(event)