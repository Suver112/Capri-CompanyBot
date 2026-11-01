"""CAPRI Voice Manager: optional, separate program. No imports from main.py.

Import WAV/MP3 with editable exact transcript or generate a new WAV through
local Fish Vulkan. The assistant's LLM is never prompted with these phrases.
"""
from __future__ import annotations
from capri_theme import apply_style, install_theme, saved_theme, is_modern, MAIN, THEMES

from capri_paths import data_root
from capri_i18n import apply_ui_language, ui_language_from_profile, translate_ui

import json
import os
from pathlib import Path
import sys
import threading

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QPlainTextEdit, QFrame, QSplitter, QScrollArea)

from capri_ui_dialogs import (open_file as topmost_open_file, reveal_folder,
                              notify as topmost_notify, confirm as topmost_confirm)
from capri_voice_matcher import semantic_voice_rule_match
from capri_voice_library import (ROOT, add_audio, entry_audio, list_entries,
                                 remove_entry, update_entry, validate_rules, find_for_question)
from fish_bridge import fish_reference_path
from s2cpp_bridge import synthesize_s2cpp, DEFAULT_S2_PORT

CONFIG_PATH = data_root() / 'settings.json'


def load_settings() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return {}


class AsyncSignals(QObject):
    progress = Signal(str)
    ready = Signal(str)
    failure = Signal(str)


class MatchSignals(QObject):
    ready = Signal(object)


class VoiceManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CAPRI // MENEDŻER GŁOSU • v16.1')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1050, 770)
        self.setMinimumSize(800, 580)
        self.selected_id = None
        self.working = False
        self.async_signals = AsyncSignals(self)
        self.async_signals.progress.connect(self.set_status)
        self.async_signals.ready.connect(self._generate_done)
        self.async_signals.failure.connect(self._generate_failed)
        self.match_signals = MatchSignals(self)
        self.match_signals.ready.connect(self._preview_semantic_result)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.65)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.errorOccurred.connect(self._audio_error)

        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 16)
        layout.setSpacing(10)
        title = QLabel('◈  CAPRI // BANK GŁOSU')
        title.setObjectName('Title')
        layout.addWidget(title)
        guide = QLabel('Zaznacz nagranie z lewej, a po prawej edytuj tekst i reguły. '
                       'Zmiany zapisują się dopiero po kliknięciu ZAPISZ. '
                       'Nagrania pozostają dostępne między uruchomieniami.')
        guide.setWordWrap(True)
        layout.addWidget(guide)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        layout.addWidget(split, 1)

        library = QFrame()
        library.setObjectName('Panel')
        library_layout = QVBoxLayout(library)
        library_layout.setContentsMargins(12, 12, 12, 12)
        library_layout.setSpacing(8)
        library_layout.addWidget(QLabel('01 / BIBLIOTEKA NAGRAŃ'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('⌕  Szukaj po tekście, pytaniu lub nazwie…')
        self.search.textChanged.connect(self._filter_entries)
        library_layout.addWidget(self.search)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['ODPOWIEDŹ', 'PYTANIA', 'JĘZYK', 'ŹRÓDŁO', 'ON'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i, width in [(1, 135), (2, 52), (3, 82), (4, 42)]:
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(i, width)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        library_layout.addWidget(self.table, 1)

        library_actions = QHBoxLayout()
        self.new_btn = QPushButton('＋  NOWY')
        self.import_btn = QPushButton('⇣  IMPORT WAV / MP3')
        library_actions.addWidget(self.new_btn)
        library_actions.addWidget(self.import_btn, 1)
        library_layout.addLayout(library_actions)
        folder_actions = QHBoxLayout()
        self.folder_btn = QPushButton('▣  FOLDER NAGRAŃ')
        self.folder_btn.setToolTip('Otwórz w Eksploratorze katalog importowanych nagrań Capri')
        self.folder_btn.clicked.connect(self.open_folder)
        self.file_btn = QPushButton('▣  POKAŻ WYBRANY PLIK')
        self.file_btn.clicked.connect(self.open_selected_folder)
        folder_actions.addWidget(self.folder_btn)
        folder_actions.addWidget(self.file_btn)
        library_layout.addLayout(folder_actions)
        split.addWidget(library)

        editor_scroller = QScrollArea()
        editor_scroller.setObjectName('EditorScroll')
        editor_scroller.setWidgetResizable(True)
        editor_scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor = QFrame()
        editor.setObjectName('Panel')
        edit = QVBoxLayout(editor)
        edit.setContentsMargins(14, 12, 14, 12)
        edit.setSpacing(9)
        edit.addWidget(QLabel('02 / TEKST I REGUŁY'))
        edit.addWidget(QLabel('TEKST W NAGRANIU — wyświetlany na czacie:'))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText('Np. Cześć! Czego dzisiaj ode mnie chcesz?')
        self.text_edit.setFixedHeight(65)
        edit.addWidget(self.text_edit)
        edit.addWidget(QLabel('PYTANIA / FRAZY — jedno na linię:'))
        self.triggers_edit = QPlainTextEdit()
        self.triggers_edit.setPlaceholderText('jak masz na imię?\nkim jesteś?\njak się nazywasz?')
        self.triggers_edit.setFixedHeight(74)
        edit.addWidget(self.triggers_edit)
        edit.addWidget(QLabel('INSTRUKCJA DLA BIELIKA (intencja nagrania):'))
        self.intent_edit = QPlainTextEdit()
        self.intent_edit.setPlaceholderText('Użyj tego nagrania, gdy użytkownik prosi Capri o przedstawienie się.')
        self.intent_edit.setFixedHeight(65)
        edit.addWidget(self.intent_edit)
        self.match_mode = QComboBox()
        self.match_mode.addItem('Dokładne pytanie (interpunkcja ignorowana)', 'exact')
        self.match_mode.addItem('Pytanie zawiera frazę (całe słowa)', 'contains')
        edit.addWidget(self.match_mode)
        form_row = QHBoxLayout()
        self.language = QComboBox()
        self.language.addItem('Polski', 'pl')
        self.language.addItem('English', 'en')
        form_row.addWidget(QLabel('JĘZYK:'))
        form_row.addWidget(self.language)
        self.enabled = QCheckBox('AKTYWNE')
        self.enabled.setChecked(True)
        form_row.addWidget(self.enabled)
        form_row.addStretch(1)
        edit.addLayout(form_row)

        modify = QHBoxLayout()
        self.save_btn = QPushButton('✓  ZAPISZ ZMIANY')
        self.save_btn.setProperty('kind', 'primary')
        self.play_btn = QPushButton('▶  ODSŁUCHAJ')
        self.delete_btn = QPushButton('✕  USUŃ')
        modify.addWidget(self.save_btn, 1)
        modify.addWidget(self.play_btn)
        modify.addWidget(self.delete_btn)
        edit.addLayout(modify)
        self.generate_btn = QPushButton('◈  WYGENERUJ NOWE NAGRANIE • FISH VULKAN')
        self.generate_btn.setToolTip('Generuje lokalnie — wymaga uruchomionego serwera Fish Vulkan')
        edit.addWidget(self.generate_btn)
        edit.addWidget(QLabel('03 / SPRAWDŹ DOPASOWANIE'))
        self.preview_question = QLineEdit()
        self.preview_question.setPlaceholderText('Wpisz przykładową wiadomość do Capri')
        edit.addWidget(self.preview_question)
        self.preview_btn = QPushButton('⌕  TESTUJ PYTANIE / INTENCJĘ')
        edit.addWidget(self.preview_btn)
        edit.addStretch(1)
        editor_scroller.setWidget(editor)
        split.addWidget(editor_scroller)
        split.setSizes([520, 510])

        self.status = QLabel('Gotowe.')
        self.status.setWordWrap(True)
        self.status.setObjectName('Status')
        layout.addWidget(self.status)

        self.new_btn.clicked.connect(self.new_entry)
        self.import_btn.clicked.connect(self.import_file)
        self.save_btn.clicked.connect(self.save_entry)
        self.play_btn.clicked.connect(self.play_entry)
        self.delete_btn.clicked.connect(self.delete_entry)
        self.generate_btn.clicked.connect(self.generate_audio)
        self.preview_btn.clicked.connect(self.preview_rule)
        apply_style(self, '''
            QWidget { background:#0B1524; color:#E4F4FF; font:11px 'Segoe UI'; }
            QLabel { color:#C2D9E5; background:transparent; }
            QLabel#Title { color:#41FF70; font:bold 21px 'Bahnschrift'; }
            QLabel#Status { color:#48F0FF; border-left:2px solid #41FF70;
                            padding:8px; background:#13273A; }
            QFrame#Panel { background:#102236; border:1px solid #37627B;
                           border-top:1px solid #315A6C; }
            QLineEdit, QPlainTextEdit, QComboBox { background:#091827; color:#F2F8FD;
                          border:1px solid #41677D; padding:8px; selection-background-color:#A3385F; }
            QLineEdit:focus, QPlainTextEdit:focus { border-color:#41FF70; }
            QPushButton { background:#1B3045; color:#DFF6FA; border:1px solid #446E86;
                          min-height:34px;
                          padding:3px 9px; font:bold 10px Consolas; }
            QPushButton:hover { background:#30495D; border-color:#41FF70; }
            QPushButton[kind='primary'] { background:#41FF70; color:#081622; border-color:#81F5A0; }
            QTableWidget { background:#0B1B2D; alternate-background-color:#152D41;
                           border:1px solid #31576C; gridline-color:#274A5E; }
            QTableWidget::item:selected { background:#31566C; color:#FFFFFF; }
            QHeaderView::section { background:#182C3D;color:#B8D5DF;border:0;
                                   border-bottom:1px solid #356276;padding:7px; }
            QScrollArea { border:0; background:#102236; }
            QScrollBar:vertical { width:8px; background:#0B1928; }
            QScrollBar::handle:vertical { background:#3F7387; min-height:20px; }
            QSplitter::handle { background:#284658; width:5px; }
        ''')
        if is_modern():
            self.resize(1180, 820)
            layout.setContentsMargins(28,24,28,24)
            layout.setSpacing(18)
            title.setText('Biblioteka głosu')
            guide.setObjectName('ToolDescription')
            split.setSizes([460,660])
        self.ui_lang = ui_language_from_profile()
        apply_ui_language(self, self.ui_lang)
        self.refresh()

    def set_status(self, value: str):
        self.status.setText(translate_ui(value, getattr(self, "ui_lang", "pl")))

    def _text(self) -> str:
        return self.text_edit.toPlainText().strip()

    def _lang(self) -> str:
        return self.language.currentData()

    def _triggers(self) -> list[str]:
        return self.triggers_edit.toPlainText().splitlines()

    def _match_mode(self) -> str:
        return self.match_mode.currentData()

    def _error(self, text: str):
        topmost_notify(self, 'Capri — Menedżer Głosu', text, QMessageBox.Icon.Warning)
        self.set_status(text)

    def refresh(self, *, select_id: str | None = None):
        try:
            self.entries = list_entries()
        except (OSError, ValueError) as exc:
            self.entries = []
            self._error(str(exc))
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.entries))
        selected_row = None
        for row, entry in enumerate(self.entries):
            values = [entry.get('text', ''), ', '.join(entry.get('triggers', [])) or '—', entry.get('language', ''),
                      'Fish lokalny' if entry.get('origin') == 'fish' else 'Import WAV/MP3',
                      'TAK' if entry.get('enabled', True) else 'NIE']
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col != 0:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setToolTip(str(value))
                self.table.setItem(row, col, cell)
            if entry.get('id') == select_id:
                selected_row = row
        self.table.blockSignals(False)
        self._filter_entries()
        if selected_row is not None:
            self.table.selectRow(selected_row)
            self._selection_changed()

    def _selection_changed(self):
        row = self.table.currentRow()
        if not 0 <= row < len(self.entries):
            return
        item = self.entries[row]
        self.selected_id = item.get('id')
        self.text_edit.setPlainText(item.get('text', ''))
        self.triggers_edit.setPlainText('\n'.join(item.get('triggers', [])))
        self.intent_edit.setPlainText(item.get('intent', ''))
        self.match_mode.setCurrentIndex(0 if item.get('match_mode', 'exact') == 'exact' else 1)
        self.language.setCurrentIndex(0 if item.get('language') == 'pl' else 1)
        self.enabled.setChecked(bool(item.get('enabled', True)))
        self.set_status('Wybrano nagranie. Możesz edytować tekst, odsłuchać je lub usunąć.')

    def new_entry(self):
        self.selected_id = None
        self.table.clearSelection()
        self.text_edit.clear()
        self.triggers_edit.clear()
        self.intent_edit.clear()
        self.match_mode.setCurrentIndex(0)
        self.enabled.setChecked(True)
        self.set_status('Wpisz tekst i wybierz IMPORTUJ lub WYGENERUJ.')
        self.text_edit.setFocus()

    def import_file(self):
        if self.working:
            return
        text = self._text()
        if not text:
            self._error('Najpierw wpisz dokładny tekst nagrania.')
            return
        file, _ = topmost_open_file(self, 'Wybierz gotowe nagranie', '', 'Nagrania (*.wav *.mp3)')
        if not file:
            return
        try:
            entry = add_audio(file, text, self._lang(), origin='import',
                              triggers=self._triggers(), match_mode=self._match_mode(),
                              intent=self.intent_edit.toPlainText().strip())
        except (OSError, ValueError) as exc:
            self._error(str(exc))
            return
        self.refresh(select_id=entry['id'])
        self.set_status('Zaimportowano. Nagranie jest gotowe — nie trzeba ponownie generować głosu.')

    def save_entry(self):
        if not self.selected_id:
            self._error('Najpierw wybierz nagranie z listy. Dla nowego tekstu użyj IMPORTUJ lub WYGENERUJ.')
            return
        try:
            changed = update_entry(self.selected_id, self._text(), self._lang(),
                                   enabled=self.enabled.isChecked(),
                                   triggers=self._triggers(), match_mode=self._match_mode(),
                              intent=self.intent_edit.toPlainText().strip())
        except (OSError, ValueError) as exc:
            self._error(str(exc))
            return
        self.refresh(select_id=changed['id'])
        self.set_status('Zapisano tekst, pytania i aktywność. Capri odczyta zmiany automatycznie.')

    def _selected(self):
        return next((x for x in self.entries if x.get('id') == self.selected_id), None)

    def play_entry(self):
        item = self._selected()
        if not item:
            self._error('Najpierw wybierz nagranie z listy.')
            return
        path = entry_audio(item)
        if not path:
            self._error('Plik audio nie istnieje lub jest uszkodzony.')
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()
        self.set_status('Odtwarzanie: ' + item.get('text', '')[:80])

    def preview_rule(self):
        question = self.preview_question.text().strip()
        if not question:
            self.set_status('Wpisz przykładowe pytanie, aby sprawdzić zapisane reguły.')
            return
        match = find_for_question(question, self._lang())
        if match:
            self.set_status('PASUJE: ' + match['text'][:150] + '  •  dopasowanie bezpośrednie')
            return
        model = load_settings().get('local_model', 'SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M')
        language = self._lang()
        self.preview_btn.setEnabled(False)
        self.set_status('Lokalny model sprawdza sens pytania (Ollama)...')
        def work():
            try:
                result = semantic_voice_rule_match(question, language, model)
            except Exception:
                result = None
            self.match_signals.ready.emit(result)
        threading.Thread(target=work, daemon=True).start()

    def _preview_semantic_result(self, match):
        self.preview_btn.setEnabled(True)
        if match:
            self.set_status('SEMANTYCZNIE PASUJE: ' + match['text'][:150] +
                            '  • pewność modelu: ' + str(match.get('confidence', '?')) + '%')
        else:
            self.set_status('Brak pewnego dopasowania. Capri użyje zwykłej rozmowy / Agenta PC.')

    def _audio_error(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self.set_status('Nie udało się odtworzyć nagrania: ' + str(error_string))

    def delete_entry(self):
        item = self._selected()
        if not item:
            self._error('Najpierw wybierz nagranie z listy.')
            return
        if topmost_confirm(self, 'Usuń nagranie',
                'Trwale usunąć nagranie i jego przypisany tekst?') != QMessageBox.StandardButton.Yes:
            return
        try:
            self.player.stop()
            remove_entry(item['id'])
        except (OSError, ValueError) as exc:
            self._error(str(exc))
            return
        self.new_entry()
        self.refresh()
        self.set_status('Nagranie usunięte.')

    def _working(self, value: bool):
        self.working = value
        for button in (self.generate_btn, self.import_btn, self.save_btn, self.delete_btn):
            button.setEnabled(not value)

    def generate_audio(self):
        if self.working:
            return
        text = self._text()
        if not text:
            self._error('Wpisz tekst do wygenerowania.')
            return
        if len(text) > 1200:
            self._error('Tekst jest za długi (maks. 1200 znaków).')
            return
        settings = load_settings()
        base_ref = settings.get('voice_ref_path', '')
        transcript = settings.get('fish_ref_transcript', '')
        transcript_path = settings.get('fish_ref_path', '')
        try:
            ref = fish_reference_path(base_ref)
            if not Path(ref).is_file() or not transcript or Path(ref).resolve() != Path(transcript_path).resolve():
                raise ValueError('Najpierw ustaw próbkę głosu i jej transkrypcję w głównej Capri.')
            port = int(settings.get('s2_port', DEFAULT_S2_PORT))
        except (OSError, TypeError, ValueError) as exc:
            self._error(str(exc))
            return
        language = self._lang()
        try:
            triggers, match_mode = validate_rules(self._triggers(), self._match_mode())
        except ValueError as exc:
            self._error(str(exc))
            return
        intent = self.intent_edit.toPlainText().strip()
        self._working(True)
        self.set_status('Fish Vulkan generuje nagranie…')

        def job():
            result = None
            try:
                result = synthesize_s2cpp(text, language, ref, transcript,
                    transcript_reference_path=transcript_path, port=port,
                    profile=settings.get('voice_profile', 'clear'),
                    whisper=False,
                    emotion_intensity=int(settings.get('fish_emotion_intensity', 65)),
                    auto_emotions=bool(settings.get('fish_emotions_enabled', True)),
                    progress=lambda phase: self.async_signals.progress.emit('Fish Vulkan: ' + str(phase)))
                entry = add_audio(result, text, language, origin='fish',
                                  triggers=triggers, match_mode=match_mode, intent=intent)
                self.async_signals.ready.emit(entry['id'])
            except Exception as exc:
                self.async_signals.failure.emit(str(exc))
            finally:
                if result:
                    try:
                        Path(result).unlink(missing_ok=True)
                    except OSError:
                        pass

        threading.Thread(target=job, daemon=True).start()

    def _generate_done(self, item_id: str):
        self._working(False)
        self.refresh(select_id=item_id)
        self.set_status('Wygenerowano nagranie. Może reagować na przypisane pytania oraz zgodną odpowiedź AI.')

    def _generate_failed(self, error: str):
        self._working(False)
        self._error('Nie udało się wyrenderować: ' + error)

    def _filter_entries(self, *_):
        term = self.search.text().strip().casefold()
        for row in range(self.table.rowCount()):
            haystack = ' '.join(self.table.item(row, col).text()
                                for col in range(self.table.columnCount())
                                if self.table.item(row, col))
            self.table.setRowHidden(row, bool(term) and term not in haystack.casefold())

    def open_folder(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        try:
            if not reveal_folder(ROOT):
                self.set_status('Nie udało się otworzyć folderu: ' + str(ROOT))
        except OSError as exc:
            self._error(str(exc))

    def open_selected_folder(self):
        entry = self._selected()
        if not entry:
            self.open_folder()
            return
        path = entry_audio(entry)
        if not path:
            self._error('Wybrany plik nagrania nie istnieje.')
            return
        try:
            if not reveal_folder(Path(path).parent):
                self._error('Nie można otworzyć folderu wybranego pliku.')
        except OSError as exc:
            self._error(str(exc))


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    install_theme(app, saved_theme())
    window = VoiceManager()
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
