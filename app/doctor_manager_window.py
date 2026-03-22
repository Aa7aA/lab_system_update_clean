from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPixmap
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QMessageBox, QFrame, QLabel,
    QToolButton, QGroupBox, QGraphicsDropShadowEffect, QApplication, QScrollArea
)

from .ui_utils import apply_global_theme, apply_round_corners

from .db import get_conn
from .branding import LAB_BRANDING

class DoctorManagerWindow(QWidget):
    doctors_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("إدارة الأطباء")
        self.resize(760, 620)
        apply_round_corners(self, 12)

    


        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False

        self.conn = get_conn()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        root = QFrame(self)
        root.setObjectName("AppShell")

        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ---------------- Header ----------------
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(88)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        header_layout.setSpacing(14)

        brand_logo = QLabel()
        brand_logo.setFixedSize(46, 46)
        brand_logo.setAlignment(Qt.AlignCenter)

        brand_logo_path = Path(LAB_BRANDING["logo_path"])
        if brand_logo_path.exists():
            brand_pixmap = QPixmap(str(brand_logo_path))
            brand_logo.setPixmap(
                brand_pixmap.scaled(
                    46, 46,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

        brand_text_wrap = QVBoxLayout()
        brand_text_wrap.setSpacing(0)

        brand_title = QLabel("إدارة الأطباء")
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

        # ---------------- Search/Add card ----------------
        editor_box = QGroupBox("إضافة أو تعديل طبيب")
        editor_box.setLayoutDirection(Qt.RightToLeft)
        editor_layout = QHBoxLayout(editor_box)
        editor_layout.setContentsMargins(18, 18, 18, 18)
        editor_layout.setSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم الطبيب")
        self.name_input.setMinimumHeight(46)

        self.btn_add = QPushButton("إضافة")
        self.btn_add.setMinimumHeight(46)
        self.btn_add.clicked.connect(self.add_doctor)

        self.btn_edit = QPushButton("تعديل")
        self.btn_edit.setMinimumHeight(46)
        self.btn_edit.clicked.connect(self.edit_doctor)

        self.btn_delete = QPushButton("حذف")
        self.btn_delete.setMinimumHeight(46)
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
        """)
        self.btn_delete.clicked.connect(self.delete_doctor)

        editor_layout.addWidget(self.name_input, 1)
        editor_layout.addWidget(self.btn_add)
        editor_layout.addWidget(self.btn_edit)
        editor_layout.addWidget(self.btn_delete)

        self.add_soft_shadow(editor_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(editor_box)

        # ---------------- Doctors list card ----------------
        list_box = QGroupBox("قائمة الأطباء")
        list_box.setLayoutDirection(Qt.RightToLeft)
        list_layout = QVBoxLayout(list_box)
        list_layout.setContentsMargins(18, 18, 18, 18)
        list_layout.setSpacing(12)

        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e1e8f1;
                border-radius: 14px;
                background: #ffffff;
                padding: 8px;
                font-size: 14px;
            }
            QListWidget::item {
                border-radius: 10px;
                padding: 10px 12px;
                margin: 4px 0;
            }
            QListWidget::item:selected {
                background: #eaf3ff;
                color: #16324f;
            }
        """)
        self.list.itemClicked.connect(self.fill_selected_name)
        list_layout.addWidget(self.list, 1)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch(1)

        self.btn_back = QPushButton("إغلاق")
        self.btn_back.setMinimumHeight(46)
        self.btn_back.setStyleSheet("""
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
        self.btn_back.clicked.connect(self.close)
        bottom_row.addWidget(self.btn_back)

        list_layout.addLayout(bottom_row)

        self.add_soft_shadow(list_box, blur=24, x=0, y=4, alpha=20)
        layout.addWidget(list_box, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll.setWidget(root)

        shell = QVBoxLayout(self)
        shell.setContentsMargins(0,0,0,0)
        shell.addWidget(scroll)

        self.load_doctors()



    def add_soft_shadow(self, widget, blur=28, x=0, y=6, alpha=30):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(__import__("PySide6.QtGui").QtGui.QColor(31, 59, 87, alpha))
        widget.setGraphicsEffect(shadow)

    def fill_selected_name(self, item):
        if item:
            self.name_input.setText(item.text())



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
        try:
            self.conn.close()
        except Exception:
            pass
        self.doctors_changed.emit()
        super().closeEvent(event)

    def load_doctors(self):
        self.list.clear()
        cur = self.conn.cursor()
        cur.execute("SELECT id, name FROM doctors ORDER BY name")
        for doc_id, name in cur.fetchall():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, doc_id)
            self.list.addItem(item)

    def add_doctor(self):
        name = self.name_input.text().strip()
        if not name:
            return
        try:
            self.conn.execute("INSERT INTO doctors(name) VALUES (?)", (name,))
            self.conn.commit()
            self.load_doctors()
            self.name_input.clear()
            self.doctors_changed.emit()
        except Exception:
            QMessageBox.warning(self, "خطأ", "اسم الطبيب موجود مسبقاً.")

    def edit_doctor(self):
        item = self.list.currentItem()
        if not item:
            return
        doc_id = item.data(Qt.UserRole)
        new_name = self.name_input.text().strip()
        if not new_name:
            return
        self.conn.execute("UPDATE doctors SET name=? WHERE id=?", (new_name, doc_id))
        self.conn.commit()
        self.load_doctors()
        self.doctors_changed.emit()

    def delete_doctor(self):
        item = self.list.currentItem()
        if not item:
            return
        doc_id = item.data(Qt.UserRole)
        self.conn.execute("DELETE FROM doctors WHERE id=?", (doc_id,))
        self.conn.commit()
        self.load_doctors()
        self.doctors_changed.emit()