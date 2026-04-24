from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QAbstractItemView,
    QInputDialog,
    QFrame,
    QToolButton,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
)

from .db import get_conn
from .ui_utils import apply_global_theme, fit_window_to_screen, show_blocking_child
from .branding import LAB_BRANDING


LAYOUT_CHOICES = [
    "",
    "form",
    "single_col",
    "two_col",
    "three_col",
    "widal",
    "titers_two_col",
    "dropdown_pairs",
    "two_panel_dropdowns",
    "notes",
]


INPUT_TYPE_CHOICES = ["text", "dropdown", "buttons", "titer"]


def load_editor_modules() -> list[tuple[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT code, display_name
            FROM modules
            WHERE code <> 'CBC'
            ORDER BY sort_order, display_name, code
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




@dataclass
class TestRowData:
    test_id: int
    category_name: str
    test_name: str
    input_type: str
    sort_order: int
    col: int | None
    pos: int | None
    options_text: str


class TestAdminModuleSelectorWindow(QWidget):
    def __init__(self, on_tests_changed=None):
        super().__init__()
        self.on_tests_changed = on_tests_changed
        self.setWindowTitle("إضافة وتعديل التحاليل")
        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        fit_window_to_screen(
            self,
            width_ratio=0.9,
            height_ratio=0.82,
            min_width=920,
            min_height=560,
        )

        self._opened_windows: list[QWidget] = []

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

        brand_title = QLabel("إضافة وتعديل التحاليل")
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

        # ---------- Module chooser ----------
        self.box = QGroupBox("اختيار القسم")
        self.box.setLayoutDirection(Qt.RightToLeft)
        self.grid = QGridLayout(self.box)
        self.grid.setContentsMargins(14, 12, 14, 12)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)

        self.rebuild_module_buttons()

        self.add_soft_shadow(self.box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(self.box, 1)

        # ---------- Bottom actions ----------
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

        module_rows = load_editor_modules()

        r = c = 0
        for module_code, display_name in module_rows:
            btn = QPushButton(display_name)
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
            btn.clicked.connect(lambda checked=False, m=module_code: self.open_module_editor(m))
            self.grid.addWidget(btn, r, c)

            c += 1
            if c == 3:
                c = 0
                r += 1

    def open_module_editor(self, module_code: str):
        w = ModuleTestAdminWindow(module_code, on_tests_changed=self.on_tests_changed)
        self._opened_windows.append(w)
        w.destroyed.connect(lambda: self._opened_windows.remove(w) if w in self._opened_windows else None)
        show_blocking_child(self, w)


class AddCategoryDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, title: str = "Add Category", name: str = "", layout_type: str = "form"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 180)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(name)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(LAYOUT_CHOICES)
        self.layout_combo.setCurrentText(layout_type or "form")

        form.addRow("Category Name:", self.name_edit)
        form.addRow("Layout Type:", self.layout_combo)

        root.addLayout(form)

        row = QHBoxLayout()
        row.addStretch(1)

        btn_ok = QPushButton("Save")
        btn_cancel = QPushButton("Back")

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)
        root.addLayout(row)

    def get_values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.layout_combo.currentText().strip()


class AddEditTestDialog(QDialog):
    def __init__(
        self,
        categories: list[str],
        parent: QWidget | None = None,
        *,
        title: str = "Add Test",
        category_name: str = "",
        test_name: str = "",
        input_type: str = "text",
        sort_order: int = 10,
        col: int | None = None,
        pos: int | None = None,
        options_text: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        title_lbl = QLabel("بيانات التحليل")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; background: transparent;")
        root.addWidget(title_lbl)

        help_lbl = QLabel(
            "املأ البيانات الأساسية أولاً. الإعدادات المتقدمة اختيارية وتُستخدم فقط عند الحاجة."
        )
        help_lbl.setWordWrap(True)
        help_lbl.setStyleSheet("color: #5b6b7f; font-size: 13px; background: transparent;")
        root.addWidget(help_lbl)

        # ---------- Basic information ----------
        basic_box = QGroupBox("البيانات الأساسية")
        basic_box.setLayoutDirection(Qt.RightToLeft)
        basic_form = QFormLayout(basic_box)
        basic_form.setContentsMargins(16, 16, 16, 16)
        basic_form.setHorizontalSpacing(12)
        basic_form.setVerticalSpacing(12)

        self.test_name_edit = QLineEdit(test_name)
        self.test_name_edit.setPlaceholderText("مثال: Color")

        self.category_combo = QComboBox()
        self.category_combo.addItems(categories)
        if category_name:
            self.category_combo.setCurrentText(category_name)

        self.input_type_combo = QComboBox()
        self.input_type_combo.addItems(INPUT_TYPE_CHOICES)
        self.input_type_combo.setCurrentText(input_type or "text")

        basic_form.addRow("اسم التحليل:", self.test_name_edit)
        basic_form.addRow("الفئة:", self.category_combo)
        basic_form.addRow("نوع النتيجة:", self.input_type_combo)

        root.addWidget(basic_box)

        # ---------- Advanced settings toggle ----------
        self.btn_toggle_advanced = QPushButton("إظهار الإعدادات المتقدمة")
        self.btn_toggle_advanced.setCheckable(True)
        self.btn_toggle_advanced.setMinimumHeight(34)
        self.btn_toggle_advanced.setStyleSheet("""
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
        root.addWidget(self.btn_toggle_advanced)

        # ---------- Advanced settings ----------
        self.advanced_box = QGroupBox("الإعدادات المتقدمة")
        self.advanced_box.setLayoutDirection(Qt.RightToLeft)
        advanced_form = QFormLayout(self.advanced_box)
        advanced_form.setContentsMargins(12, 12, 12, 12)
        advanced_form.setHorizontalSpacing(10)
        advanced_form.setVerticalSpacing(8)

        self.sort_spin = QSpinBox()
        self.sort_spin.setRange(0, 999999)
        self.sort_spin.setValue(int(sort_order or 0))
        self.sort_spin.setMinimumHeight(34)

        self.col_spin = QSpinBox()
        self.col_spin.setRange(0, 3)
        self.col_spin.setSpecialValueText("")
        self.col_spin.setValue(int(col) if col is not None else 0)
        self.col_spin.setMinimumHeight(34)

        self.pos_spin = QSpinBox()
        self.pos_spin.setRange(0, 999999)
        self.pos_spin.setSpecialValueText("")
        self.pos_spin.setValue(int(pos) if pos is not None else 0)
        self.pos_spin.setMinimumHeight(34)

        self.options_edit = QLineEdit(options_text)
        self.options_edit.setPlaceholderText("للقائمة فقط: Positive | Negative | Nil")

        advanced_form.addRow("ترتيب الظهور:", self.sort_spin)
        advanced_form.addRow("العمود (1 / 2 / 3):", self.col_spin)
        advanced_form.addRow("الموضع داخل العمود:", self.pos_spin)
        advanced_form.addRow("خيارات القائمة:", self.options_edit)

        self.advanced_box.setVisible(False)
        self.btn_toggle_advanced.toggled.connect(self.advanced_box.setVisible)
        self.btn_toggle_advanced.toggled.connect(
            lambda checked: self.btn_toggle_advanced.setText(
                "إخفاء الإعدادات المتقدمة" if checked else "إظهار الإعدادات المتقدمة"
            )
        )

        root.addWidget(self.advanced_box)

        # ---------- Buttons ----------
        row = QHBoxLayout()
        row.addStretch(1)

        btn_ok = QPushButton("حفظ")
        btn_cancel = QPushButton("رجوع")

        btn_ok.setMinimumHeight(34)
        btn_cancel.setMinimumHeight(34)

        btn_cancel.setStyleSheet("""
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

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)
        root.addLayout(row)

    def get_values(self) -> dict[str, Any]:
        col_value = int(self.col_spin.value())
        pos_value = int(self.pos_spin.value())

        return {
            "test_name": self.test_name_edit.text().strip(),
            "category_name": self.category_combo.currentText().strip(),
            "input_type": self.input_type_combo.currentText().strip(),
            "sort_order": int(self.sort_spin.value()),
            "col": None if col_value == 0 else col_value,
            "pos": None if pos_value == 0 else pos_value,
            "options_text": self.options_edit.text().strip(),
        }


class ModuleTestAdminWindow(QWidget):
    def __init__(self, module_code: str, on_tests_changed=None):
        super().__init__()
        self.module_code = module_code
        self.on_tests_changed = on_tests_changed
        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        fit_window_to_screen(
            self,
            width_ratio=0.82,
            height_ratio=0.78,
            min_width=960,
            min_height=560,
        )

        self.setWindowTitle(f"إضافة وتعديل التحاليل - {module_code}")

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
        header.setFixedHeight(58)

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

        brand_title = QLabel(f"التحاليل - {module_code}")
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

        # ---------- Top actions ----------
        top_box = QGroupBox("الإجراءات")
        top_box.setLayoutDirection(Qt.RightToLeft)
        top_layout = QVBoxLayout(top_box)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(8)

        top_hint = QLabel("اختر العملية المطلوبة، ثم اختر التحليل من الجدول عند التعديل أو الحذف.")
        top_hint.setWordWrap(True)
        top_hint.setStyleSheet("""
            QLabel {
                color: #5b6b7f;
                font-size: 12px;
                background: transparent;
                padding: 0 2px 2px 2px;
            }
        """)
        top_layout.addWidget(top_hint)

        self.btn_add_category = QPushButton("إضافة فئة")
        self.btn_rename_category = QPushButton("تعديل الفئة")
        self.btn_delete_category = QPushButton("حذف فئة")

        self.btn_add_test = QPushButton("إضافة تحليل")
        self.btn_edit_test = QPushButton("تعديل المحدد")
        self.btn_delete_test = QPushButton("حذف المحدد")

        self.btn_add_category.clicked.connect(self.add_category)
        self.btn_rename_category.clicked.connect(self.rename_category)
        self.btn_delete_category.clicked.connect(self.delete_category)
        self.btn_add_test.clicked.connect(self.add_test)
        self.btn_edit_test.clicked.connect(self.edit_selected_test)
        self.btn_delete_test.clicked.connect(self.delete_selected_test)

        for btn in (
            self.btn_add_category,
            self.btn_rename_category,
            self.btn_delete_category,
            self.btn_add_test,
            self.btn_edit_test,
            self.btn_delete_test,
        ):
            btn.setMinimumHeight(32)

        self.btn_delete_category.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #a33232;
                border: 1px solid #f0c8c8;
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #fff5f5;
                border: 1px solid #e6a8a8;
            }
        """)

        self.btn_delete_test.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #a33232;
                border: 1px solid #f0c8c8;
                border-radius: 14px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #fff5f5;
                border: 1px solid #e6a8a8;
            }
        """)

        category_row = QHBoxLayout()
        category_row.setSpacing(8)
        category_label = QLabel("الفئات:")
        category_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #28415f; background: transparent;")
        category_row.addWidget(self.btn_add_category)
        category_row.addWidget(self.btn_rename_category)
        category_row.addWidget(self.btn_delete_category)
        category_row.addStretch(1)
        category_row.addWidget(category_label)

        test_row = QHBoxLayout()
        test_row.setSpacing(8)
        test_label = QLabel("التحاليل:")
        test_label.setStyleSheet("font-size: 13px; font-weight: 800; color: #28415f; background: transparent;")
        test_row.addWidget(self.btn_add_test)
        test_row.addWidget(self.btn_edit_test)
        test_row.addWidget(self.btn_delete_test)
        test_row.addStretch(1)
        test_row.addWidget(test_label)

        top_layout.addLayout(category_row)
        top_layout.addLayout(test_row)

        self.add_soft_shadow(top_box, blur=18, x=0, y=3, alpha=18)
        root.addWidget(top_box)

        # ---------- Table ----------
        table_box = QGroupBox("قائمة التحاليل الحالية")
        table_box.setLayoutDirection(Qt.RightToLeft)
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(6, 6, 6, 6)
        table_layout.setSpacing(6)

        table_help = QLabel("اختر تحليلاً من الجدول للتعديل أو الحذف.")
        table_help.setWordWrap(True)
        table_help.setStyleSheet("""
            QLabel {
                color: #5b6b7f;
                font-size: 12px;
                background: transparent;
                padding: 2px 4px 4px 4px;
            }
        """)
        table_layout.addWidget(table_help)

        table_top_row = QHBoxLayout()
        table_top_row.setContentsMargins(0, 0, 0, 0)
        table_top_row.setSpacing(8)

        self.btn_toggle_advanced_table = QPushButton("إظهار التفاصيل المتقدمة")
        self.btn_toggle_advanced_table.setCheckable(True)
        self.btn_toggle_advanced_table.setMinimumHeight(30)
        self.btn_toggle_advanced_table.setStyleSheet("""
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
        table_top_row.addWidget(self.btn_toggle_advanced_table)
        table_top_row.addStretch(1)
        table_layout.addLayout(table_top_row)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "الفئة",
            "اسم التحليل",
            "نوع النتيجة",
            "ترتيب الظهور",
            "العمود",
            "الموضع",
            "خيارات القائمة",
            "معرف التحليل",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # hidden by default to keep the view simple
        self.table.setColumnHidden(3, True)  # ترتيب الظهور
        self.table.setColumnHidden(4, True)  # العمود
        self.table.setColumnHidden(5, True)  # الموضع
        self.table.setColumnHidden(6, True)  # خيارات القائمة
        self.table.setColumnHidden(7, True)  # معرف التحليل

        self.table.doubleClicked.connect(self.edit_selected_test)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e1e8f1;
                border-radius: 12px;
                background: #ffffff;
                gridline-color: #eef2f7;
                font-size: 13px;
            }
            QHeaderView::section {
                background: #f5f8fc;
                font-weight: 800;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e6edf5;
            }
        """)
        table_layout.addWidget(self.table, 1)

        self.btn_toggle_advanced_table.toggled.connect(
            lambda checked: self.table.setColumnHidden(3, not checked)
        )
        self.btn_toggle_advanced_table.toggled.connect(
            lambda checked: self.table.setColumnHidden(4, not checked)
        )
        self.btn_toggle_advanced_table.toggled.connect(
            lambda checked: self.table.setColumnHidden(5, not checked)
        )
        self.btn_toggle_advanced_table.toggled.connect(
            lambda checked: self.table.setColumnHidden(6, not checked)
        )
        self.btn_toggle_advanced_table.toggled.connect(
            lambda checked: self.btn_toggle_advanced_table.setText(
                "إخفاء التفاصيل المتقدمة" if checked else "إظهار التفاصيل المتقدمة"
            )
        )

        self.add_soft_shadow(table_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(table_box, 1)

        # ---------- Bottom actions ----------
        bottom_box = QGroupBox("الإجراءات")
        bottom_box.setLayoutDirection(Qt.RightToLeft)
        bottom = QHBoxLayout(bottom_box)
        bottom.setContentsMargins(10, 8, 10, 8)
        bottom.setSpacing(8)
        bottom.addStretch(1)

        self.btn_refresh = QPushButton("تحديث")
        self.btn_back = QPushButton("إغلاق")

        self.btn_refresh.setMinimumHeight(32)
        self.btn_back.setMinimumHeight(32)

        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #28415f;
                border: 1px solid #dfe7f1;
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #f7fbff;
                border: 1px solid #8fc7ff;
            }
        """)

        self.btn_refresh.clicked.connect(self.refresh_all_views)
        self.btn_back.clicked.connect(self.close)

        bottom.addWidget(self.btn_refresh)
        bottom.addWidget(self.btn_back)
        self.add_soft_shadow(bottom_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(bottom_box)

        scroll.setWidget(root_frame)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

        self.load_rows()





    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)



    def showEvent(self, event):
        super().showEvent(event)
        self.load_rows()

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








    # ---------------------------
    # Data loading helpers
    # ---------------------------
    def _load_categories(self) -> list[tuple[str, str, int]]:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT name, COALESCE(layout_type, ''), sort_order
                FROM categories
                WHERE module_code = ?
                ORDER BY sort_order, name
                """,
                (self.module_code,),
            ).fetchall()
        return [(str(r[0] or ""), str(r[1] or ""), int(r[2] or 0)) for r in rows]

    def _category_names(self) -> list[str]:
        return [name for (name, _layout, _sort) in self._load_categories()]


    def load_rows(self):
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.id,
                    t.category_name,
                    t.test_name,
                    COALESCE(t.input_type, 'text') AS input_type,
                    COALESCE(t.sort_order, 0) AS sort_order,
                    t.col,
                    t.pos
                FROM tests t
                WHERE t.module_code = ?
                ORDER BY t.category_name, t.sort_order, t.pos, t.test_name
                """,
                (self.module_code,),
            ).fetchall()

            test_ids = [int(r["id"]) for r in rows]
            options_by_test_id: dict[int, list[str]] = {}

            if test_ids:
                placeholders = ",".join("?" for _ in test_ids)
                opt_rows = conn.execute(
                    f"""
                    SELECT test_id, option_value
                    FROM test_options
                    WHERE test_id IN ({placeholders})
                    ORDER BY sort_order, option_value
                    """,
                    test_ids,
                ).fetchall()
                for r in opt_rows:
                    tid = int(r["test_id"])
                    options_by_test_id.setdefault(tid, []).append(str(r["option_value"] or ""))

        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            test_id = int(row["id"])
            category_name = str(row["category_name"] or "")
            test_name = str(row["test_name"] or "")
            input_type = str(row["input_type"] or "text")
            sort_order = int(row["sort_order"] or 0)
            col = "" if row["col"] is None else str(row["col"])
            pos = "" if row["pos"] is None else str(row["pos"])
            options_text = " | ".join(options_by_test_id.get(test_id, []))

            values = [
                category_name,
                test_name,
                input_type,
                str(sort_order),
                col,
                pos,
                options_text,
                str(test_id),
            ]

            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

    def _notify_tests_changed(self):
        if callable(self.on_tests_changed):
            self.on_tests_changed()

    def refresh_all_views(self):
        self.load_rows()
        self._notify_tests_changed()

    def _selected_test_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None

        item = self.table.item(row, 7)
        if item is None:
            return None

        try:
            return int(item.text().strip())
        except Exception:
            return None

    def _selected_test_data(self) -> TestRowData | None:
        row = self.table.currentRow()
        if row < 0:
            return None

        test_id = self._selected_test_id()
        if test_id is None:
            return None

        return TestRowData(
            test_id=test_id,
            category_name=self.table.item(row, 0).text().strip(),
            test_name=self.table.item(row, 1).text().strip(),
            input_type=self.table.item(row, 2).text().strip(),
            sort_order=int(self.table.item(row, 3).text().strip() or 0),
            col=int(self.table.item(row, 4).text().strip()) if self.table.item(row, 4).text().strip() else None,
            pos=int(self.table.item(row, 5).text().strip()) if self.table.item(row, 5).text().strip() else None,
            options_text=self.table.item(row, 6).text().strip(),
        )

    # ---------------------------
    # Category operations
    # ---------------------------
    def add_category(self):
        dlg = AddCategoryDialog(self, title="Add Category", layout_type="form")
        if dlg.exec() != QDialog.Accepted:
            return

        name, layout_type = dlg.get_values()
        if not name:
            QMessageBox.warning(self, "Invalid", "Category name is required.")
            return

        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM categories
                WHERE module_code = ? AND name = ?
                """,
                (self.module_code, name),
            ).fetchone()
            if row and int(row["c"]) > 0:
                QMessageBox.warning(self, "مكرر", "هذه الفئة موجودة بالفعل في هذا القسم.")
                return

            max_sort = conn.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0) AS mx
                FROM categories
                WHERE module_code = ?
                """,
                (self.module_code,),
            ).fetchone()

            next_sort = int(max_sort["mx"] or 0) + 10

            conn.execute(
                """
                INSERT INTO categories(module_code, name, sort_order, layout_type, layout_meta)
                VALUES (?, ?, ?, ?, '')
                """,
                (self.module_code, name, next_sort, layout_type or "form"),
            )

        self.refresh_all_views()

    def rename_category(self):
        categories = self._category_names()
        if not categories:
            QMessageBox.information(self, "لا توجد فئات", "هذا القسم لا يحتوي على فئات.")
            return

        old_name, ok = QInputDialog.getItem(
            self,
            "Rename Category",
            "Choose category:",
            categories,
            0,
            False,
        )
        if not ok or not old_name:
            return

        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(layout_type, 'form') AS layout_type
                FROM categories
                WHERE module_code = ? AND name = ?
                """,
                (self.module_code, old_name),
            ).fetchone()

        current_layout = str(row["layout_type"] or "form") if row else "form"

        dlg = AddCategoryDialog(self, title="Rename Category", name=old_name, layout_type=current_layout)
        if dlg.exec() != QDialog.Accepted:
            return

        new_name, new_layout_type = dlg.get_values()
        if not new_name:
            QMessageBox.warning(self, "بيانات غير صحيحة", "اسم الفئة مطلوب.")
            return
        if old_name != new_name:
            confirm = QMessageBox.question(
                self,
                "Confirm Rename",
                f"Rename category '{old_name}' to '{new_name}'?\n\nThis will also update old saved report rows for this module."
            )
            if confirm != QMessageBox.Yes:
                return





        with get_conn() as conn:
            if old_name != new_name:
                dup = conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM categories
                    WHERE module_code = ? AND name = ?
                    """,
                    (self.module_code, new_name),
                ).fetchone()
                if dup and int(dup["c"]) > 0:
                    QMessageBox.warning(self, "Duplicate", "Another category with this name already exists.")
                    return

            conn.execute(
                """
                UPDATE categories
                SET name = ?, layout_type = ?
                WHERE module_code = ? AND name = ?
                """,
                (new_name, new_layout_type or "form", self.module_code, old_name),
            )

            conn.execute(
                """
                UPDATE tests
                SET category_name = ?
                WHERE module_code = ? AND category_name = ?
                """,
                (new_name, self.module_code, old_name),
            )

            conn.execute(
                """
                UPDATE normal_ranges
                SET category_name = ?
                WHERE module_code = ? AND category_name = ?
                """,
                (new_name, self.module_code, old_name),
            )

            conn.execute(
                """
                UPDATE report_results
                SET category = ?
                WHERE module = ? AND category = ?
                """,
                (new_name, self.module_code, old_name),
            )

        self.refresh_all_views()

    def delete_category(self):
        categories = self._category_names()
        if not categories:
            QMessageBox.information(self, "No Categories", "This module has no categories.")
            return

        name, ok = QInputDialog.getItem(
            self,
            "Delete Category",
            "Choose category:",
            categories,
            0,
            False,
        )
        if not ok or not name:
            return

        if len(categories) == 1:
            QMessageBox.warning(
                self,
                "آخر فئة",
                "لا يمكن حذف آخر فئة في هذا القسم من هنا.\n\n"
                "إذا كنت تريد إعادة بناء هذا القسم، احذف التحاليل أولاً أو غيّر بنية القسم ثم أعد ترتيبه."
            )
            return

        with get_conn() as conn:
            test_rows = conn.execute(
                """
                SELECT id, test_name
                FROM tests
                WHERE module_code = ? AND category_name = ?
                """,
                (self.module_code, name),
            ).fetchall()

            test_count = len(test_rows)

            range_count_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM normal_ranges
                WHERE module_code = ? AND category_name = ?
                """,
                (self.module_code, name),
            ).fetchone()
            range_count = int(range_count_row["c"] if range_count_row and range_count_row["c"] is not None else 0)

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete category '{name}' from module '{self.module_code}'?\n\n"
            f"This will remove:\n"
            f"- {test_count} test(s)\n"
            f"- {range_count} normal range row(s)\n\n"
            f"Old patient reports will remain unchanged.",
        )
        if confirm != QMessageBox.Yes:
            return

        with get_conn() as conn:
            test_rows = conn.execute(
                """
                SELECT id, test_name
                FROM tests
                WHERE module_code = ? AND category_name = ?
                """,
                (self.module_code, name),
            ).fetchall()

            test_ids = [int(r["id"]) for r in test_rows]

            if test_ids:
                placeholders = ",".join("?" for _ in test_ids)
                conn.execute(
                    f"DELETE FROM test_options WHERE test_id IN ({placeholders})",
                    test_ids,
                )

            conn.execute(
                """
                DELETE FROM normal_ranges
                WHERE module_code = ? AND category_name = ?
                """,
                (self.module_code, name),
            )

            conn.execute(
                """
                DELETE FROM tests
                WHERE module_code = ? AND category_name = ?
                """,
                (self.module_code, name),
            )

            conn.execute(
                """
                DELETE FROM categories
                WHERE module_code = ? AND name = ?
                """,
                (self.module_code, name),
            )

        self.refresh_all_views()

    # ---------------------------
    # Test operations
    # ---------------------------
    def add_test(self):
        categories = self._category_names()
        if not categories:
            QMessageBox.warning(self, "No Categories", "Add a category first.")
            return

        dlg = AddEditTestDialog(categories, self, title="Add Test", sort_order=10)
        if dlg.exec() != QDialog.Accepted:
            return

        values = dlg.get_values()
        test_name = values["test_name"]
        category_name = values["category_name"]
        input_type = values["input_type"]
        sort_order = values["sort_order"]
        col = values["col"]
        pos = values["pos"]
        options_text = values["options_text"]

        if not test_name:
            QMessageBox.warning(self, "بيانات غير صحيحة", "اسم التحليل مطلوب.")
            return

        with get_conn() as conn:
            dup = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM tests
                WHERE module_code = ? AND category_name = ? AND test_name = ?
                """,
                (self.module_code, category_name, test_name),
            ).fetchone()
            if dup and int(dup["c"]) > 0:
                QMessageBox.warning(self, "Duplicate", "Test already exists in this category.")
                return

            cur = conn.execute(
                """
                INSERT INTO tests(
                    module_code, category_name, test_name,
                    input_type, unit_default, sort_order, col, pos
                )
                VALUES (?, ?, ?, ?, '', ?, ?, ?)
                """,
                (self.module_code, category_name, test_name, input_type, sort_order, col, pos),
            )
            test_id = int(cur.lastrowid)

            self._replace_dropdown_options(conn, test_id, input_type, options_text)

        self.refresh_all_views()

    def edit_selected_test(self):
        data = self._selected_test_data()
        if data is None:
            QMessageBox.information(self, "اختيار تحليل", "يرجى اختيار تحليل أولاً.")
            return

        categories = self._category_names()
        if not categories:
            QMessageBox.warning(self, "No Categories", "This module has no categories.")
            return

        dlg = AddEditTestDialog(
            categories,
            self,
            title="Edit Test",
            category_name=data.category_name,
            test_name=data.test_name,
            input_type=data.input_type,
            sort_order=data.sort_order,
            col=data.col,
            pos=data.pos,
            options_text=data.options_text,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        values = dlg.get_values()
        new_test_name = values["test_name"]
        new_category_name = values["category_name"]
        new_input_type = values["input_type"]
        new_sort_order = values["sort_order"]
        new_col = values["col"]
        new_pos = values["pos"]
        new_options_text = values["options_text"]

        if not new_test_name:
            QMessageBox.warning(self, "Invalid", "Test name is required.")
            return
        if data.test_name != new_test_name or data.category_name != new_category_name:
            confirm = QMessageBox.question(
                self,
                "Confirm Edit",
                f"Apply changes to test '{data.test_name}'?\n\nThis will also update linked normal ranges and old saved report rows for this module."
            )
            if confirm != QMessageBox.Yes:
                return



        with get_conn() as conn:
            dup = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM tests
                WHERE module_code = ? AND category_name = ? AND test_name = ? AND id <> ?
                """,
                (self.module_code, new_category_name, new_test_name, data.test_id),
            ).fetchone()
            if dup and int(dup["c"]) > 0:
                QMessageBox.warning(self, "Duplicate", "Another test with this name already exists in that category.")
                return

            old_category = data.category_name
            old_test_name = data.test_name

            conn.execute(
                """
                UPDATE tests
                SET category_name = ?,
                    test_name = ?,
                    input_type = ?,
                    sort_order = ?,
                    col = ?,
                    pos = ?
                WHERE id = ?
                """,
                (
                    new_category_name,
                    new_test_name,
                    new_input_type,
                    new_sort_order,
                    new_col,
                    new_pos,
                    data.test_id,
                ),
            )

            conn.execute(
                """
                UPDATE normal_ranges
                SET category_name = ?, test_name = ?
                WHERE module_code = ? AND category_name = ? AND test_name = ?
                """,
                (
                    new_category_name,
                    new_test_name,
                    self.module_code,
                    old_category,
                    old_test_name,
                ),
            )

            conn.execute(
                """
                UPDATE report_results
                SET category = ?, test_name = ?
                WHERE module = ? AND category = ? AND test_name = ?
                """,
                (
                    new_category_name,
                    new_test_name,
                    self.module_code,
                    old_category,
                    old_test_name,
                ),
            )

            self._replace_dropdown_options(conn, data.test_id, new_input_type, new_options_text)

        self.refresh_all_views()

    def delete_selected_test(self):
        data = self._selected_test_data()
        if data is None:
            QMessageBox.information(self, "Select Test", "Select a test first.")
            return

        with get_conn() as conn:
            range_count_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM normal_ranges
                WHERE module_code = ? AND category_name = ? AND test_name = ?
                """,
                (self.module_code, data.category_name, data.test_name),
            ).fetchone()
            range_count = int(range_count_row["c"] if range_count_row and range_count_row["c"] is not None else 0)

            options_count_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM test_options
                WHERE test_id = ?
                """,
                (data.test_id,),
            ).fetchone()
            options_count = int(options_count_row["c"] if options_count_row and options_count_row["c"] is not None else 0)

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete test '{data.test_name}' from module '{self.module_code}'?\n\n"
            f"This will remove:\n"
            f"- {range_count} normal range row(s)\n"
            f"- {options_count} dropdown option row(s)\n\n"
            f"Old patient reports will remain unchanged.",
        )
        if confirm != QMessageBox.Yes:
            return

        with get_conn() as conn:
            conn.execute("DELETE FROM test_options WHERE test_id = ?", (data.test_id,))
            conn.execute(
                """
                DELETE FROM normal_ranges
                WHERE module_code = ? AND category_name = ? AND test_name = ?
                """,
                (self.module_code, data.category_name, data.test_name),
            )
            conn.execute("DELETE FROM tests WHERE id = ?", (data.test_id,))

        self.refresh_all_views()

    def _replace_dropdown_options(self, conn, test_id: int, input_type: str, options_text: str) -> None:
        conn.execute("DELETE FROM test_options WHERE test_id = ?", (test_id,))

        if input_type != "dropdown":
            return

        # Always keep a blank option first
        conn.execute(
            """
            INSERT INTO test_options(test_id, option_value, sort_order)
            VALUES (?, ?, ?)
            """,
            (test_id, "", 0),
        )

        options = [part.strip() for part in options_text.split("|")]
        options = [opt for opt in options if opt != ""]

        for idx, opt in enumerate(options, start=1):
            conn.execute(
                """
                INSERT INTO test_options(test_id, option_value, sort_order)
                VALUES (?, ?, ?)
                """,
                (test_id, opt, idx * 10),
            )


