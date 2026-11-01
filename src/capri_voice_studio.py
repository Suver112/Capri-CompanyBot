"""Standalone editor + WSL Piper fine-tuning launcher for a user-owned voice.

Not IVONA. Piper training requires an external environment; this tool does not
silently install toolchains, models, or arbitrary third-party scripts.
"""
from __future__ import annotations
from capri_i18n import apply_ui_language, ui_language_from_profile, translate_ui
from capri_theme import apply_style, install_theme, saved_theme, is_modern, MAIN, THEMES
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid
import wave

from PySide6.QtCore import QProcess, Qt, QThread, Signal, QUrl, QTimer
from capri_ui_dialogs import (open_file as topmost_open_file, open_files as topmost_open_files,
                              reveal_folder, notify as topmost_notify)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QPlainTextEdit, QComboBox, QGroupBox, QHeaderView, QTabWidget)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from capri_auto_dataset import Options as AutoOptions, auto_prepare_dataset
from capri_piper_import import audio_duration_seconds
from capri_piper_engine import ROOT, installed_model, install_model

PROJECT = ROOT / 'training'
CLIPS = PROJECT / 'audio'
METADATA = PROJECT / 'metadata.csv'


def windows_to_wsl(path: str | Path) -> str:
    """Mapped C:\\... path, no network locations or shell interpolations."""
    resolved = Path(path).resolve()
    raw = str(resolved)
    found = re.match(r'^([A-Za-z]):\\(.*)$', raw)
    if not found:
        raise ValueError('Trening WSL wymaga folderu na lokalnym dysku Windows, np. C:.')
    return '/mnt/' + found.group(1).lower() + '/' + found.group(2).replace('\\', '/')


def prepare_clip(source: str | Path, destination: Path) -> None:
    """Mono PCM16 22050 Hz, one clean utterance per training row."""
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('Do importu próbek potrzebny jest FFmpeg w PATH (ffmpeg.exe).')
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
        '-i', str(source), '-vn', '-ac', '1', '-ar', '22050', '-c:a', 'pcm_s16le', str(destination)],
        capture_output=True, text=True, timeout=60,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if completed.returncode or not destination.exists():
        destination.unlink(missing_ok=True)
        raise RuntimeError('FFmpeg: ' + completed.stderr[-500:])
    try:
        with wave.open(str(destination), 'rb') as wav:
            duration = wav.getnframes() / max(1, wav.getframerate())
    except wave.Error as exc:
        destination.unlink(missing_ok=True)
        raise RuntimeError('Błędny WAV.') from exc
    if not 0.4 <= duration <= 30:
        destination.unlink(missing_ok=True)
        raise ValueError('Próbki powinny mieć 0,4–30 sekund. Podziel dłuższy materiał na pojedyncze zdania.')


def load_clips() -> list[tuple[str, str]]:
    path = PROJECT / 'clips.json'
    if not path.is_file():
        return []
    try:
        items = json.loads(path.read_text(encoding='utf-8'))
        return [(x['file'], x['text']) for x in items if isinstance(x, dict)
                and re.fullmatch(r'[a-f0-9]{32}\.wav', str(x.get('file', '')))
                and isinstance(x.get('text'), str)]
    except (ValueError, OSError, KeyError, TypeError):
        return []


def save_clips(clips: list[tuple[str, str]]) -> int:
    PROJECT.mkdir(parents=True, exist_ok=True)
    clean = []
    for filename, text in clips:
        if not re.fullmatch(r'[a-f0-9]{32}\.wav', filename) or not (CLIPS / filename).is_file():
            continue
        text = ' '.join(str(text).split()).replace('|', ',')
        if not text or len(text) > 500:
            raise ValueError('Każda próbka wymaga zgodnej z nagraniem transkrypcji (1–500 znaków).')
        clean.append((filename, text))
    if not clean:
        raise ValueError('Dodaj i opisz przynajmniej jedną próbkę.')
    (PROJECT / 'clips.json').write_text(json.dumps(
        [{'file': f, 'text': t} for f, t in clean], indent=2, ensure_ascii=False), encoding='utf-8')
    METADATA.write_text(''.join(f'{name}|{text}\n' for name, text in clean), encoding='utf-8')
    return len(clean)


def load_reviewed_clips() -> list[dict]:
    """Backward compatible: older entries were manually transcribed and approved."""
    path = PROJECT / 'clips.json'
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, list):
            return []
        clean = []
        for item in raw:
            if (isinstance(item, dict) and re.fullmatch(r'[a-f0-9]{32}\.wav', str(item.get('file', '')))
                    and isinstance(item.get('text'), str)):
                clean.append({'file': item['file'], 'text': item['text'],
                              'approved': item.get('approved', True) is True,
                              'confidence': item.get('confidence', None),
                              'source': str(item.get('source', ''))[:255],
                              'review': str(item.get('review', ''))[:80]})
        return clean
    except (OSError, ValueError, TypeError):
        return []


def save_reviewed_clips(items: list[dict]) -> tuple[int, int]:
    """All drafts persist; metadata.csv receives ONLY manually approved pairs."""
    PROJECT.mkdir(parents=True, exist_ok=True)
    clean: list[dict] = []
    eligible = []
    for item in items:
        filename = str(item.get('file', ''))
        if not re.fullmatch(r'[a-f0-9]{32}\.wav', filename) or not (CLIPS / filename).is_file():
            raise ValueError('Brak pliku WAV próbki: ' + filename)
        phrase = ' '.join(str(item.get('text', '')).split()).replace('|', ',')
        approved = item.get('approved') is True
        if len(phrase) > 500 or (approved and not phrase):
            raise ValueError('Zatwierdzona próbka wymaga poprawnej transkrypcji (1–500 znaków).')
        cleaned = {'file': filename, 'text': phrase, 'approved': approved,
                   'confidence': item.get('confidence'),
                   'source': str(item.get('source', ''))[:255],
                   'review': str(item.get('review', ''))[:80]}
        clean.append(cleaned)
        if approved:
            eligible.append((filename, phrase))
    if not clean:
        raise ValueError('Nie masz żadnych próbek w projekcie.')
    # Write both temp files before replacing existing project state.
    import tempfile
    temp_paths = []
    try:
        for target, data in (
            (PROJECT / 'clips.json', json.dumps(clean, indent=2, ensure_ascii=False)),
            (METADATA, ''.join(f'{name}|{text}\n' for name, text in eligible)),
        ):
            fd, name = tempfile.mkstemp(dir=PROJECT, prefix='.capri-', suffix='.tmp')
            temp_paths.append((Path(name), target))
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        for src, dst in temp_paths:
            os.replace(src, dst)
    finally:
        for src, _ in temp_paths:
            src.unlink(missing_ok=True)
    return len(clean), len(eligible)


class AutoSttWorker(QThread):
    progress = Signal(str)
    clips_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, sources: list[str], options: AutoOptions, parent=None):
        super().__init__(parent)
        self.sources = sources
        self.options = options

    def run(self):
        try:
            rows = auto_prepare_dataset(
                self.sources, CLIPS, self.options, model_dir=ROOT.parent / 'models',
                report=self.progress.emit, canceled=self.isInterruptionRequested)
            self.clips_ready.emit(rows)
        except Exception as exc:
            self.failed.emit(f'{type(exc).__name__}: {exc}')



def write_training_script(epochs: int = 100, checkpoint: str = '') -> Path:
    """Generate a MOS-safe Piper trainer, with checkpoints and logs on WSL ext4.

    The optional UTMOS scoring is disabled to keep validation independent from
    external MOS predictors. Best/last checkpoints use the real val_mel metric.
    All changes live in this generated launcher, never inside the Piper install.
    """
    project = windows_to_wsl(PROJECT)
    checkpoint = windows_to_wsl(checkpoint) if checkpoint else ''
    escaped_project = shlex.quote(project)
    escaped_checkpoint = shlex.quote(checkpoint)
    content = f'''#!/usr/bin/env bash
set -euo pipefail
P={escaped_project}
REPO="$HOME/piper1-gpl"
PY="$REPO/.venv/bin/python"
# Keep checkpoints, cache, logs and temporary export on WSL ext4, NOT /mnt/c.
RUN_DIR="$HOME/.local/share/capri-piper/runs"
CACHE_DIR="$HOME/.cache/capri-piper/dataset"
EXPORT_DIR="$HOME/.local/share/capri-piper/export"
if [[ ! -x "$PY" ]]; then
  echo 'BRAK PIPER: Skonfiguruj ~/piper1-gpl/.venv w WSL.' >&2
  exit 20
fi
if [[ ! -s "$P/metadata.csv" ]]; then
  echo 'Brak zatwierdzonych probek w metadata.csv.' >&2
  exit 22
fi
mkdir -p "$RUN_DIR" "$CACHE_DIR" "$EXPORT_DIR"
RUN_TAG="$(date +%Y%m%d_%H%M%S)_$$"
SESSION_DIR="$RUN_DIR/$RUN_TAG"
mkdir -p "$SESSION_DIR"
LOG_FILE="$SESSION_DIR/capri_piper_full_log.txt"
# Log remains on Linux during training; copy to Windows only on exit.
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'status=$?; if [[ "$status" -ne 0 ]]; then echo "CAPRI PIPER ERROR code=$status. Full log: $LOG_FILE"; fi; cp "$LOG_FILE" "$P/capri_piper_full_log.txt" 2>/dev/null || true; exit "$status"' EXIT
echo "CAPRI PIPER: checkpointy WSL: $SESSION_DIR"
echo "CAPRI PIPER: log WSL: $LOG_FILE"
echo "CAPRI PIPER: dane: $P"
# Detect a missing exporter dependency BEFORE spending hours training.
if ! "$PY" -c 'import onnx; import onnxscript' >/dev/null 2>&1; then
  echo 'Brakuje onnx / onnxscript w WSL. Zainstaluj: ~/piper1-gpl/.venv/bin/python -m pip install onnx onnxscript' >&2
  exit 26
fi
RESUME_CKPT={escaped_checkpoint}
if [[ -n "$RESUME_CKPT" ]]; then
  if [[ ! -f "$RESUME_CKPT" ]]; then
    echo 'Nie znaleziono wybranego checkpointu.' >&2
    exit 23
  fi
  # Move imported Windows checkpoint to ext4; original is preserved.
  cp "$RESUME_CKPT" "$SESSION_DIR/resume_import.ckpt"
  RESUME_CKPT="$SESSION_DIR/resume_import.ckpt"
fi
# Smaller datasets benefit from smaller batches. Never edit Piper packages.
N_SAMPLES="$(grep -cve '^[[:space:]]*$' "$P/metadata.csv" || true)"
if (( N_SAMPLES < 1 )); then echo 'Zbior danych jest pusty.' >&2; exit 22; fi
if (( N_SAMPLES < 16 )); then
  BATCH_SIZE=2
elif (( N_SAMPLES < 50 )); then
  BATCH_SIZE=4
else
  BATCH_SIZE=8
fi
echo "CAPRI PIPER: $N_SAMPLES zatwierdzonych probek, batch size $BATCH_SIZE"
# The upstream piper.train entry point registers an optional val_mos callback.
# UTMOS may be unavailable: use val_mel only and disable the optional predictor.
cat > "$SESSION_DIR/capri_train_mos_safe.py" <<'CAPRI_PY'
import inspect
import logging
import sys
from lightning.pytorch.callbacks import ModelCheckpoint
from piper.train import __main__ as cli
from piper.train.vits.lightning import VitsModel

if not hasattr(cli, '_DEFAULT_CALLBACKS') or not callable(getattr(cli, 'main', None)):
    raise RuntimeError('Ta wersja piper1-gpl ma inny interfejs. Nie podmieniam plikow Pipera. Zaktualizuj integracje Studio.')
cli._DEFAULT_CALLBACKS = [
    ModelCheckpoint(
        monitor='val_mel', mode='min', save_top_k=5, save_last=True,
        filename='epoch={{epoch}}-val_mel={{val_mel:.4f}}',
        auto_insert_metric_name=False,
    )
]
# Older Piper builds have no MOS option; pass it only when supported.
if 'mos_metric' in inspect.signature(VitsModel.__init__).parameters:
    sys.argv.extend(['--model.mos_metric', 'none'])
else:
    logging.warning('Piper bez model.mos_metric; MOS callback zostal wylaczony.')
cli.main()
CAPRI_PY
ARGS=(
  --data.voice_name capri
  --data.csv_path "$P/metadata.csv"
  --data.audio_dir "$P/audio"
  --model.sample_rate 22050
  --data.espeak_voice pl
  --data.cache_dir "$CACHE_DIR"
  --data.config_path "$P/capri.onnx.json"
  --data.batch_size "$BATCH_SIZE"
  --trainer.default_root_dir "$SESSION_DIR"
  --trainer.log_every_n_steps 1
  --trainer.max_epochs {int(epochs)}
)
if [[ -n "$RESUME_CKPT" ]]; then ARGS+=(--ckpt_path "$RESUME_CKPT"); fi
"$PY" "$SESSION_DIR/capri_train_mos_safe.py" fit "${{ARGS[@]}}"
# Select a checkpoint only from THIS run, never a previous session.
CHECKPOINT="$(find "$SESSION_DIR" -type f -name 'last.ckpt' -printf '%T@ %p\n' | sort -nr | sed -n '1p' | cut -d' ' -f2-)"
if [[ -z "$CHECKPOINT" ]]; then
  CHECKPOINT="$(find "$SESSION_DIR" -type f -name '*.ckpt' -printf '%T@ %p\n' | sort -nr | sed -n '1p' | cut -d' ' -f2-)"
fi
if [[ -z "$CHECKPOINT" ]]; then echo 'Trening nie zapisal checkpointu.' >&2; exit 21; fi
# Export on ext4. Do not alter the user's installed model unless export succeeds.
"$PY" -m piper.train.export_onnx --checkpoint "$CHECKPOINT" --output-file "$EXPORT_DIR/capri.onnx"
if [[ ! -s "$EXPORT_DIR/capri.onnx" ]]; then
  echo 'Nie udalo sie wyeksportowac pliku ONNX.' >&2
  exit 25
fi
if ! cp "$EXPORT_DIR/capri.onnx" "$P/capri.onnx"; then
  echo 'Eksport ONNX powiodl sie, ale skopiowanie do Windows nie.' >&2
  echo "Oryginal pozostaje w $EXPORT_DIR/capri.onnx" >&2
  exit 24
fi
echo "CAPRI TRAINING DONE: $P/capri.onnx"
'''
    PROJECT.mkdir(parents=True, exist_ok=True)
    out = PROJECT / 'train_piper.sh'
    out.write_text(content, encoding='utf-8', newline='\n')
    return out


class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CAPRI // STUDIO WŁASNEGO GŁOSU — PIPER')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(1100, 835)
        self.setMinimumSize(850, 635)
        self.job = None
        self.auto_worker = None
        self.pending_auto_sources = []
        self._dataset_save_timer = QTimer(self)
        self._dataset_save_timer.setSingleShot(True)
        self._dataset_save_timer.setInterval(450)
        self._dataset_save_timer.timeout.connect(self._save_dataset_after_edit)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.75)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        heading = QLabel('STUDIO GŁOSU CAPRI  •  Piper ONNX  •  dataset + trening WSL')
        root.addWidget(heading)
        description = QLabel('To trenowany głos Piper, a nie klasyczna IVONA. Dodawaj krótkie nagrania z dokładnymi tekstami. '
                             'Do samego treningu wymagany jest skonfigurowany Piper w WSL (osobno od Capri).')
        description.setWordWrap(True)
        root.addWidget(description)
        # Two independent workspaces: dataset cleaning and actual training.
        # Keeping existing widgets ensures no behavior or signal is lost.
        self.studio_tabs = QTabWidget()
        self.studio_tabs.setDocumentMode(True)
        prep_page = QWidget()
        prep_layout = QVBoxLayout(prep_page)
        prep_layout.setContentsMargins(12, 12, 12, 12)
        prep_layout.setSpacing(12)
        train_page = QWidget()
        training_layout = QVBoxLayout(train_page)
        training_layout.setContentsMargins(12, 12, 12, 12)
        training_layout.setSpacing(12)
        self.studio_tabs.addTab(prep_page, 'Nagrania i przygotowanie')
        self.studio_tabs.addTab(train_page, 'Trening i eksport')
        root.addWidget(self.studio_tabs, 1)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            'NAGRANIE WAV', 'TEKST (POPRAW PRZED TRENINGIEM)', 'ZATWIERDŹ', 'PEWNOŚĆ STT'])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 105)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._row_edited)
        prep_layout.addWidget(self.table, 1)
        prep_layout.addWidget(QLabel('Automatyczne transkrypcje to wersje robocze. Odsłuchaj, popraw tekst i zaznacz „ZATWIERDŹ” przed treningiem.'))

        row = QHBoxLayout()
        add = QPushButton('DODAJ NAGRANIA • AUTO-CIĘCIE >30 s')
        add.clicked.connect(self.add_clips)
        row.addWidget(add)
        play = QPushButton('▶ ODSŁUCHAJ')
        play.clicked.connect(self.play_clip)
        row.addWidget(play)
        self.pause_btn = QPushButton('■ ZATRZYMAJ')
        self.pause_btn.clicked.connect(self.player.stop)
        row.addWidget(self.pause_btn)
        remove = QPushButton('USUŃ PRÓBKĘ')
        remove.clicked.connect(self.remove_clip)
        row.addWidget(remove)
        save = QPushButton('ZAPISZ TEKSTY / DATASET')
        save.clicked.connect(self.save_dataset)
        row.addWidget(save)
        prep_layout.addLayout(row)
        auto_box = QGroupBox('AUTO STT + AUTOMATYCZNE CIĘCIE • PIPER')
        auto_col = QVBoxLayout(auto_box)
        auto_fields = QHBoxLayout()
        auto_fields.addWidget(QLabel('Silnik STT:'))
        self.stt_model = QComboBox()
        self.stt_model.addItems(['small', 'parakeet-v3', 'medium', 'large-v3', 'base'])
        self.stt_model.setToolTip('Parakeet v3: lokalny CPU ONNX; wymaga Napraw Capri (menu Start). Cięcie wg pauz, bez sztucznych word timestamps.')
        auto_fields.addWidget(self.stt_model)
        auto_fields.addWidget(QLabel('Język:'))
        self.stt_lang = QComboBox()
        self.stt_lang.addItem('Polski', 'pl')
        self.stt_lang.addItem('Angielski', 'en')
        self.stt_lang.addItem('Auto', None)
        auto_fields.addWidget(self.stt_lang)
        auto_fields.addWidget(QLabel('Min (s):'))
        self.min_clip = QDoubleSpinBox()
        self.min_clip.setRange(0.5, 8.0)
        self.min_clip.setSingleStep(0.5)
        self.min_clip.setValue(1.5)
        auto_fields.addWidget(self.min_clip)
        auto_fields.addWidget(QLabel('Max (s):'))
        self.max_clip = QDoubleSpinBox()
        self.max_clip.setRange(3.0, 30.0)
        self.max_clip.setValue(12.0)
        auto_fields.addWidget(self.max_clip)
        auto_col.addLayout(auto_fields)
        auto_settings = QHBoxLayout()
        auto_settings.addWidget(QLabel('Pauza do cięcia (ms):'))
        self.pause_ms = QSpinBox()
        self.pause_ms.setRange(100, 1800)
        self.pause_ms.setSingleStep(100)
        self.pause_ms.setValue(500)
        auto_settings.addWidget(self.pause_ms)
        auto_settings.addWidget(QLabel('Margines audio (ms):'))
        self.margin_ms = QSpinBox()
        self.margin_ms.setRange(0, 350)
        self.margin_ms.setValue(140)
        auto_settings.addWidget(self.margin_ms)
        auto_settings.addStretch(1)
        self.auto_button = QPushButton('◈ AUTO STT + PODZIEL DŁUGIE AUDIO')
        self.auto_button.clicked.connect(self.auto_import)
        auto_settings.addWidget(self.auto_button)
        self.cancel_auto_button = QPushButton('■ ANULUJ')
        self.cancel_auto_button.clicked.connect(self.cancel_auto)
        self.cancel_auto_button.setEnabled(False)
        auto_settings.addWidget(self.cancel_auto_button)
        auto_col.addLayout(auto_settings)
        prep_layout.addWidget(auto_box)
        folders = QHBoxLayout()
        self.open_samples_btn = QPushButton('▣  OTWÓRZ FOLDER PRÓBEK')
        self.open_samples_btn.clicked.connect(lambda: reveal_folder(CLIPS))
        folders.addWidget(self.open_samples_btn)
        self.open_dataset_btn = QPushButton('▣  FOLDER TRENINGOWY')
        self.open_dataset_btn.clicked.connect(lambda: reveal_folder(PROJECT))
        folders.addWidget(self.open_dataset_btn)
        folders.addStretch(1)
        prep_layout.addLayout(folders)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('Epoki:'))
        self.epochs = QSpinBox()
        self.epochs.setRange(1, 5000)
        self.epochs.setValue(100)
        controls.addWidget(self.epochs)
        controls.addWidget(QLabel('Checkpoint (opcjonalnie, zalecany):'))
        self.checkpoint = QLineEdit()
        controls.addWidget(self.checkpoint, 1)
        choose = QPushButton('WYBIERZ .CKPT')
        choose.clicked.connect(self.choose_checkpoint)
        controls.addWidget(choose)
        training_layout.addLayout(controls)
        training_layout.addWidget(QLabel('PIPER: UTMOS/MOS wyłączony dla stabilności; checkpointy wg val_mel + last.'))
        buttons = QHBoxLayout()
        train = QPushButton('TRENUJ W WSL + ZAPISZ W CAPRI')
        train.clicked.connect(self.train)
        buttons.addWidget(train)
        import_model = QPushButton('ZAIMPORTUJ GOTOWY MODEL .ONNX')
        import_model.clicked.connect(self.import_voice)
        buttons.addWidget(import_model)
        training_layout.addLayout(buttons)
        self.status = QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(135)
        root.addWidget(self.log)
        for item in load_reviewed_clips():
            self.add_row(item['file'], item['text'], item.get('approved', True),
                         item.get('confidence'), item.get('source', ''))
        apply_style(self, """
            QWidget { background:#0B1625;color:#E8F5FA;font:11px 'Segoe UI'; }
            QLabel { color:#BBDBE8;background:transparent; }
            QPushButton { background:#122235;color:#D6E9F0;border:1px solid #34596A;
                          min-height:30px;padding:5px 10px;
                          font:bold 10px Consolas; }
            QPushButton:hover { background:#304A63;border-color:#41FF70; }
            QLineEdit, QSpinBox, QPlainTextEdit { background:#0C1F30;color:#EAF7FF;
                        border:1px solid #3C647B;padding:6px; }
            QTableWidget { background:#0A1E30;alternate-background-color:#172C42;
                           gridline-color:#345A70;border:1px solid #406F83; }
            QHeaderView::section { background:#162B3B;color:#B8D5DF;padding:8px; }
        """)
        if is_modern():
            self.resize(1180, 820)
            root.setContentsMargins(28,24,28,24)
            root.setSpacing(16)
            heading.setText('Studio głosu')
            heading.setObjectName('ToolTitle')
            description.setText('Przygotuj nagrania, popraw transkrypcje i wytrenuj własny głos Piper.')
            description.setObjectName('ToolDescription')
            for page_layout in (prep_layout, training_layout):
                page_layout.setContentsMargins(0,20,0,0)
                page_layout.setSpacing(20)
        self.design_tabs = self.studio_tabs
        self.ui_lang = ui_language_from_profile()
        apply_ui_language(self, self.ui_lang)
        self.update_status()
        if self.table.rowCount():
            self.log.appendPlainText(
                f'Wczytano {self.table.rowCount()} zapisanych próbek. '
                'Nie trzeba ponownie uruchamiać Auto STT dla tych samych nagrań.')

    def update_status(self):
        status = translate_ui('ZAINSTALOWANY MODEL: ', getattr(self, 'ui_lang', 'pl')) + translate_ui('TAK' if installed_model() else 'NIE', getattr(self, 'ui_lang', 'pl'))
        self.status.setText(status + '  |  Folder: ' + str(PROJECT))

    def add_row(self, filename, text='', approved=True, confidence=None, source=''):
        row_index = self.table.rowCount()
        self.table.blockSignals(True)
        try:
            self.table.insertRow(row_index)
            name = QTableWidgetItem(filename)
            name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name.setData(Qt.ItemDataRole.UserRole, source)
            self.table.setItem(row_index, 0, name)
            self.table.setItem(row_index, 1, QTableWidgetItem(text))
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable |
                           Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Checked if approved else Qt.CheckState.Unchecked)
            self.table.setItem(row_index, 2, check)
            prob = QTableWidgetItem(f'{float(confidence) * 100:.0f}%' if confidence is not None else '—')
            prob.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            prob.setData(Qt.ItemDataRole.UserRole, confidence)
            self.table.setItem(row_index, 3, prob)
            if confidence is not None and confidence < 0.72:
                prob.setToolTip(translate_ui('Niska pewność STT. Koniecznie sprawdź odsłuch i tekst.', getattr(self, 'ui_lang', 'pl')))
            name.setToolTip(('Source: ' if getattr(self, 'ui_lang', 'pl') == 'en' else 'Źródło: ') + source if source else filename)
        finally:
            self.table.blockSignals(False)

    def _save_dataset_after_edit(self):
        if self.table.rowCount():
            self.save_dataset()

    def _row_edited(self, item):
        if item.column() == 2 and item.checkState() == Qt.CheckState.Checked:
            text_item = self.table.item(item.row(), 1)
            if text_item is None or not text_item.text().strip():
                self.table.blockSignals(True)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.table.blockSignals(False)
                self.log.appendPlainText('Najpierw wpisz tekst próbki, potem zatwierdź.')
        # Persist edits without requiring Auto STT again after restarting Studio.
        self._dataset_save_timer.start()

    def add_clips(self):
        paths, _ = topmost_open_files(self, 'Próbki głosu Capri', '', 'Audio (*.wav *.mp3 *.flac *.m4a *.ogg)')
        if not paths:
            return
        long_files = []
        for path in paths:
            name = uuid.uuid4().hex + '.wav'
            try:
                # Manual samples can be left without text; long samples cannot.
                # Their STT transcript must be aligned to each automatically cut clip.
                if audio_duration_seconds(path) > 30.0:
                    long_files.append(path)
                    continue
                prepare_clip(path, CLIPS / name)
                self.add_row(name, approved=False, source=Path(path).name)
            except Exception as exc:
                (CLIPS / name).unlink(missing_ok=True)
                topmost_notify(self, 'Import nagrania', f'{Path(path).name}: {exc}', QMessageBox.Icon.Warning)
        self.log.appendPlainText('Nowe próbki są niezatwierdzone. Odsłuchaj i popraw tekst przed treningiem.')
        if long_files:
            self.log.appendPlainText(
                f'AUTO-CIĘCIE: {len(long_files)} długich nagrań (>30 s) → Whisper + podział na zdania.')
            self._start_auto_import(long_files)

    def _start_auto_import(self, paths: list[str]):
        if not paths:
            return
        if self.auto_worker and self.auto_worker.isRunning():
            # Preserve newly selected files until the running batch finishes.
            self.pending_auto_sources.extend(paths)
            self.log.appendPlainText(f'AUTO STT: dodano {len(paths)} plików do kolejki.')
            return
        options = AutoOptions(model=self.stt_model.currentText(),
                              language=self.stt_lang.currentData(),
                              min_seconds=self.min_clip.value(), max_seconds=self.max_clip.value(),
                              pause_ms=self.pause_ms.value(), margin_ms=self.margin_ms.value())
        try:
            options.checked()
        except ValueError as exc:
            topmost_notify(self, 'Auto STT', str(exc), QMessageBox.Icon.Warning)
            return
        self.auto_button.setEnabled(False)
        self.cancel_auto_button.setEnabled(True)
        self.log.appendPlainText(f'AUTO STT: {len(paths)} plików. Model {options.model}, język {options.language or "auto"}.')
        self.auto_worker = AutoSttWorker(paths, options, self)
        self.auto_worker.progress.connect(self.log.appendPlainText)
        self.auto_worker.clips_ready.connect(self.auto_done)
        self.auto_worker.failed.connect(self.auto_error)
        self.auto_worker.finished.connect(self.auto_finished)
        self.auto_worker.start()

    def auto_import(self):
        paths, _ = topmost_open_files(self, 'Długie nagrania do Auto STT', '',
                                      'Audio (*.wav *.mp3 *.flac *.m4a *.ogg)')
        self._start_auto_import(paths)

    def cancel_auto(self):
        if self.auto_worker and self.auto_worker.isRunning():
            self.auto_worker.requestInterruption()
            self.log.appendPlainText('Anulowanie zlecone — aktualny etap Whisper może jeszcze chwilę potrwać.')

    def auto_done(self, rows):
        for entry in rows:
            self.add_row(entry['file'], entry['text'], False, entry['confidence'], entry.get('source', ''))
        self.log.appendPlainText(f'AUTO STT: dodano {len(rows)} wersji roboczych. ZATWIERDŹ dopiero po odsłuchu.')
        if rows:
            self.save_dataset()

    def auto_error(self, detail):
        self.log.appendPlainText('AUTO STT: ' + detail)
        topmost_notify(self, 'Auto STT', detail, QMessageBox.Icon.Warning)

    def auto_finished(self):
        self.auto_button.setEnabled(True)
        self.cancel_auto_button.setEnabled(False)
        worker = self.auto_worker
        self.auto_worker = None
        if worker:
            worker.deleteLater()
        if self.pending_auto_sources:
            pending = self.pending_auto_sources[:30]
            del self.pending_auto_sources[:30]
            QTimer.singleShot(0, lambda: self._start_auto_import(pending))

    def play_clip(self):
        current = self.table.currentRow()
        if current < 0:
            return
        item = self.table.item(current, 0)
        if not item:
            return
        path = CLIPS / item.text()
        if not path.is_file():
            self.log.appendPlainText('Nie znaleziono nagrania: ' + str(path))
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def remove_clip(self):
        i = self.table.currentRow()
        if i < 0:
            return
        filename = self.table.item(i, 0).text()
        self.player.stop()
        self.table.removeRow(i)
        if self.table.rowCount():
            self._dataset_save_timer.start()
        (CLIPS / filename).unlink(missing_ok=True)

    def _get_rows(self):
        output = []
        for i in range(self.table.rowCount()):
            name_item, text_item = self.table.item(i, 0), self.table.item(i, 1)
            checked = self.table.item(i, 2)
            score = self.table.item(i, 3)
            if not name_item or not text_item or not checked:
                continue
            output.append({'file': name_item.text(), 'text': text_item.text(),
                           'approved': checked.checkState() == Qt.CheckState.Checked,
                           'confidence': score.data(Qt.ItemDataRole.UserRole) if score else None,
                           'source': name_item.data(Qt.ItemDataRole.UserRole) or ''})
        return output

    def save_dataset(self):
        try:
            total, approved = save_reviewed_clips(self._get_rows())
            self.log.appendPlainText(f'Zapisano {total} klipów, do treningu ZATWIERDZONO {approved}.')
            self.update_status()
            return True
        except Exception as exc:
            topmost_notify(self, 'Dataset', str(exc), QMessageBox.Icon.Warning)
            return False

    def choose_checkpoint(self):
        path, _ = topmost_open_file(self, 'Checkpoint Piper', '', 'Checkpoint (*.ckpt)')
        if path:
            self.checkpoint.setText(path)

    def train(self):
        if self.job is not None and self.job.state() != QProcess.ProcessState.NotRunning:
            topmost_notify(self, 'Trening', 'Trening jest już uruchomiony.')
            return
        if not self.save_dataset():
            return
        if not any(row['approved'] for row in self._get_rows()):
            topmost_notify(self, 'Trening', 'Najpierw odsłuchaj i ZATWIERDŹ przynajmniej jedną próbkę.', QMessageBox.Icon.Warning)
            return
        if self.auto_worker and self.auto_worker.isRunning():
            topmost_notify(self, 'Trening', 'Poczekaj na zakończenie Auto STT lub anuluj ten proces.', QMessageBox.Icon.Warning)
            return
        if os.name != 'nt' or not shutil.which('wsl.exe'):
            topmost_notify(self, 'WSL', 'Automatyczny start treningu wymaga Windows + WSL.', QMessageBox.Icon.Warning)
            return
        try:
            shell_script = write_training_script(self.epochs.value(), self.checkpoint.text().strip())
            script_wsl = windows_to_wsl(shell_script)
        except Exception as exc:
            topmost_notify(self, 'Trening', str(exc))
            return
        self.log.appendPlainText('Start Piper (bez MOS/UTMOS) w WSL: checkpointy, cache i pełny log na ext4; zapisuję 5 najlepszych wg val_mel i last.ckpt. Gotowy ONNX trafi do Capri. GPU/ROCm sprawdź osobno.')
        self.job = QProcess(self)
        self.job.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.job.readyReadStandardOutput.connect(self.read_job)
        self.job.finished.connect(self.finished_job)
        self.job.start('wsl.exe', ['-e', 'bash', script_wsl])

    def read_job(self):
        if self.job:
            self.log.appendPlainText(bytes(self.job.readAllStandardOutput()).decode('utf-8', errors='replace')[-4000:])

    def finished_job(self, exit_code, _status):
        self.read_job()
        if exit_code:
            self.log.appendPlainText(f'TRENING NIE ZAKOŃCZONY (kod {exit_code}). Model w Capri pozostaje bez zmian.')
        else:
            try:
                install_model(PROJECT / 'capri.onnx', PROJECT / 'capri.onnx.json')
                self.log.appendPlainText('MODEL GOTOWY. Automatycznie zainstalowany w Capri. Wybierz PIPER w modelach głosu.')
            except Exception as exc:
                self.log.appendPlainText('Trening się zakończył, ale import ONNX nie powiódł się: ' + str(exc))
        self.update_status()
        self.job = None

    def import_voice(self):
        path, _ = topmost_open_file(self, 'Wyeksportowany model Piper', '', 'Piper (*.onnx)')
        if not path:
            return
        cfg = path + '.json'
        if not Path(cfg).is_file():
            cfg, _ = topmost_open_file(self, 'Konfiguracja modelu Piper', '', 'JSON (*.json)')
        try:
            install_model(path, cfg)
            self.log.appendPlainText('Model zapisany w Capri. Przełącz silnik głosu na Piper.')
            self.update_status()
        except Exception as exc:
            topmost_notify(self, 'Model Piper', str(exc), QMessageBox.Icon.Warning)


def main():
    app = QApplication(sys.argv)
    install_theme(app, saved_theme())
    window = Studio()
    window.show()
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(main())
