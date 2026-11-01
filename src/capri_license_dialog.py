"""Capri-themed, foreground-safe, optional vendor license dialog.

No blanket first-run EULA: a consent dialog is shown only before use of
local Fish S2-Pro weights without a recorded acceptance. It runs as a top-level
application-modal Capri window, above the always-on-top overlay.
"""
from __future__ import annotations

import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QComboBox, QCheckBox,
)

from capri_paths import local_root
from capri_licenses import (
    FISH_RESEARCH_URL, FISH_RESEARCH_PAGE, FISH_COMMUNITY_RAW,
    FISH_COMMUNITY_URL, fetch_vendor_license, record_fish_research_acceptance,
)
from capri_theme import selected_theme

ROOT = Path(__file__).resolve().parent
LEGAL_DOCUMENT = (ROOT / 'LEGAL' / 'INFORMACJE_PRAWNE.md')
if not LEGAL_DOCUMENT.is_file():
    LEGAL_DOCUMENT = ROOT.parent / 'LEGAL' / 'INFORMACJE_PRAWNE.md'
# An HTTP read may finish after the dialog was dismissed. Keep the QThread alive
# independently of the dialog so Qt never destroys a running thread.
_ACTIVE_FETCHES = set()


class _LicenseFetchThread(QThread):
    finished_read = Signal(str, bool)

    def __init__(self, url, cache):
        super().__init__()  # Not parented to a dialog which may close during HTTP.
        self.url = url
        self.cache = cache

    def run(self):
        try:
            self.finished_read.emit(fetch_vendor_license(self.url, self.cache), True)
        except Exception:
            self.finished_read.emit('', False)


class _CapriLicenseHeader(QFrame):
    """Drag handle for a branded frameless Capri window."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('LicenseHeader')
        self._drag_origin = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.window().pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_origin is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.window().move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_origin = None
        super().mouseReleaseEvent(event)


_PALETTES = {
    'holocall': ('#06181b', '#0c262a', '#ef7784', '#bde6e2', '#76b7bd', '#3b6f73'),
    'silverhand': ('#080f1e', '#0e2035', '#d5e65f', '#e0ee9a', '#a8b879', '#446392'),
    'capri': ('#191a1d', '#25252d', '#ff175d', '#e8e6ea', '#aaa8b3', '#54545f'),
}


def _license_stylesheet(theme: str) -> str:
    bg, surface, accent, text, muted, border = _PALETTES.get(theme, _PALETTES['holocall'])
    return f'''
    QDialog#CapriLicenseDialog {{ background:{bg}; color:{text}; border:2px solid {border}; }}
    QFrame#LicenseHeader {{ background:{surface}; border:0; border-bottom:2px solid {accent}; }}
    QLabel#LicenseBrand {{ color:{accent}; font:700 17px 'Bahnschrift','Segoe UI'; }}
    QLabel#LicenseTitle {{ color:{text}; font:700 23px 'Bahnschrift','Segoe UI'; }}
    QLabel#LicenseNote, QLabel#LicenseHint {{ color:{muted}; font:12px 'Segoe UI'; }}
    QLabel#LicenseNotice {{ color:{accent}; font:600 12px 'Segoe UI'; }}
    QPlainTextEdit#LicenseDocument {{ background:{surface}; color:{text}; border:1px solid {border};
         padding:12px; font:12px 'Segoe UI'; selection-background-color:{border}; }}
    QComboBox#LicenseSource {{ background:{surface}; color:{text}; border:1px solid {border};
         min-height:34px; padding:4px 10px; }}
    QComboBox QAbstractItemView {{ background:{surface}; color:{text}; selection-background-color:{border}; }}
    QCheckBox#LicenseConsent {{ color:{text}; spacing:8px; font:13px 'Segoe UI'; }}
    QCheckBox#LicenseConsent::indicator {{ width:17px; height:17px; border:1px solid {border};
         background:{surface}; }}
    QCheckBox#LicenseConsent::indicator:checked {{ background:{accent}; border:1px solid {accent}; }}
    QPushButton {{ border:1px solid {border}; background:{surface}; color:{text};
         min-height:32px; padding:4px 16px; font:12px 'Segoe UI'; }}
    QPushButton:hover {{ border-color:{accent}; }}
    QPushButton#LicenseAccept {{ background:{accent}; color:{bg}; border-color:{accent}; font-weight:700; }}
    QPushButton#LicenseAccept:disabled {{ background:{surface}; color:{muted}; border-color:{border}; }}
    QPushButton#LicenseClose {{ background:transparent; color:{muted}; border:0;
         font:20px 'Segoe UI'; min-width:30px; padding:0; }}
    QScrollBar:vertical {{ width:8px; background:transparent; margin:0 4px 0 6px; }}
    QScrollBar::handle:vertical {{ background:{accent}; border-radius:3px; min-height:24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
    '''


class _LicenseDialog(QDialog):
    def __init__(self, language='pl', parent=None, *, require_consent=False):
        super().__init__(parent)
        self.lang = language
        self.require_consent = require_consent
        self._worker = None
        self._first_show = True
        self.setObjectName('CapriLicenseDialog')
        # Capri's overlay is Qt.Tool + WindowStaysOnTopHint. A default QDialog
        # can land UNDER that overlay. Set the same topmost level explicitly.
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle('Capri — Fish S2-Pro License' if require_consent else
                            'Capri — Licenses')
        self.setMinimumSize(540, 400)
        self.resize(800, 620)
        self.setStyleSheet(_license_stylesheet(selected_theme()))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        top = _CapriLicenseHeader(self)
        bar = QHBoxLayout(top)
        bar.setContentsMargins(24, 12, 18, 12)
        self.brand = QLabel('CAPRI  //  FISH S2-PRO' if require_consent else 'CAPRI  //  LEGAL')
        self.brand.setObjectName('LicenseBrand')
        bar.addWidget(self.brand)
        bar.addStretch()
        close = QPushButton('×')
        close.setAccessibleName('Pomiń' if require_consent and language == 'pl' else
                                'Skip' if require_consent else
                                'Zamknij' if language == 'pl' else 'Close')
        close.setObjectName('LicenseClose')
        close.clicked.connect(self.reject if require_consent else self.accept)
        bar.addWidget(close)
        outer.addWidget(top)

        content = QWidget(self)
        box = QVBoxLayout(content)
        box.setContentsMargins(28, 22, 28, 24)
        box.setSpacing(13)
        title = QLabel(('Licencja lokalnego modelu głosu' if language == 'pl' else
                        'Local voice model license') if require_consent else
                       ('Licencje i informacje prawne' if language == 'pl' else
                        'Licenses and legal information'))
        title.setObjectName('LicenseTitle')
        box.addWidget(title)
        hint = QLabel(('Przed uruchomieniem lokalnego Fish S2-Pro zapoznaj się z warunkami wag modelu.'
                       if language == 'pl' else
                       'Please review the model-weights license before using local Fish S2-Pro.')
                      if require_consent else
                      ('Dokumenty komponentów zewnętrznych używanych przez Capri.' if language == 'pl'
                       else 'Third-party component licenses used by Capri.'))
        hint.setObjectName('LicenseHint')
        hint.setWordWrap(True)
        box.addWidget(hint)
        self.source = QComboBox(self)
        self.source.setObjectName('LicenseSource')
        self.source.addItem('Fish S2-Pro  •  Research License', 'research')
        if not require_consent:
            self.source.addItem('Fish Speech  •  Community License', 'community')
            self.source.addItem('Capri  •  ' + ('prawa i zasady' if language == 'pl' else 'rights and notices'), 'capri')
        box.addWidget(self.source)
        self.note = QLabel()
        self.note.setObjectName('LicenseNotice')
        self.note.setWordWrap(True)
        box.addWidget(self.note)
        self.body = QPlainTextEdit(self)
        self.body.setObjectName('LicenseDocument')
        self.body.setReadOnly(True)
        self.body.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        box.addWidget(self.body, 1)

        if require_consent:
            self.check = QCheckBox(('Przeczytałem(-am) licencję wag Fish S2-Pro i akceptuję jej warunki.'
                                    if language == 'pl' else
                                    'I have read and accept the Fish S2-Pro model weights license.'))
            self.check.setObjectName('LicenseConsent')
            self.check.setEnabled(False)
            box.addWidget(self.check)
        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.link = QPushButton('Otwórz pełną licencję w przeglądarce' if language == 'pl' else
                                'Open license in browser')
        self.link.clicked.connect(self.open_source)
        footer.addWidget(self.link)
        footer.addStretch(1)
        if require_consent:
            self.skip_button = QPushButton('Pomiń Fish' if language == 'pl' else 'Skip Fish')
            self.skip_button.clicked.connect(self.reject)
            footer.addWidget(self.skip_button)
            self.accept_button = QPushButton('Akceptuję' if language == 'pl' else 'Accept')
            self.accept_button.setObjectName('LicenseAccept')
            self.accept_button.setEnabled(False)
            self.check.toggled.connect(self._update_accept_enabled)
            self.accept_button.clicked.connect(self._accepted)
            footer.addWidget(self.accept_button)
        else:
            dismiss = QPushButton('Zamknij' if language == 'pl' else 'Close')
            dismiss.clicked.connect(self.accept)
            footer.addWidget(dismiss)
            self.source.currentIndexChanged.connect(self.refresh)
        box.addLayout(footer)
        outer.addWidget(content, 1)
        self.refresh()

    def _update_accept_enabled(self):
        if self.require_consent:
            self.accept_button.setEnabled(self.check.isEnabled() and self.check.isChecked())

    def current_url(self):
        code = self.source.currentData()
        return FISH_RESEARCH_PAGE if code == 'research' else FISH_COMMUNITY_URL if code == 'community' else ''

    def open_source(self):
        url = self.current_url()
        if url:
            webbrowser.open(url)
        else:
            webbrowser.open(LEGAL_DOCUMENT.as_uri())

    def refresh(self):
        code = self.source.currentData()
        if code == 'capri':
            self.body.setPlainText(LEGAL_DOCUMENT.read_text(encoding='utf-8'))
            self.note.setText('Nieoficjalny projekt fanowski. Grafiki: ChatGPT. Głos: syntetyczny.' if self.lang == 'pl'
                              else 'Unofficial fan project. Artwork: ChatGPT. Voice: synthetic.')
            return
        if self.require_consent:
            self.check.setChecked(False)
            self.check.setEnabled(False)
            self.accept_button.setEnabled(False)
        self.body.setPlainText('Ładowanie pełnej licencji…' if self.lang == 'pl' else
                               'Loading the full license…')
        self.note.setText(('Fish S2-Pro: użycie badawcze i niekomercyjne. Zastosowania komercyjne wymagają odrębnej zgody.'
                           if self.lang == 'pl' else
                           'Fish S2-Pro research and non-commercial use; commercial use needs separate permission.')
                          if code == 'research' else
                          ('Kod Fish Speech i wagi S2-Pro mają różne licencje.' if self.lang == 'pl' else
                           'Fish Speech code and S2-Pro weights have different licenses.'))
        cache = local_root() / 'licenses' / ('fish-s2-pro-research.md' if code == 'research' else 'fish-speech-community.txt')
        url = FISH_RESEARCH_URL if code == 'research' else FISH_COMMUNITY_RAW
        worker = _LicenseFetchThread(url, cache)
        self._worker = worker
        _ACTIVE_FETCHES.add(worker)
        worker.finished_read.connect(self._loaded)
        worker.finished.connect(lambda w=worker: _ACTIVE_FETCHES.discard(w))
        worker.start()

    def _loaded(self, content, success):
        if success:
            self.body.setPlainText(content)
            if self.require_consent:
                self.check.setEnabled(True)
        else:
            self.body.setPlainText(('Nie można pobrać licencji. Otwórz dokument w przeglądarce '
                                    'lub spróbuj ponownie przy połączeniu z internetem. '
                                    'Pozostałe funkcje Capri działają nadal.' if self.lang == 'pl' else
                                    'The license could not be loaded. Open the document in your browser '
                                    'or try again online. Other Capri features are still available.'))
        self._worker = None

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            screen = (QApplication.screenAt(self.parentWidget().frameGeometry().center())
                      if self.parentWidget() else None) or QApplication.primaryScreen()
            if screen is not None:
                area = screen.availableGeometry()
                width = min(self.width(), max(420, area.width() - 28))
                height = min(self.height(), max(340, area.height() - 28))
                self.resize(width, height)
                self.move(area.x() + (area.width() - width)//2,
                          area.y() + (area.height() - height)//2)
        QTimer.singleShot(0, self._bring_to_front)

    def _bring_to_front(self):
        if self.isVisible():
            self.raise_()
            self.activateWindow()
            self.body.setFocus(Qt.FocusReason.OtherFocusReason)

    def _accepted(self):
        if not self.require_consent or not self.check.isEnabled() or not self.check.isChecked():
            return
        try:
            record_fish_research_acceptance()
        except OSError:
            self.note.setText('Nie udało się zapisać zgody.' if self.lang == 'pl' else
                              'Could not save acceptance.')
            return
        self.accept()


def show_license_catalog(language='pl', parent=None):
    return _LicenseDialog(language, parent).exec()


def confirm_local_fish_license(language='pl', parent=None):
    return _LicenseDialog(language, parent, require_consent=True).exec() == QDialog.DialogCode.Accepted
