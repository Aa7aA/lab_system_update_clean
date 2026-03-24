from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4


from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QTextEdit,
    QFrame,
)

from .version import APP_VERSION
from .updater import (
    UpdateInfo,
    get_download_target,
    download_file,
    verify_download,
)
from .ui_utils import apply_round_corners


class DownloadWorker(QObject):
    progress_percent = Signal(int)
    status_text = Signal(str)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, info: UpdateInfo):
        super().__init__()
        self.info = info

    def run(self):
        try:
            self.status_text.emit("Preparing download...")
            target = get_download_target(self.info)

            def on_progress(downloaded: int, total: int):
                if total > 0:
                    percent = int(downloaded * 100 / total)
                    self.progress_percent.emit(percent)
                    self.status_text.emit(
                        f"Downloading update... {percent}% "
                        f"({downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB)"
                    )
                else:
                    self.status_text.emit(
                        f"Downloading update... {downloaded // 1024 // 1024} MB"
                    )

            download_file(self.info.download_url, target, progress_cb=on_progress)

            self.status_text.emit("Verifying download...")
            if not verify_download(target, self.info.sha256):
                raise RuntimeError("Downloaded file hash does not match manifest sha256.")

            self.progress_percent.emit(100)
            self.status_text.emit("Download completed successfully.")
            self.finished.emit(str(target))

        except Exception as e:
            self.failed.emit(str(e))


class UpdateWindow(QWidget):
    def __init__(self, info: UpdateInfo, parent_main_window=None):
        super().__init__(parent_main_window)
        self.info = info
        self.parent_main_window = parent_main_window

        self.worker_thread: QThread | None = None
        self.worker: DownloadWorker | None = None
        self.downloaded_installer_path: str | None = None
        self.is_busy = False

        self.setWindowTitle("Update")
        self.resize(620, 430)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        apply_round_corners(self, 15)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Update Available")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #12385c;")
        root.addWidget(title)

        version_label = QLabel(
            f"Current version: {APP_VERSION}\n"
            f"New version: {self.info.latest_version}"
        )
        version_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        root.addWidget(version_label)

        notes_label = QLabel("Release Notes")
        notes_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #12385c;")
        root.addWidget(notes_label)

        self.notes_box = QTextEdit()
        self.notes_box.setReadOnly(True)
        self.notes_box.setMinimumHeight(150)
        notes_text = "\n".join(f"- {note}" for note in self.info.notes) if self.info.notes else "No release notes."
        self.notes_box.setPlainText(notes_text)
        root.addWidget(self.notes_box)

        self.status_label = QLabel("Ready to download.")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        root.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setMinimumHeight(28)
        root.addWidget(self.progress)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        root.addWidget(line)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_close = QPushButton("Close")
        self.btn_download = QPushButton("Download and Install")
        self.btn_install_now = QPushButton("Install Now")

        self.btn_close.setMinimumHeight(38)
        self.btn_download.setMinimumHeight(38)
        self.btn_install_now.setMinimumHeight(38)

        self.btn_install_now.setEnabled(False)

        self.btn_close.clicked.connect(self.close)
        self.btn_download.clicked.connect(self.start_download)
        self.btn_install_now.clicked.connect(self.start_install)

        btn_row.addWidget(self.btn_download)
        btn_row.addWidget(self.btn_install_now)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_close)

        root.addLayout(btn_row)

    def closeEvent(self, event):
        if self.is_busy:
            QMessageBox.information(
                self,
                "Update in progress",
                "Please wait until the update download finishes."
            )
            event.ignore()
            return
        super().closeEvent(event)

    def start_download(self):
        if self.is_busy:
            return

        self.is_busy = True
        self.btn_download.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.btn_install_now.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Starting download...")

        self.worker_thread = QThread()
        self.worker = DownloadWorker(self.info)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_percent.connect(self.progress.setValue)
        self.worker.status_text.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.failed.connect(self.on_download_failed)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def on_download_finished(self, installer_path: str):
        self.is_busy = False
        self.downloaded_installer_path = installer_path
        self.btn_close.setEnabled(True)
        self.btn_install_now.setEnabled(True)
        self.status_label.setText("Download complete. Ready to install.")

        auto_reply = QMessageBox.question(
            self,
            "Install Update",
            "The update has been downloaded successfully.\n\n"
            "Do you want to close the app and install it now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if auto_reply == QMessageBox.Yes:
            self.start_install()

    def on_download_failed(self, message: str):
        self.is_busy = False
        self.btn_close.setEnabled(True)
        self.btn_download.setEnabled(True)
        self.btn_install_now.setEnabled(False)

        QMessageBox.warning(
            self,
            "Update Error",
            f"Failed to download update:\n{message}"
        )
        self.status_label.setText("Download failed.")

    def start_install(self):
        if not self.downloaded_installer_path:
            QMessageBox.warning(self, "Update", "No downloaded installer was found.")
            return

        installer_path = Path(self.downloaded_installer_path)
        if not installer_path.exists():
            QMessageBox.warning(self, "Update", "Downloaded installer file does not exist.")
            return

        app_exe = Path(sys.executable).resolve()

        # real helper next to installed app
        installed_helper_exe = app_exe.parent / "update_helper.exe"

        if not installed_helper_exe.exists():
            QMessageBox.warning(
                self,
                "Update Error",
                f"Could not find update helper:\n{installed_helper_exe}\n\n"
                f"You need to package update_helper.exe with the app."
            )
            return

        current_pid = os.getpid()

        # Run a TEMP copy of the helper so installer can replace the real helper in Program Files
        temp_dir = Path(tempfile.gettempdir()) / "AlShafaqLabUpdater"
        temp_dir.mkdir(parents=True, exist_ok=True)

        temp_helper_exe = temp_dir / f"update_helper_{uuid4().hex}.exe"

        try:
            shutil.copy2(installed_helper_exe, temp_helper_exe)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Update Error",
                f"Failed to prepare temporary update helper:\n{e}"
            )
            return

        try:
            subprocess.Popen([
                str(temp_helper_exe),
                str(installer_path),
                str(current_pid),
            ])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Update Error",
                f"Failed to start update helper:\n{e}"
            )
            return

        from PySide6.QtWidgets import QApplication
        QApplication.closeAllWindows()
        QApplication.quit()

        os._exit(0)