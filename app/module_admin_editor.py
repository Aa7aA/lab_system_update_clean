from __future__ import annotations


from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QColor
from pathlib import Path
from PySide6.QtWidgets import (
    QGroupBox,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QAbstractItemView,
    QFrame,
    QToolButton,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
)

from .db import get_conn
from .ui_utils import apply_global_theme, fit_window_to_screen
from .branding import LAB_BRANDING

PROTECTED_MODULES = {"Tests", "Culture", "CBC"}


class AddEditModuleDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title: str = "Add Module",
        code: str = "",
        display_name: str = "",
        sort_order: int = 10,
        allow_code_edit: bool = True,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 280)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title_lbl = QLabel("بيانات القسم")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; background: transparent;")
        root.addWidget(title_lbl)

        form_box = QGroupBox("المعلومات الأساسية")
        form_box.setLayoutDirection(Qt.RightToLeft)
        form = QFormLayout(form_box)
        form.setContentsMargins(16, 16, 16, 16)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.code_edit = QLineEdit(code)
        self.code_edit.setReadOnly(not allow_code_edit)

        self.display_name_edit = QLineEdit(display_name)

        self.sort_spin = QSpinBox()
        self.sort_spin.setRange(0, 999999)
        self.sort_spin.setValue(int(sort_order or 0))
        self.sort_spin.setMinimumHeight(34)

        form.addRow("رمز القسم:", self.code_edit)
        form.addRow("الاسم الظاهر:", self.display_name_edit)
        form.addRow("الترتيب:", self.sort_spin)

        root.addWidget(form_box)

        row = QHBoxLayout()
        row.addStretch(1)

        btn_save = QPushButton("حفظ")
        btn_back = QPushButton("إغلاق")

        btn_save.setMinimumHeight(34)
        btn_back.setMinimumHeight(34)

        btn_back.setStyleSheet("""
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

        btn_save.clicked.connect(self.accept)
        btn_back.clicked.connect(self.reject)

        row.addWidget(btn_save)
        row.addWidget(btn_back)
        root.addLayout(row)

    def get_values(self) -> tuple[str, str, int]:
        return (
            self.code_edit.text().strip(),
            self.display_name_edit.text().strip(),
            int(self.sort_spin.value()),
        )


class ModuleAdminEditorWindow(QWidget):
    def __init__(self, on_modules_changed=None):
        super().__init__()
        self.on_modules_changed = on_modules_changed
        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        fit_window_to_screen(
            self,
            width_ratio=0.92,
            height_ratio=0.86,
            min_width=980,
            min_height=620,
        )

        self.setWindowTitle("إضافة وتعديل الأقسام")

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

        brand_title = QLabel("إضافة وتعديل الأقسام")
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

        # ---------- Actions ----------
        top_box = QGroupBox("إدارة الأقسام")
        top_box.setLayoutDirection(Qt.RightToLeft)
        top = QHBoxLayout(top_box)
        top.setContentsMargins(10, 8, 10, 8)
        top.setSpacing(8)

        self.btn_add = QPushButton("إضافة قسم")
        self.btn_edit = QPushButton("تعديل قسم")
        self.btn_delete = QPushButton("حذف قسم")
        self.btn_refresh = QPushButton("تحديث")

        self.btn_add.clicked.connect(self.add_module)
        self.btn_edit.clicked.connect(self.edit_selected_module)
        self.btn_delete.clicked.connect(self.delete_selected_module)
        self.btn_refresh.clicked.connect(self.refresh_all_views)

        for btn in (self.btn_add, self.btn_edit, self.btn_delete, self.btn_refresh):
            btn.setMinimumHeight(34)

        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #a33232;
                border: 1px solid #f0c8c8;
                border-radius: 14px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton:hover {
                background-color: #fff5f5;
                border: 1px solid #e6a8a8;
            }
        """)

        top.addWidget(self.btn_add)
        top.addWidget(self.btn_edit)
        top.addWidget(self.btn_delete)
        top.addStretch(1)
        top.addWidget(self.btn_refresh)

        self.add_soft_shadow(top_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(top_box)

        # ---------- Table ----------
        table_box = QGroupBox("جدول الأقسام")
        table_box.setLayoutDirection(Qt.RightToLeft)
        table_layout = QVBoxLayout(table_box)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(6)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "رمز القسم",
            "الاسم الظاهر",
            "الترتيب",
            "محمي",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_selected_module)
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

        self.add_soft_shadow(table_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(table_box, 1)

        # ---------- Bottom ----------
        bottom_box = QGroupBox("الإجراءات")
        bottom_box.setLayoutDirection(Qt.RightToLeft)
        bottom = QHBoxLayout(bottom_box)
        bottom.setContentsMargins(10, 8, 10, 8)
        bottom.setSpacing(8)
        bottom.addStretch(1)

        self.btn_back = QPushButton("إغلاق")
        self.btn_back.setMinimumHeight(34)
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
        self.btn_back.clicked.connect(self.close)
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


    def load_rows(self):
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT code, display_name, sort_order
                FROM modules
                ORDER BY sort_order, display_name, code
                """
            ).fetchall()

        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            code = str(row[0] or "").strip()
            display_name = str(row[1] or "").strip()
            sort_order = int(row[2] or 0)
            protected = "Yes" if code in PROTECTED_MODULES else ""

            values = [code, display_name, str(sort_order), protected]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

    def _selected_row_values(self) -> tuple[str, str, int] | None:
        row = self.table.currentRow()
        if row < 0:
            return None

        code_item = self.table.item(row, 0)
        display_item = self.table.item(row, 1)
        sort_item = self.table.item(row, 2)

        if code_item is None or display_item is None or sort_item is None:
            return None

        code = code_item.text().strip()
        display_name = display_item.text().strip()

        try:
            sort_order = int(sort_item.text().strip() or 0)
        except Exception:
            sort_order = 0

        return code, display_name, sort_order


    def _notify_modules_changed(self):
        if callable(self.on_modules_changed):
            self.on_modules_changed()

    def refresh_all_views(self):
        self.load_rows()
        self._notify_modules_changed()

    def add_module(self):
        dlg = AddEditModuleDialog(self, title="Add Module", allow_code_edit=True)
        if dlg.exec() != QDialog.Accepted:
            return

        code, display_name, sort_order = dlg.get_values()

        if not code:
            QMessageBox.warning(self, "بيانات غير صحيحة", "رمز القسم مطلوب.")
            return

        if not display_name:
            display_name = code

        with get_conn() as conn:
            dup = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM modules
                WHERE code = ?
                """,
                (code,),
            ).fetchone()

            if dup and int(dup["c"]) > 0:
                QMessageBox.warning(self, "مكرر", "يوجد قسم بهذا الرمز بالفعل.")
                return

            conn.execute(
                """
                INSERT INTO modules(code, display_name, sort_order)
                VALUES (?, ?, ?)
                """,
                (code, display_name, sort_order),
            )

        self.load_rows()
        self._notify_modules_changed()

    def edit_selected_module(self):
        selected = self._selected_row_values()
        if selected is None:
            QMessageBox.information(self, "اختيار قسم", "يرجى اختيار قسم أولاً.")
            return

        old_code, old_display_name, old_sort = selected

        dlg = AddEditModuleDialog(
            self,
            title="Edit Module",
            code=old_code,
            display_name=old_display_name,
            sort_order=old_sort,
            allow_code_edit=False,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        code, display_name, sort_order = dlg.get_values()

        if not display_name:
            display_name = code

        with get_conn() as conn:
            conn.execute(
                """
                UPDATE modules
                SET display_name = ?, sort_order = ?
                WHERE code = ?
                """,
                (display_name, sort_order, code),
            )

        self.load_rows()
        self._notify_modules_changed()

    def delete_selected_module(self):
        selected = self._selected_row_values()
        if selected is None:
            QMessageBox.information(self, "Select Module", "Select a module first.")
            return

        code, display_name, _sort_order = selected

        if code in PROTECTED_MODULES:
            QMessageBox.warning(
                self,
                "قسم محمي",
                f"القسم '{code}' محمي ولا يمكن حذفه من هنا."
            )
            return

        with get_conn() as conn:
            remaining_rows = conn.execute(
                """
                SELECT code
                FROM modules
                WHERE code NOT IN ('Tests', 'Culture', 'CBC')
                """
            ).fetchall()

        if len(remaining_rows) <= 1:
            QMessageBox.warning(
                self,
                "آخر قسم",
                "لا يمكن حذف آخر قسم متاح من هنا.\n\n"
                "أضف قسماً جديداً أولاً إذا كنت تريد إعادة تنظيم الأقسام."
            )
            return

        with get_conn() as conn:
            category_count_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM categories
                WHERE module_code = ?
                """,
                (code,),
            ).fetchone()
            category_count = int(category_count_row["c"] if category_count_row and category_count_row["c"] is not None else 0)

            test_count_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM tests
                WHERE module_code = ?
                """,
                (code,),
            ).fetchone()
            test_count = int(test_count_row["c"] if test_count_row and test_count_row["c"] is not None else 0)

            range_count_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM normal_ranges
                WHERE module_code = ?
                """,
                (code,),
            ).fetchone()
            range_count = int(range_count_row["c"] if range_count_row and range_count_row["c"] is not None else 0)

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete module '{display_name or code}'?\n\n"
            f"This will remove:\n"
            f"- {category_count} category row(s)\n"
            f"- {test_count} test row(s)\n"
            f"- {range_count} normal range row(s)\n"
            f"- linked dropdown options for its tests\n\n"
            f"Old patient report results will remain unchanged."
        )
        if confirm != QMessageBox.Yes:
            return

        with get_conn() as conn:
            test_rows = conn.execute(
                """
                SELECT id
                FROM tests
                WHERE module_code = ?
                """,
                (code,),
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
                WHERE module_code = ?
                """,
                (code,),
            )

            conn.execute(
                """
                DELETE FROM tests
                WHERE module_code = ?
                """,
                (code,),
            )

            conn.execute(
                """
                DELETE FROM categories
                WHERE module_code = ?
                """,
                (code,),
            )

            conn.execute(
                """
                DELETE FROM modules
                WHERE code = ?
                """,
                (code,),
            )

        self.load_rows()
        self._notify_modules_changed()