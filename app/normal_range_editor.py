from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QColor
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QComboBox,
    QFrame,
    QToolButton,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QFormLayout,
)

from .db import get_conn
from .ui_utils import apply_global_theme, fit_window_to_screen, show_blocking_child
from .branding import LAB_BRANDING




def load_range_modules() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT code
            FROM modules
            ORDER BY sort_order, display_name, code
            """
        ).fetchall()

    return [str(r["code"]) for r in rows]


class SimpleNormalRangeDialog(QDialog):
    def __init__(
        self,
        module_code: str,
        category_name: str,
        test_name: str,
        row_data: dict | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.module_code = module_code
        self.category_name = category_name
        self.test_name = test_name
        self.row_data = row_data or {}

        self.setWindowTitle("تعديل القيم الطبيعية")
        self.resize(620, 650)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root_frame = QFrame()
        root_frame.setObjectName("AppShell")

        root = QVBoxLayout(root_frame)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title_lbl = QLabel(f"التحليل: {self.test_name}")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; background: transparent;")
        root.addWidget(title_lbl)

        help_lbl = QLabel("اختر نوع القيم أولاً. سيتم إظهار الحقول المناسبة فقط.")
        help_lbl.setWordWrap(True)
        help_lbl.setStyleSheet("color: #5b6b7f; font-size: 12px; background: transparent;")
        root.addWidget(help_lbl)

        mode_box = QGroupBox("نوع القيم")
        mode_box.setLayoutDirection(Qt.RightToLeft)
        mode_form = QFormLayout(mode_box)
        mode_form.setContentsMargins(14, 14, 14, 14)
        mode_form.setHorizontalSpacing(10)
        mode_form.setVerticalSpacing(10)

        self.range_type_combo = QComboBox()
        self.range_type_combo.addItems(["none", "gender", "age", "multiple"])
        self.range_type_combo.setCurrentText(str(self.row_data.get("range_mode") or "none"))
        mode_form.addRow("نوع القيم:", self.range_type_combo)
        root.addWidget(mode_box)

        # -------- shared fields --------
        self.shared_box = QGroupBox("بيانات مشتركة")
        self.shared_box.setLayoutDirection(Qt.RightToLeft)
        shared_form = QFormLayout(self.shared_box)
        shared_form.setContentsMargins(14, 14, 14, 14)
        shared_form.setHorizontalSpacing(10)
        shared_form.setVerticalSpacing(10)

        self.unit_edit = QLineEdit(str(self.row_data.get("unit") or ""))
        self.subject_edit = QLineEdit(str(self.row_data.get("subject") or ""))
        self.normal_text_edit = QLineEdit(str(self.row_data.get("normal_text") or ""))

        self.unit_edit.setPlaceholderText("مثال: mg/dl")
        self.subject_edit.setPlaceholderText("اختياري")
        self.normal_text_edit.setPlaceholderText("اختياري")

        shared_form.addRow("الوحدة:", self.unit_edit)
        shared_form.addRow("الوصف:", self.subject_edit)
        shared_form.addRow("النص الطبيعي:", self.normal_text_edit)

        root.addWidget(self.shared_box)

        # -------- simple mode --------
        self.simple_box = QGroupBox("القيم البسيطة")
        self.simple_box.setLayoutDirection(Qt.RightToLeft)
        simple_form = QFormLayout(self.simple_box)
        simple_form.setContentsMargins(14, 14, 14, 14)
        simple_form.setHorizontalSpacing(10)
        simple_form.setVerticalSpacing(10)

        self.min_edit = QLineEdit(str(self.row_data.get("min_value") or ""))
        self.max_edit = QLineEdit(str(self.row_data.get("max_value") or ""))

        self.min_edit.setPlaceholderText("الحد الأدنى")
        self.max_edit.setPlaceholderText("الحد الأعلى")

        simple_form.addRow("الحد الأدنى:", self.min_edit)
        simple_form.addRow("الحد الأعلى:", self.max_edit)

        root.addWidget(self.simple_box)

        # -------- gender mode --------
        self.gender_box = QGroupBox("القيم حسب الجنس")
        self.gender_box.setLayoutDirection(Qt.RightToLeft)
        gender_form = QFormLayout(self.gender_box)
        gender_form.setContentsMargins(14, 14, 14, 14)
        gender_form.setHorizontalSpacing(10)
        gender_form.setVerticalSpacing(10)

        gender_rows = self.row_data.get("gender_rows") or {}

        male_row = gender_rows.get("ذكر", {})
        female_row = gender_rows.get("أنثى", {})

        self.male_min_edit = QLineEdit(str(male_row.get("min_value") or ""))
        self.male_max_edit = QLineEdit(str(male_row.get("max_value") or ""))
        self.male_label_edit = QLineEdit(str(male_row.get("label") or ""))

        self.female_min_edit = QLineEdit(str(female_row.get("min_value") or ""))
        self.female_max_edit = QLineEdit(str(female_row.get("max_value") or ""))
        self.female_label_edit = QLineEdit(str(female_row.get("label") or ""))

        self.male_min_edit.setPlaceholderText("الحد الأدنى للذكر")
        self.male_max_edit.setPlaceholderText("الحد الأعلى للذكر")
        self.male_label_edit.setPlaceholderText("وصف الذكر - مثال: Male")

        self.female_min_edit.setPlaceholderText("الحد الأدنى للأنثى")
        self.female_max_edit.setPlaceholderText("الحد الأعلى للأنثى")
        self.female_label_edit.setPlaceholderText("وصف الأنثى - مثال: Female")

        self.male_min_edit.setPlaceholderText("الحد الأدنى للذكر")
        self.male_max_edit.setPlaceholderText("الحد الأعلى للذكر")
        self.female_min_edit.setPlaceholderText("الحد الأدنى للأنثى")
        self.female_max_edit.setPlaceholderText("الحد الأعلى للأنثى")

        gender_form.addRow("الذكر - الحد الأدنى:", self.male_min_edit)
        gender_form.addRow("الذكر - الحد الأعلى:", self.male_max_edit)
        gender_form.addRow("الذكر - الوصف:", self.male_label_edit)

        gender_form.addRow("الأنثى - الحد الأدنى:", self.female_min_edit)
        gender_form.addRow("الأنثى - الحد الأعلى:", self.female_max_edit)
        gender_form.addRow("الأنثى - الوصف:", self.female_label_edit)

        root.addWidget(self.gender_box)

        # -------- age mode --------
        self.age_box = QGroupBox("القيم حسب العمر")
        self.age_box.setLayoutDirection(Qt.RightToLeft)
        age_box_layout = QVBoxLayout(self.age_box)
        age_box_layout.setContentsMargins(14, 14, 14, 14)
        age_box_layout.setSpacing(8)

        age_help = QLabel("أضف صفاً لكل فئة عمرية.")
        age_help.setStyleSheet("color: #5b6b7f; font-size: 12px; background: transparent;")
        age_box_layout.addWidget(age_help)

        self.age_rows_wrap = QVBoxLayout()
        self.age_rows_wrap.setSpacing(8)
        age_box_layout.addLayout(self.age_rows_wrap)

        self.btn_add_age_row = QPushButton("إضافة صف عمري")
        self.btn_add_age_row.setMinimumHeight(32)
        self.btn_add_age_row.clicked.connect(self.add_age_row)
        age_box_layout.addWidget(self.btn_add_age_row)

        root.addWidget(self.age_box)

        # -------- multiple mode --------
        self.multiple_box = QGroupBox("القيم المتعددة")
        self.multiple_box.setLayoutDirection(Qt.RightToLeft)
        multiple_box_layout = QVBoxLayout(self.multiple_box)
        multiple_box_layout.setContentsMargins(14, 14, 14, 14)
        multiple_box_layout.setSpacing(8)

        multiple_help = QLabel("أضف صفاً لكل حالة أو وصف مختلف.")
        multiple_help.setStyleSheet("color: #5b6b7f; font-size: 12px; background: transparent;")
        multiple_box_layout.addWidget(multiple_help)

        self.multiple_rows_wrap = QVBoxLayout()
        self.multiple_rows_wrap.setSpacing(8)
        multiple_box_layout.addLayout(self.multiple_rows_wrap)

        self.btn_add_multiple_row = QPushButton("إضافة صف متعدد")
        self.btn_add_multiple_row.setMinimumHeight(32)
        self.btn_add_multiple_row.clicked.connect(self.add_multiple_row)
        multiple_box_layout.addWidget(self.btn_add_multiple_row)

        root.addWidget(self.multiple_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_save = QPushButton("حفظ")
        self.btn_cancel = QPushButton("إغلاق")

        self.btn_save.setMinimumHeight(34)
        self.btn_cancel.setMinimumHeight(34)

        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel)
        root.addLayout(btn_row)

        self._age_row_widgets = []
        self._multiple_row_widgets = []

        for row in (self.row_data.get("age_rows") or []):
            self.add_age_row(row)

        for row in (self.row_data.get("multiple_rows") or []):
            self.add_multiple_row(row)

        self.range_type_combo.currentTextChanged.connect(self.update_mode_ui)
        self.update_mode_ui(self.range_type_combo.currentText())

        scroll.setWidget(root_frame)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)





    def _build_row_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #f8fbff;
                border: 1px solid #dfe7f1;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        return card, layout

    def add_age_row(self, row_data: dict | None = None):
        row_data = row_data or {}
        card, layout = self._build_row_card()

        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        age_min = QLineEdit(str(row_data.get("age_min") or ""))
        age_max = QLineEdit(str(row_data.get("age_max") or ""))
        min_value = QLineEdit(str(row_data.get("min_value") or ""))
        max_value = QLineEdit(str(row_data.get("max_value") or ""))
        label = QLineEdit(str(row_data.get("label") or ""))

        age_min.setPlaceholderText("من عمر")
        age_max.setPlaceholderText("إلى عمر")
        min_value.setPlaceholderText("الحد الأدنى")
        max_value.setPlaceholderText("الحد الأعلى")
        label.setPlaceholderText("وصف اختياري")

        form.addRow("العمر من:", age_min)
        form.addRow("العمر إلى:", age_max)
        form.addRow("الحد الأدنى:", min_value)
        form.addRow("الحد الأعلى:", max_value)
        form.addRow("الوصف:", label)

        layout.addLayout(form)

        btn_remove = QPushButton("حذف هذا الصف")
        btn_remove.setMinimumHeight(30)
        layout.addWidget(btn_remove)

        self.age_rows_wrap.addWidget(card)

        row_widgets = {
            "card": card,
            "age_min": age_min,
            "age_max": age_max,
            "min_value": min_value,
            "max_value": max_value,
            "label": label,
        }
        self._age_row_widgets.append(row_widgets)

        btn_remove.clicked.connect(lambda: self.remove_age_row(row_widgets))

    def remove_age_row(self, row_widgets: dict):
        card = row_widgets["card"]
        self.age_rows_wrap.removeWidget(card)
        card.deleteLater()
        if row_widgets in self._age_row_widgets:
            self._age_row_widgets.remove(row_widgets)

    def add_multiple_row(self, row_data: dict | None = None):
        row_data = row_data or {}
        card, layout = self._build_row_card()

        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        label = QLineEdit(str(row_data.get("label") or ""))
        min_value = QLineEdit(str(row_data.get("min_value") or ""))
        max_value = QLineEdit(str(row_data.get("max_value") or ""))
        normal_text = QLineEdit(str(row_data.get("normal_text") or ""))

        label.setPlaceholderText("اسم الحالة أو الوصف")
        min_value.setPlaceholderText("الحد الأدنى")
        max_value.setPlaceholderText("الحد الأعلى")
        normal_text.setPlaceholderText("نص طبيعي اختياري")

        form.addRow("الوصف:", label)
        form.addRow("الحد الأدنى:", min_value)
        form.addRow("الحد الأعلى:", max_value)
        form.addRow("النص الطبيعي:", normal_text)

        layout.addLayout(form)

        btn_remove = QPushButton("حذف هذا الصف")
        btn_remove.setMinimumHeight(30)
        layout.addWidget(btn_remove)

        self.multiple_rows_wrap.addWidget(card)

        row_widgets = {
            "card": card,
            "label": label,
            "min_value": min_value,
            "max_value": max_value,
            "normal_text": normal_text,
        }
        self._multiple_row_widgets.append(row_widgets)

        btn_remove.clicked.connect(lambda: self.remove_multiple_row(row_widgets))

    def remove_multiple_row(self, row_widgets: dict):
        card = row_widgets["card"]
        self.multiple_rows_wrap.removeWidget(card)
        card.deleteLater()
        if row_widgets in self._multiple_row_widgets:
            self._multiple_row_widgets.remove(row_widgets)

    def update_mode_ui(self, mode: str):
        mode = (mode or "none").strip()

        self.simple_box.setVisible(mode == "none")
        self.gender_box.setVisible(mode == "gender")
        self.age_box.setVisible(mode == "age")
        self.multiple_box.setVisible(mode == "multiple")

    def values(self) -> dict:
        mode = self.range_type_combo.currentText().strip() or "none"

        age_rows = []
        for row in self._age_row_widgets:
            age_rows.append({
                "age_min": row["age_min"].text().strip(),
                "age_max": row["age_max"].text().strip(),
                "min_value": row["min_value"].text().strip(),
                "max_value": row["max_value"].text().strip(),
                "label": row["label"].text().strip(),
            })

        multiple_rows = []
        for row in self._multiple_row_widgets:
            multiple_rows.append({
                "label": row["label"].text().strip(),
                "min_value": row["min_value"].text().strip(),
                "max_value": row["max_value"].text().strip(),
                "normal_text": row["normal_text"].text().strip(),
            })

        return {
            "range_mode": mode,
            "min_value": self.min_edit.text().strip(),
            "max_value": self.max_edit.text().strip(),
            "unit": self.unit_edit.text().strip(),
            "subject": self.subject_edit.text().strip(),
            "normal_text": self.normal_text_edit.text().strip(),

            "male_min": self.male_min_edit.text().strip(),
            "male_max": self.male_max_edit.text().strip(),
            "male_label": self.male_label_edit.text().strip(),

            "female_min": self.female_min_edit.text().strip(),
            "female_max": self.female_max_edit.text().strip(),
            "female_label":self.female_label_edit.text().strip(),

            "age_rows": age_rows,
            "multiple_rows": multiple_rows,
        }


class NormalRangeModuleSelectorWindow(QWidget):
    def __init__(self, on_ranges_changed=None):
        super().__init__()
        self.on_ranges_changed = on_ranges_changed
        self.setWindowTitle("تعديل القيم الطبيعية")
        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        fit_window_to_screen(
            self,
            width_ratio=0.9,
            height_ratio=0.82,
            min_width=900,
            min_height=540,
        )

        self._opened_windows = []

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        root_frame = QFrame(self)
        root_frame.setObjectName("AppShell")

        root = QVBoxLayout(root_frame)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ---------- Header ----------
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

        brand_title = QLabel("تعديل القيم الطبيعية")
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
        root.addWidget(header)

        self.box = QGroupBox("اختيار القسم")
        self.box.setLayoutDirection(Qt.RightToLeft)
        self.grid = QGridLayout(self.box)
        self.grid.setContentsMargins(14, 12, 14, 12)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)

        self.rebuild_module_buttons()

        self.add_soft_shadow(self.box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(self.box, 1)

        bottom_box = QGroupBox("الإجراءات")
        bottom_box.setLayoutDirection(Qt.RightToLeft)
        bottom = QHBoxLayout(bottom_box)
        bottom.setContentsMargins(10, 8, 10, 8)
        bottom.setSpacing(8)
        bottom.addStretch(1)

        back = QPushButton("إغلاق")
        back.setMinimumHeight(34)
        back.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #28415f;
                border: 1px solid #dfe7f1;
                border-radius: 14px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #f7fbff;
                border: 1px solid #8fc7ff;
            }
        """)
        back.clicked.connect(self.close)
        bottom.addWidget(back)

        self.add_soft_shadow(bottom_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(bottom_box)

        scroll.setWidget(root_frame)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)




    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)



    def showEvent(self, event):
        super().showEvent(event)
        self.rebuild_module_buttons()

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








    def rebuild_module_buttons(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        module_codes = load_range_modules()

        r = c = 0
        for module_name in module_codes:
            btn = QPushButton(module_name)
            btn.setLayoutDirection(Qt.LeftToRight)
            btn.setMinimumHeight(54)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #16324f;
                    border: 1px solid #e7edf5;
                    border-radius: 18px;
                    padding: 10px;
                    font-size: 15px;
                    font-weight: 800;
                }
                QPushButton:hover {
                    background-color: #f7fbff;
                    border: 1px solid #8fc7ff;
                }
            """)
            btn.clicked.connect(lambda checked=False, m=module_name: self.open_module_editor(m))
            self.grid.addWidget(btn, r, c)

            c += 1
            if c == 3:
                c = 0
                r += 1

    def open_module_editor(self, module_code: str):
        w = ModuleNormalRangeEditorWindow(module_code, on_ranges_changed=self.on_ranges_changed)
        self._opened_windows.append(w)
        w.destroyed.connect(lambda: self._opened_windows.remove(w) if w in self._opened_windows else None)
        show_blocking_child(self, w)


class ModuleNormalRangeEditorWindow(QWidget):
    def __init__(self, module_code: str, on_ranges_changed=None):
        super().__init__()
        self.module_code = module_code
        self.on_ranges_changed = on_ranges_changed
        
        self._display_to_internal_name: dict[tuple[str, str], str] = {}
        self._internal_to_display_name: dict[tuple[str, str], str] = {}
        self._display_category_to_internal: dict[str, str] = {}
        self._internal_category_to_display: dict[str, str] = {}




        self.setWindowTitle(f"تعديل القيم الطبيعية - {module_code}")
        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        fit_window_to_screen(
            self,
            width_ratio=0.96,
            height_ratio=0.9,
            min_width=1150,
            min_height=620,
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        root_frame = QFrame(self)
        root_frame.setObjectName("AppShell")

        root = QVBoxLayout(root_frame)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ---------- Header ----------
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(72)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 6, 14, 6)
        header_layout.setSpacing(12)

        brand_logo = QLabel()
        brand_logo.setFixedSize(36, 36)
        brand_logo.setAlignment(Qt.AlignCenter)

        brand_logo_path = Path(__file__).resolve().parent / "assets" / "lab_logo.png"
        if brand_logo_path.exists():
            brand_pixmap = QPixmap(str(brand_logo_path))
            brand_logo.setPixmap(
                brand_pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        brand_text_wrap = QVBoxLayout()
        brand_text_wrap.setSpacing(0)

        brand_title = QLabel(f"القيم الطبيعية - {module_code}")
        brand_title.setObjectName("BrandTitle")

        brand_subtitle = QLabel("AL-SHAFAQ LAB")
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
        root.addWidget(header)

        picker_box = QGroupBox("اختيار التحليل")
        picker_box.setLayoutDirection(Qt.RightToLeft)
        picker_layout = QVBoxLayout(picker_box)
        picker_layout.setContentsMargins(10, 10, 10, 10)
        picker_layout.setSpacing(8)

        help_label = QLabel("اختر التحليل الذي تريد تعديل قيمه الطبيعية. ليس من الضروري أن تكون كل الحقول موجودة لكل تحليل.")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("""
            QLabel {
                color: #5b6b7f;
                font-size: 12px;
                background: transparent;
            }
        """)
        picker_layout.addWidget(help_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("ابحث عن التحليل...")
        self.search_edit.setMinimumHeight(34)
        self.search_edit.textChanged.connect(self.apply_test_filter)
        picker_layout.addWidget(self.search_edit)

        self.test_list = QListWidget()
        self.test_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e1e8f1;
                border-radius: 12px;
                background: #ffffff;
                font-size: 13px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #eef2f7;
            }
            QListWidget::item:selected {
                background: #edf5ff;
                color: #16324f;
                border-radius: 8px;
            }
        """)
        self.test_list.itemDoubleClicked.connect(lambda _: self.edit_selected_test_range())
        picker_layout.addWidget(self.test_list, 1)

        self.add_soft_shadow(picker_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(picker_box, 1)

        bottom_box = QGroupBox("الإجراءات")
        bottom_box.setLayoutDirection(Qt.RightToLeft)
        bottom = QHBoxLayout(bottom_box)
        bottom.setContentsMargins(10, 8, 10, 8)
        bottom.setSpacing(8)

        self.btn_edit_selected = QPushButton("تعديل المحدد")
        self.btn_refresh = QPushButton("تحديث")
        self.btn_back = QPushButton("إغلاق")

        self.btn_edit_selected.setMinimumHeight(34)
        self.btn_refresh.setMinimumHeight(34)
        self.btn_back.setMinimumHeight(34)

        self.btn_edit_selected.clicked.connect(self.edit_selected_test_range)
        self.btn_refresh.clicked.connect(self.load_test_list)
        self.btn_back.clicked.connect(self.close)

        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #28415f;
                border: 1px solid #dfe7f1;
                border-radius: 14px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #f7fbff;
                border: 1px solid #8fc7ff;
            }
        """)

        bottom.addWidget(self.btn_edit_selected)
        bottom.addWidget(self.btn_refresh)
        bottom.addStretch(1)
        bottom.addWidget(self.btn_back)

        self.add_soft_shadow(bottom_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(bottom_box)

        scroll.setWidget(root_frame)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

        self._all_test_items = []
        self.load_test_list()

    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)



    def showEvent(self, event):
        super().showEvent(event)
        self.load_test_list()

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




    def _notify_ranges_changed(self):
        if callable(self.on_ranges_changed):
            self.on_ranges_changed()

    def _mode_label(self, mode: str) -> str:
        mapping = {
            "none": "بسيط",
            "gender": "حسب الجنس",
            "age": "حسب العمر",
            "multiple": "متعدد",
        }
        return mapping.get((mode or "none").strip(), "بسيط")

    def load_test_list(self):
        self.test_list.clear()
        self._all_test_items = []

        with get_conn() as conn:
            tests = conn.execute(
                """
                SELECT category_name, test_name
                FROM tests
                WHERE module_code = ?
                ORDER BY category_name, sort_order, pos, test_name
                """,
                (self.module_code,),
            ).fetchall()

            ranges = conn.execute(
                """
                SELECT category_name, test_name, COALESCE(range_mode, 'none') AS range_mode
                FROM normal_ranges
                WHERE module_code = ?
                ORDER BY sort_order, id
                """,
                (self.module_code,),
            ).fetchall()

        range_mode_by_test = {}
        for row in ranges:
            key = (str(row["category_name"] or ""), str(row["test_name"] or ""))
            mode = str(row["range_mode"] or "none")
            if key not in range_mode_by_test:
                range_mode_by_test[key] = mode

        for row in tests:
            category_name = str(row["category_name"] or "")
            test_name = str(row["test_name"] or "")
            mode = range_mode_by_test.get((category_name, test_name), "none")

            if (category_name, test_name) not in range_mode_by_test:
                status = "بدون قيمة طبيعية"
            else:
                status = self._mode_label(mode)

            item = QListWidgetItem(f"{test_name}   —   {category_name}   —   {status}")
            item.setData(Qt.UserRole, {
                "category_name": category_name,
                "test_name": test_name,
                "range_mode": mode,
            })
            self.test_list.addItem(item)
            self._all_test_items.append(item)

        self.apply_test_filter()

    def apply_test_filter(self):
        query = self.search_edit.text().strip().lower() if hasattr(self, "search_edit") else ""
        for i in range(self.test_list.count()):
            item = self.test_list.item(i)
            text = item.text().lower()
            item.setHidden(query not in text if query else False)

    def edit_selected_test_range(self):
        item = self.test_list.currentItem()
        if item is None:
            QMessageBox.information(self, "اختيار تحليل", "يرجى اختيار تحليل أولاً.")
            return

        data = item.data(Qt.UserRole) or {}
        category_name = str(data.get("category_name") or "")
        test_name = str(data.get("test_name") or "")

        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM normal_ranges
                WHERE module_code = ? AND category_name = ? AND test_name = ?
                ORDER BY sort_order, id
                """,
                (self.module_code, category_name, test_name),
            ).fetchall()

        if rows:
            first_row = dict(rows[0])
            gender_rows = {}
            age_rows = []
            multiple_rows = []

            for r in rows:
                rr = dict(r)
                gender_value = str(rr.get("gender") or "").strip()
                mode_value = str(rr.get("range_mode") or "none").strip()

                if gender_value:
                    gender_rows[gender_value] = rr

                if mode_value == "age":
                    age_rows.append({
                        "age_min": str(rr.get("age_min") or ""),
                        "age_max": str(rr.get("age_max") or ""),
                        "min_value": str(rr.get("min_value") or ""),
                        "max_value": str(rr.get("max_value") or ""),
                        "label": str(rr.get("label") or ""),
                    })

                if mode_value == "multiple":
                    multiple_rows.append({
                        "label": str(rr.get("label") or ""),
                        "min_value": str(rr.get("min_value") or ""),
                        "max_value": str(rr.get("max_value") or ""),
                        "normal_text": str(rr.get("normal_text") or ""),
                    })

            row_data = {
                "range_mode": str(first_row.get("range_mode") or "none"),
                "min_value": str(first_row.get("min_value") or ""),
                "max_value": str(first_row.get("max_value") or ""),
                "unit": str(first_row.get("unit") or ""),
                "subject": str(first_row.get("subject") or ""),
                "normal_text": str(first_row.get("normal_text") or ""),
                "gender_rows": gender_rows,
                "age_rows": age_rows,
                "multiple_rows": multiple_rows,
            }
        else:
            row_data = {
                "range_mode": "none",
                "min_value": "",
                "max_value": "",
                "unit": "",
                "subject": "",
                "normal_text": "",
                "gender_rows": {},
                "age_rows": [],
                "multiple_rows": [],
            }

        dlg = SimpleNormalRangeDialog(
            self.module_code,
            category_name,
            test_name,
            row_data=row_data,
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted:
            return

    

        values = dlg.values()

        with get_conn() as conn:
            conn.execute(
                """
                DELETE FROM normal_ranges
                WHERE module_code = ? AND category_name = ? AND test_name = ?
                """,
                (self.module_code, category_name, test_name),
            )

            if values["range_mode"] == "none":
                is_empty = (
                    not values["min_value"]
                    and not values["max_value"]
                    and not values["unit"]
                    and not values["subject"]
                    and not values["normal_text"]
                )

                if not is_empty:
                    conn.execute(
                        """
                        INSERT INTO normal_ranges (
                            module_code, category_name, test_name,
                            range_mode, gender, age_min, age_max, label,
                            min_value, max_value, unit, subject, normal_text, sort_order, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (
                            self.module_code,
                            category_name,
                            test_name,
                            "none",
                            "",
                            None,
                            None,
                            "",
                            values["min_value"],
                            values["max_value"],
                            values["unit"],
                            values["subject"],
                            values["normal_text"],
                            0,
                        ),
                    )

            elif values["range_mode"] == "gender":
                gender_rows = [
                    ("ذكر", values["male_min"], values["male_max"], values["male_label"], 0),
                    ("أنثى", values["female_min"], values["female_max"], values["female_label"], 1),
                ]

                for gender_value, min_value, max_value, label_value, sort_order in gender_rows:
                    is_empty = (
                        not min_value
                        and not max_value
                        and not label_value
                        and not values["unit"]
                        and not values["subject"]
                        and not values["normal_text"]
                    )
                    if is_empty:
                        continue

                    conn.execute(
                        """
                        INSERT INTO normal_ranges (
                            module_code, category_name, test_name,
                            range_mode, gender, age_min, age_max, label,
                            min_value, max_value, unit, subject, normal_text, sort_order, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (
                            self.module_code,
                            category_name,
                            test_name,
                            "gender",
                            gender_value,
                            None,
                            None,
                            label_value,
                            min_value,
                            max_value,
                            values["unit"],
                            values["subject"],
                            values["normal_text"],
                            sort_order,
                        ),
                    )

            elif values["range_mode"] == "age":
                for sort_order, row in enumerate(values["age_rows"]):
                    is_empty = (
                        not row["age_min"]
                        and not row["age_max"]
                        and not row["min_value"]
                        and not row["max_value"]
                        and not row["label"]
                        and not values["unit"]
                        and not values["subject"]
                        and not values["normal_text"]
                    )
                    if is_empty:
                        continue

                    conn.execute(
                        """
                        INSERT INTO normal_ranges (
                            module_code, category_name, test_name,
                            range_mode, gender, age_min, age_max, label,
                            min_value, max_value, unit, subject, normal_text, sort_order, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (
                            self.module_code,
                            category_name,
                            test_name,
                            "age",
                            "",
                            row["age_min"] if row["age_min"] else None,
                            row["age_max"] if row["age_max"] else None,
                            row["label"],
                            row["min_value"],
                            row["max_value"],
                            values["unit"],
                            values["subject"],
                            values["normal_text"],
                            sort_order,
                        ),
                    )

            elif values["range_mode"] == "multiple":
                for sort_order, row in enumerate(values["multiple_rows"]):
                    is_empty = (
                        not row["label"]
                        and not row["min_value"]
                        and not row["max_value"]
                        and not row["normal_text"]
                        and not values["unit"]
                        and not values["subject"]
                    )
                    if is_empty:
                        continue

                    conn.execute(
                        """
                        INSERT INTO normal_ranges (
                            module_code, category_name, test_name,
                            range_mode, gender, age_min, age_max, label,
                            min_value, max_value, unit, subject, normal_text, sort_order, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (
                            self.module_code,
                            category_name,
                            test_name,
                            "multiple",
                            "",
                            None,
                            None,
                            row["label"],
                            row["min_value"],
                            row["max_value"],
                            values["unit"],
                            values["subject"],
                            row["normal_text"],
                            sort_order,
                        ),
                    )

            conn.commit()

        QMessageBox.information(self, "تم الحفظ", f"تم تحديث القيم الطبيعية للتحليل:\n{test_name}")
        self.refresh_all_views()

    def _torch_titer_name_map(self) -> list[tuple[str, str, str]]:
        """
        Returns:
            (visible_category, visible_test_name, internal_test_name)
        The visible names are shown in the editor.
        The internal name is what Torch PDF/range lookup expects.
        """
        return [
            ("IgG", "Toxo IgG", "TOXO IgG-Ab__titer"),
            ("IgG", "Rubella IgG", "Rubella IgG-Ab__titer"),
            ("IgG", "CMV IgG", "CMV IgG-Ab__titer"),
            ("IgG", "HSV-1 IgG", "HSV I -IgG- Ab__titer"),
            ("IgG", "HSV-2 IgG", "HSV II -IgG- Ab__titer"),

            ("IgM", "Toxo IgM", "TOXO IgM-Ab__titer"),
            ("IgM", "Rubella IgM", "Rubella IgM-Ab__titer"),
            ("IgM", "CMV IgM", "CMV IgM-Ab__titer"),
            ("IgM", "HSV-1 IgM", "HSV I -IgM- Ab__titer"),
            ("IgM", "HSV-2 IgM", "HSV II -IgM- Ab__titer"),
        ]




    def refresh_all_views(self):
        self.load_test_list()
        self._notify_ranges_changed()



