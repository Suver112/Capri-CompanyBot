"""Native Windows File Explorer dialogs for selecting audio, folders and images.

Message boxes remain separately topmost; file pickers use OS-native dialogs.
"""
from __future__ import annotations

from pathlib import Path
from capri_i18n import translate_ui, ui_language_from_profile
import os
import sys
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox


DIALOG_FLAGS = (Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint |
                Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowStaysOnTopHint)


def make_modal(dialog):
    dialog.setWindowFlags(DIALOG_FLAGS)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    # A queued focus request comes after the window enters the native hierarchy.
    QTimer.singleShot(0, lambda: (dialog.raise_(), dialog.activateWindow()))
    return dialog


def _native_options():
    # On Windows the native IFileDialog/File Explorer picker is preferable.
    # Keep standard native OS file picker behavior and parent ownership.
    return QFileDialog.Option(0)


def open_file(parent, caption, directory='', filter=''):
    return QFileDialog.getOpenFileName(parent, caption, directory, filter, options=_native_options())


def open_files(parent, caption, directory='', filter=''):
    return QFileDialog.getOpenFileNames(parent, caption, directory, filter, options=_native_options())


def open_folder_dialog(parent, caption, directory=''):
    return QFileDialog.getExistingDirectory(parent, caption, directory, options=_native_options())


def notify(parent, title, message, icon=QMessageBox.Icon.Information):
    dlg = make_modal(QMessageBox(parent))
    dlg.setIcon(icon)
    dlg.setWindowTitle(translate_ui(title, ui_language_from_profile()))
    dlg.setText(translate_ui(str(message), ui_language_from_profile()))
    dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
    return dlg.exec()


def confirm(parent, title, message):
    dlg = make_modal(QMessageBox(parent))
    dlg.setIcon(QMessageBox.Icon.Question)
    dlg.setWindowTitle(translate_ui(title, ui_language_from_profile()))
    dlg.setText(translate_ui(str(message), ui_language_from_profile()))
    dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    dlg.setDefaultButton(QMessageBox.StandardButton.No)
    return dlg.exec()


def reveal_folder(path: str | Path) -> bool:
    """Open a managed audio folder, not the user's home or an arbitrary shell command."""
    directory = Path(path).expanduser().resolve()
    if directory.is_file():
        directory = directory.parent
    directory.mkdir(parents=True, exist_ok=True)
    return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))))
