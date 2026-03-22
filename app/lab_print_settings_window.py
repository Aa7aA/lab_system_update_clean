from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QColor
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QMessageBox,
    QFrame,
    QToolButton,
    QGroupBox,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
)

from .ui_utils import apply_global_theme, apply_round_corners

from .db import get_conn, get_lab_setting, set_lab_setting
from .branding import LAB_BRANDING

class LabPrintSettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("إعدادات الطباعة")
        self.resize(860, 620)
        apply_round_corners(self, 12)


        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)




        root = QFrame(self)
        root.setObjectName("AppShell")

        shell_layout = QVBoxLayout(root)
        shell_layout.setContentsMargins(10, 10, 10, 10)
        shell_layout.setSpacing(10)

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

        brand_title = QLabel("إعدادات الطباعة")
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
        shell_layout.addWidget(header)

        # ---------------- Settings card ----------------
        form_box = QGroupBox("بيانات التذييل والطباعة")
        form_box.setLayoutDirection(Qt.RightToLeft)

        form_layout = QVBoxLayout(form_box)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_layout.setSpacing(12)

        lbl_footer = QLabel("نص التذييل:")
        lbl_footer.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        form_layout.addWidget(lbl_footer)

        self.footer_text = QTextEdit()
        self.footer_text.setPlaceholderText("النص الذي يظهر أسفل التقرير المطبوع")
        self.footer_text.setMinimumHeight(180)
        form_layout.addWidget(self.footer_text)

        lbl_whatsapp = QLabel("رقم الواتساب:")
        lbl_whatsapp.setStyleSheet("font-size: 14px; font-weight: 700; background: transparent;")
        form_layout.addWidget(lbl_whatsapp)

        self.whatsapp_number = QLineEdit()
        self.whatsapp_number.setPlaceholderText("مثال: 07725017776")
        self.whatsapp_number.setMinimumHeight(46)
        form_layout.addWidget(self.whatsapp_number)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_save = QPushButton("حفظ")
        self.btn_back = QPushButton("إغلاق")

        self.btn_save.setMinimumHeight(46)
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

        self.btn_save.clicked.connect(self.on_save)
        self.btn_back.clicked.connect(self.close)

        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_back)
        form_layout.addLayout(btn_row)

        self.add_soft_shadow(form_box, blur=24, x=0, y=4, alpha=20)
        shell_layout.addWidget(form_box, 1)

        scroll.setWidget(root)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

        self.load_settings()


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







    def load_settings(self):
        with get_conn() as conn:
            footer = get_lab_setting(conn, "footer_text", "")
            whatsapp = get_lab_setting(conn, "whatsapp_number", "")

        self.footer_text.setPlainText(footer)
        self.whatsapp_number.setText(whatsapp)

    def on_save(self):
        footer = self.footer_text.toPlainText().strip()
        whatsapp = self.whatsapp_number.text().strip()

        with get_conn() as conn:
            set_lab_setting(conn, "footer_text", footer)
            set_lab_setting(conn, "whatsapp_number", whatsapp)

        QMessageBox.information(self, "تم الحفظ", "تم حفظ إعدادات الطباعة بنجاح.")