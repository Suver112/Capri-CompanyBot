"""Windowed OAuth setup for the packaged Capri.exe (no console/input())."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox, QProgressDialog


class ConnectThread(QThread):
    done = Signal(bool, str)

    def __init__(self, client_id: str):
        super().__init__()
        self.client_id = client_id

    def run(self):
        try:
            from capri_spotify_web import connect
            connect(self.client_id)
            self.done.emit(True, 'Spotify połączono z Capri.')
        except Exception as exc:
            self.done.emit(False, str(exc))


def run() -> int:
    from capri_spotify_web import CALLBACK
    app = QApplication.instance() or QApplication([])
    text = ('1. Otwórz https://developer.spotify.com/dashboard\n'
            '2. Skonfiguruj redirect URI:\n   ' + CALLBACK + '\n'
            '3. Wklej Client ID (bez hasła ani sekretu).')
    QMessageBox.information(None, 'Capri // Spotify', text)
    value, ok = QInputDialog.getText(None, 'Capri // Spotify', 'Spotify Client ID:')
    if not ok or not value.strip():
        return 0
    progress = QProgressDialog('Oczekiwanie na logowanie w przeglądarce…', '', 0, 0)
    progress.setWindowTitle('Capri // Spotify')
    progress.setCancelButton(None)
    progress.setMinimumDuration(0)
    progress.setWindowModality(__import__('PySide6.QtCore', fromlist=['Qt']).Qt.WindowModality.ApplicationModal)
    worker = ConnectThread(value.strip())
    result = {}
    def finished(ok, message):
        result['ok'], result['message'] = ok, message
        progress.close()
    worker.done.connect(finished)
    worker.start()
    progress.exec()
    worker.wait(1000)
    if result.get('ok'):
        QMessageBox.information(None, 'Capri // Spotify', result['message'])
        return 0
    QMessageBox.warning(None, 'Capri // Spotify', result.get('message', 'Przerwano autoryzację.'))
    return 1
