"""Small Qt library editor for Capri emotional avatars (PNG/GIF/video)."""
from __future__ import annotations

from capri_theme import is_modern
from capri_i18n import apply_ui_language, ui_language_from_profile, translate_ui
from pathlib import Path
import os
import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget,
                               QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget)
from capri_avatar_emotions import EMOTIONS, ACTIVITIES, DEFAULT_TRANSITIONS
from capri_ui_dialogs import make_modal, open_files

EMOTION_PL = {
    "neutral":"Neutralna", "happy":"Radosna", "playful":"Figlarna", "caring":"Troskliwa",
    "serious":"Poważna", "annoyed":"Zirytowana", "furious":"Wściekła", "surprised":"Zaskoczona",
    "sleepy":"Senna", "flirty":"Flirtująca", "bashful":"Zawstydzona", "smug":"Zadziorna",
    "curious":"Zaciekawiona", "skeptical":"Sceptyczna", "sad":"Smutna", "worried":"Zaniepokojona",
    "relieved":"Z ulgą", "excited":"Podekscytowana",
}
ACTIVITY_PL = dict(zip(ACTIVITIES, ("Spoczynek", "Myślenie", "Mówienie", "Reakcja")))


class AvatarEditorDialog(QDialog):
    def __init__(self, library, on_change, on_preview, parent=None):
        super().__init__(parent)
        self.library = library
        self.on_change = on_change
        self.on_preview = on_preview
        self.setWindowTitle("CAPRI // EMOCJE I AWATARY")
        self.resize(585, 510)
        make_modal(self)
        root = QVBoxLayout(self)
        if is_modern():
            self.resize(840, 680)
            root.setContentsMargins(28, 24, 28, 24)
            root.setSpacing(16)
            title = QLabel('Emocje i awatary')
            title.setObjectName('ToolTitle')
            root.addWidget(title)
        help_text = QLabel("Pliki awatarów: assets/emocje/<emocja>/, np. happy/zdjecie.gif.\n"
                           "Każda zwykła nazwa GIF/PNG/WEBP/MP4 działa automatycznie.\n"
                           "Podfolder idle/thinking/speaking/reaction jest opcjonalny.\n"
                           "Import kopiuje pliki do folderu wybranej emocji i aktywności.")
        help_text.setWordWrap(True)
        root.addWidget(help_text)
        selectors = QHBoxLayout()
        self.emotion = QComboBox()
        for key in EMOTIONS:
            self.emotion.addItem(EMOTION_PL[key], key)
        self.activity = QComboBox()
        for key in ACTIVITIES:
            self.activity.addItem(ACTIVITY_PL[key], key)
        selectors.addWidget(self.emotion)
        selectors.addWidget(self.activity)
        root.addLayout(selectors)
        folder_row = QHBoxLayout()
        self.folder_label = QLabel()
        self.folder_label.setWordWrap(True)
        self.folder_button = QPushButton("OTWÓRZ FOLDER EMOCJI")
        self.folder_button.clicked.connect(self.open_emotion_folder)
        self.reload_button = QPushButton("ODŚWIEŻ LISTĘ")
        self.reload_button.clicked.connect(self.reload)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(self.folder_button)
        folder_row.addWidget(self.reload_button)
        root.addLayout(folder_row)
        self.emotion.currentIndexChanged.connect(self.reload)
        self.activity.currentIndexChanged.connect(self.reload)
        self.files = QListWidget()
        preview_row = QHBoxLayout()
        preview_row.addWidget(self.files, 3)
        preview_col = QVBoxLayout()
        self.preview_heading = QLabel('PODGLĄD WYBRANEGO AWATARA')
        preview_col.addWidget(self.preview_heading)
        self.preview_image = QLabel('Wybierz plik z listy')
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setMinimumSize(250, 220)
        self.preview_image.setStyleSheet('QLabel { background:#101722; border:1px solid #41526B; border-radius:5px; color:#A6B0BD; }')
        preview_col.addWidget(self.preview_image, 1)
        self.preview_filename = QLabel('')
        self.preview_filename.setWordWrap(True)
        preview_col.addWidget(self.preview_filename)
        preview_row.addLayout(preview_col, 2)
        root.addLayout(preview_row, 1)
        self._preview_movie = None
        buttons = QHBoxLayout()
        self.add_button = QPushButton("+ DODAJ PLIKI")
        self.add_button.clicked.connect(self.add_media)
        self.remove_button = QPushButton("− USUŃ WYBRANY")
        self.remove_button.clicked.connect(self.remove_media)
        for b in (self.add_button, self.remove_button):
            buttons.addWidget(b)
        root.addLayout(buttons)
        weights = QHBoxLayout()
        weights.addWidget(QLabel("Waga wariantu (częstość):"))
        self.weight = QSpinBox()
        self.weight.setRange(1, 100)
        self.weight.setValue(3)
        self.weight.setToolTip("Większa waga = częstsze losowanie danego pliku")
        self.weight.valueChanged.connect(self.change_weight)
        self.files.currentRowChanged.connect(self.load_weight)
        self.files.currentRowChanged.connect(self.update_inline_preview)
        weights.addWidget(self.weight)
        weights.addStretch(1)
        root.addLayout(weights)
        root.addWidget(QLabel("Czas płynnego przejścia (ms):"))
        timing = QHBoxLayout()
        self.timing = {}
        for key, label in (("emotion", "Emocja"), ("variant", "Wariant"),
                           ("reaction", "Reakcja"), ("return", "Powrót")):
            control = QSpinBox()
            control.setRange(80, 2000)
            control.setSingleStep(50)
            control.setValue(self.library.config["transition_ms"].get(key, DEFAULT_TRANSITIONS[key]))
            control.valueChanged.connect(lambda value, name=key: self.set_timing(name, value))
            col = QVBoxLayout()
            col.addWidget(QLabel(label))
            col.addWidget(control)
            timing.addLayout(col)
            self.timing[key] = control
        root.addLayout(timing)
        self.close_button = QPushButton("ZAMKNIJ")
        self.close_button.clicked.connect(self.accept)
        root.addWidget(self.close_button)
        self.ui_lang = getattr(parent, 'lang', None) or ui_language_from_profile()
        apply_ui_language(self, self.ui_lang)
        self.reload()

    def keys(self):
        return self.emotion.currentData(), self.activity.currentData()

    def reload(self):
        emotion, activity = self.keys()
        self.files.blockSignals(True)
        self.files.clear()
        directory = self.library.folder_for(emotion)
        self.folder_label.setText(str(directory) if directory else translate_ui("Foldery aplikacji niedostępne", self.ui_lang))
        for entry in self.library.list_entries(emotion, activity):
            filename = str(entry.get("label") or Path(entry["file"]).name)
            path = self.library.resolve(entry["file"])
            self.files.addItem(f"{filename}  •  {translate_ui('waga', self.ui_lang)} {entry.get('weight', 1)}" + (f"  [{translate_ui('BRAK PLIKU', self.ui_lang)}]" if not path else ""))
        self.files.blockSignals(False)
        if self.files.count():
            self.files.setCurrentRow(0)
        else:
            self.load_weight(-1)
            self.update_inline_preview(-1)

    def add_media(self):
        chosen, _ = open_files(self, "Dodaj animacje i obrazy Capri", "",
                               "Obrazy i filmy (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.mp4 *.webm *.mov)")
        emotion, activity = self.keys()
        errors = []
        for path in chosen:
            try:
                self.library.add(emotion, activity, path, weight=self.weight.value())
            except (OSError, ValueError) as exc:
                errors.append(f"{Path(path).name}: {exc}")
        if chosen:
            self.reload()
            self.on_change()
        if errors:
            QMessageBox.warning(self, translate_ui("Nie udało się dodać pliku", self.ui_lang), "\n".join(errors[:5]))

    def remove_media(self):
        idx = self.files.currentRow()
        if idx < 0:
            return
        emotion, activity = self.keys()
        entries = self.library.list_entries(emotion, activity)
        if idx < len(entries) and self.library.resolve(entries[idx]["file"]):
            decision = QMessageBox.question(self, translate_ui("Usuń plik avatara", self.ui_lang),
                translate_ui("Usunąć plik z dysku? Tej operacji nie można cofnąć.", self.ui_lang))
            if decision != QMessageBox.Yes:
                return
        self.library.remove(emotion, activity, idx)
        self.reload()
        self.on_change()

    def load_weight(self, idx):
        emotion, activity = self.keys()
        entries = self.library.list_entries(emotion, activity)
        self.weight.blockSignals(True)
        if 0 <= idx < len(entries):
            self.weight.setValue(int(entries[idx].get("weight", 3)))
        self.weight.blockSignals(False)

    def change_weight(self, value):
        emotion, activity = self.keys()
        entries = self.library.list_entries(emotion, activity)
        idx = self.files.currentRow()
        if 0 <= idx < len(entries):
            self.library.set_weight(emotion, activity, idx, value)
            self.reload()
            self.files.setCurrentRow(idx)
            self.on_change()

    def set_timing(self, name, value):
        self.library.config["transition_ms"][name] = int(value)
        self.library.save()

    def open_emotion_folder(self):
        emotion, _ = self.keys()
        folder = self.library.folder_for(emotion)
        if folder is None:
            return
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except OSError as exc:
            QMessageBox.warning(self, "Folder emocji", str(exc))

    def update_inline_preview(self, idx):
        # Preview selection in this dialog; never replace the live on-screen
        # avatar and never require the old, broken preview button.
        if self._preview_movie is not None:
            self._preview_movie.stop()
            self._preview_movie.deleteLater()
            self._preview_movie = None
        emotion, activity = self.keys()
        entries = self.library.list_entries(emotion, activity)
        if idx < 0 or idx >= len(entries):
            self.preview_image.setPixmap(QPixmap())
            self.preview_image.setText(translate_ui('Brak wybranego pliku', self.ui_lang))
            self.preview_filename.clear()
            return
        entry = entries[idx]
        resolved = self.library.resolve(entry['file'])
        if not resolved:
            self.preview_image.setPixmap(QPixmap())
            self.preview_image.setText(translate_ui('Nie znaleziono pliku', self.ui_lang))
            return
        path = Path(resolved)
        self.preview_filename.setText(path.name)
        if path.suffix.lower() == '.gif':
            movie = QMovie(str(path), parent=self)
            if movie.isValid():
                self._preview_movie = movie
                movie.frameChanged.connect(self._preview_movie_frame)
                movie.start()
                self._preview_movie_frame(0)
                return
            movie.deleteLater()
        if path.suffix.lower() in ('.mp4', '.webm', '.mov'):
            self.preview_image.setPixmap(QPixmap())
            self.preview_image.setText('Wideo: podgląd GIF/PNG/JPG/WEBP działa tutaj.\nWideo odtwarzane jest w awatarze.')
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            self.preview_image.setPixmap(QPixmap())
            self.preview_image.setText('Nie można odczytać obrazu')
        else:
            self.preview_image.setPixmap(pix.scaled(285, 245,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def _preview_movie_frame(self, _frame):
        movie = self._preview_movie
        if movie is None:
            return
        pix = movie.currentPixmap()
        if not pix.isNull():
            self.preview_image.setPixmap(pix.scaled(285, 245,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def closeEvent(self, event):
        if self._preview_movie is not None:
            self._preview_movie.stop()
            self._preview_movie = None
        super().closeEvent(event)
