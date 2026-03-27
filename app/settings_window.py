from __future__ import annotations

from pathlib import Path






from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QGroupBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QApplication,
    QScrollArea,
    QMessageBox
)

from .ui_utils import apply_global_theme, fit_window_to_screen, apply_round_corners, show_blocking_child
from .branding import LAB_BRANDING
from .version import APP_VERSION, APP_CHANNEL
from .lab_identity import get_lab_identity
from .support_snapshot import export_support_snapshot


class SettingsWindow(QWidget):
    def __init__(self, parent_main_window=None):
        super().__init__()
        self.parent_main_window = parent_main_window
        identity = get_lab_identity()

        self._drag_pos: QPoint | None = None
        self.is_dark_mode = False

        self.setWindowTitle("الإعدادات")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        fit_window_to_screen(
            self,
            width_ratio=0.72,
            height_ratio=0.72,
            min_width=760,
            min_height=560,
        )
        apply_round_corners(self, 24)


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

        brand_title = QLabel("إعدادات النظام")
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

        # ---------- Settings actions ----------
        actions_box = QGroupBox("أدوات الإدارة")
        actions_box.setLayoutDirection(Qt.RightToLeft)
        actions_layout = QVBoxLayout(actions_box)
        actions_layout.setContentsMargins(16, 16, 16, 16)
        actions_layout.setSpacing(12)

        self.btn_doctors = self.make_tool_button("إدارة الأطباء")
        self.btn_ranges = self.make_tool_button("تعديل القيم الطبيعية")
        self.btn_tests = self.make_tool_button("إضافة / تعديل التحاليل")
        self.btn_modules = self.make_tool_button("إضافة / تعديل الأقسام")
        self.btn_print = self.make_tool_button("إعدادات الطباعة")
        self.btn_support_snapshot = self.make_tool_button("Export Support Report")



        self.btn_doctors.clicked.connect(self.open_doctor_manager)
        self.btn_ranges.clicked.connect(self.open_normal_range_editor)
        self.btn_tests.clicked.connect(self.open_test_admin_editor)
        self.btn_modules.clicked.connect(self.open_module_admin_editor)
        self.btn_print.clicked.connect(self.open_lab_print_settings)
        self.btn_support_snapshot.clicked.connect(self.export_support_report)


        actions_layout.addWidget(self.btn_doctors)
        actions_layout.addWidget(self.btn_ranges)
        actions_layout.addWidget(self.btn_tests)
        actions_layout.addWidget(self.btn_modules)
        actions_layout.addWidget(self.btn_print)
        actions_layout.addWidget(self.btn_support_snapshot)
 

        self.lbl_version_info = QLabel(
            f"Version: {APP_VERSION}   |   Channel: {APP_CHANNEL}   |   Lab ID: {identity['lab_id']}"
        )
        self.lbl_version_info.setAlignment(Qt.AlignCenter)
        self.lbl_version_info.setStyleSheet("""
            QLabel {
                color: #4f6f8f;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                padding-top: 8px;
            }
        """)
        actions_layout.addWidget(self.lbl_version_info)





        self.add_soft_shadow(actions_box, blur=24, x=0, y=4, alpha=20)
        root.addWidget(actions_box, 1)

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

        self._opened_windows = []

    def make_tool_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(46)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #28415f;
                border: 1px solid #e4ebf5;
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

    def open_doctor_manager(self):
        from .doctor_manager_window import DoctorManagerWindow

        w = DoctorManagerWindow()

        if self.parent_main_window is not None:
            w.doctors_changed.connect(self.parent_main_window.load_doctors)

        self._opened_windows.append(w)
        w.destroyed.connect(
            lambda: self._opened_windows.remove(w) if w in self._opened_windows else None
        )
        show_blocking_child(self, w)

    def open_normal_range_editor(self):
        from .normal_range_editor import NormalRangeModuleSelectorWindow
        callback = None
        if self.parent_main_window is not None:
            callback = self.parent_main_window.refresh_all_structure_views

        w = NormalRangeModuleSelectorWindow(on_ranges_changed=callback)
        self._opened_windows.append(w)
        w.destroyed.connect(lambda: self._opened_windows.remove(w) if w in self._opened_windows else None)
        show_blocking_child(self, w)

    def open_test_admin_editor(self):
        from .test_admin_editor import TestAdminModuleSelectorWindow
        callback = None
        if self.parent_main_window is not None:
            callback = self.parent_main_window.refresh_all_structure_views

        w = TestAdminModuleSelectorWindow(on_tests_changed=callback)
        self._opened_windows.append(w)
        w.destroyed.connect(lambda: self._opened_windows.remove(w) if w in self._opened_windows else None)
        show_blocking_child(self, w)

    def open_module_admin_editor(self):
        from .module_admin_editor import ModuleAdminEditorWindow
        callback = None
        if self.parent_main_window is not None:
            callback = self.parent_main_window.refresh_all_structure_views

        w = ModuleAdminEditorWindow(on_modules_changed=callback)
        self._opened_windows.append(w)
        w.destroyed.connect(lambda: self._opened_windows.remove(w) if w in self._opened_windows else None)
        show_blocking_child(self, w)

    def open_lab_print_settings(self):
        from .lab_print_settings_window import LabPrintSettingsWindow
        w = LabPrintSettingsWindow()
        self._opened_windows.append(w)
        w.destroyed.connect(lambda: self._opened_windows.remove(w) if w in self._opened_windows else None)
        show_blocking_child(self, w)

    def export_support_report(self):
        try:
            out_path = export_support_snapshot()
            QMessageBox.information(
                self,
                "Support Report",
                f"Support report exported successfully:\n{out_path}"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Support Report Error",
                f"Failed to export support report:\n{e}"
            )


