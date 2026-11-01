"""Shared reversible appearance for all Capri Qt windows.

Original styles are retained per widget, never reconstructed from a recolored
stylesheet. Separate voice tools read the same persisted selection on startup.
"""
from __future__ import annotations
import json
import re
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

THEMES = {'capri': 'Basic', 'holocall': 'Holocall', 'silverhand': 'Silverhand'}


def selected_theme():
    app = QApplication.instance()
    value = (app.property('capri_theme') or 'holocall') if app else 'holocall'
    return value if value in THEMES else 'holocall'


def is_modern():
    return selected_theme() in ('capri', 'holocall', 'silverhand')


def saved_theme():
    from capri_paths import data_root
    try:
        value = json.loads((data_root() / 'settings.json').read_text(encoding='utf-8')).get('ui_theme')
        return value if value in THEMES else 'holocall'
    except (OSError, ValueError, TypeError):
        return 'holocall'


BASE = """
QWidget { color:#E8E6EA; font-family:'Segoe UI'; font-size:12px; }
QMainWindow, QDialog, QMessageBox { background:#191A1D; }
QLabel { background:transparent; }
QToolTip { color:#F3F1F4; background:#292A2F; border:1px solid #53555E; padding:7px; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
 background:#202125; color:#E8E6EA; border:1px solid #45464F; border-radius:4px;
 padding:7px; selection-background-color:#74324F; selection-color:#FFFFFF; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border:1px solid #FF175D; }
QComboBox QAbstractItemView, QMenu { background:#24252A; color:#E8E6EA;
 border:1px solid #45464F; selection-background-color:#74324F; padding:4px; }
QMenu::item { padding:7px 20px; }
QMenu::item:selected { background:#74324F; }
QPushButton, QToolButton { background:#292A2F; color:#E8E6EA;
 border:1px solid #45464F; border-radius:4px; padding:7px 11px; }
QPushButton:hover, QToolButton:hover { background:#35363D; border-color:#7E808B; }
QPushButton:pressed, QPushButton:checked { background:#543044; border-color:#FF175D; }
QPushButton:disabled, QLineEdit:disabled, QComboBox:disabled { color:#92939D; background:#232429; border-color:#383940; }
QAbstractItemView { background:#202125; alternate-background-color:#26272C;
 color:#E8E6EA; border:1px solid #45464F; selection-background-color:#543044;
 selection-color:#FFFFFF; gridline-color:#383940; }
QAbstractItemView::item { padding:5px; }
QHeaderView::section { background:#292A2F; color:#BDBBC4; border:0;
 border-bottom:1px solid #45464F; padding:8px; }
QTabWidget::pane { background:#191A1D; border:0; border-top:1px solid #383940; }
QTabBar::tab { background:transparent; color:#BDBBC4; border:0;
 border-bottom:2px solid transparent; padding:10px 12px; }
QTabBar::tab:selected { color:#FFFFFF; border-bottom:2px solid #FF175D; }
QTabBar::tab:hover { background:#292A2F; }
QCheckBox, QRadioButton { spacing:8px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #747681; border-radius:3px; background:#202125; }
QCheckBox::indicator:checked { background:#FF175D; border:3px solid #F4C2D4; }
QCheckBox::indicator:disabled { border-color:#45464F; background:#34353C; }
QRadioButton::indicator { width:14px; height:14px; border-radius:8px; border:1px solid #747681; background:#202125; }
QRadioButton::indicator:checked { background:#FF175D; border:3px solid #F4C2D4; }
QSlider::groove:horizontal { background:#45464F; height:4px; border-radius:2px; }
QSlider::handle:horizontal { background:#E8E6EA; width:12px; margin:-5px 0; border-radius:5px; }
QSlider::sub-page:horizontal { background:#FF175D; }
QProgressBar { border:1px solid #45464F; background:#202125; color:#E8E6EA; text-align:center; border-radius:3px; }
QProgressBar::chunk { background:#FF175D; }
QScrollBar:vertical { background:transparent; width:6px; margin:6px 8px 6px 12px; border-radius:3px; }
QScrollBar::handle:vertical { background:#F56B70; min-height:16px; border-radius:3px; }
QScrollBar::handle:vertical:hover { background:#FF7D94; }
QScrollBar::handle:vertical:pressed { background:#FF98A9; }
QScrollBar:horizontal { background:transparent; height:6px; margin:12px 6px 8px 6px; border-radius:3px; }
QScrollBar::handle:horizontal { background:#F56B70; min-width:16px; border-radius:3px; }
QScrollBar::handle:horizontal:hover { background:#FF7D94; }
QScrollBar::handle:horizontal:pressed { background:#FF98A9; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
QGroupBox { border:1px solid #383940; border-radius:4px; margin-top:12px; padding:12px; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 4px; }
QSplitter::handle { background:#383940; }
"""

MAIN = BASE + """
#Root, #BodyScroll, #ChatScroll, #ChatContent { background:transparent; border:0; }
#Brand { font: bold 25px 'Bahnschrift'; color:#F3F1F4; }
#SubBrand, #Micro, #Footer { color:#AAA8B3; font:11px 'Segoe UI'; letter-spacing:0; }
#StatusBadge { color:#8DD5AB; background:transparent; border:0; padding:8px; }
#PinkRule { background:#383940; border:0; }
#HoloPanel { background:transparent; border:0; border-right:1px solid #383940; }
#ChatPanel { background:transparent; border:0; }
#HoloTitle { color:#E8E6EA; font:bold 17px 'Bahnschrift'; }
#State { color:#BDBBC4; background:transparent; padding:8px 0; }
#Section { color:#F3F1F4; font:bold 19px 'Segoe UI'; border:0; padding:4px 0; }
QPushButton[kind='primary'] { color:#FFFFFF; background:#B52B5C; border:1px solid #E45384; }
QPushButton[kind='primary']:hover { background:#CB356B; }
QPushButton[kind='cyan'], QPushButton[kind='pink'], QPushButton[kind='flat'] {
 background:#292A2F; border:1px solid #45464F; color:#E8E6EA; }
QPushButton[kind='mini'] { min-width:24px; max-width:70px; min-height:30px; padding:0 8px; }
QPushButton#OutlineOptions { min-width:29px; min-height:29px; padding:0; }
#QuickBar { background:#202125; border:0; border-radius:4px; }
#QuickLabel { color:#AAA8B3; font:11px 'Segoe UI'; }
#SettingsPanel, #SettingsContents, #SettingsScroll, #SettingsCategoryScroll,
#SettingsCategoryTabs, QScrollArea#SettingsCategoryScroll > QWidget { background:#191A1D; border:0; }
#SettingsPanel QLabel { color:#D8D6DE; font:12px 'Segoe UI'; }
#SettingsPanel QLabel#Micro { color:#AAA8B3; font:11px 'Segoe UI'; }
#SettingsPanel QLabel#SettingsHeading { color:#F3F1F4; font:bold 19px 'Segoe UI'; padding:8px 4px; }
#SettingsPanel QLabel#LocalBadge { color:#8DD5AB; background:#202B25; padding:8px; border-radius:4px; }
#SettingsPanel QPushButton { min-height:22px; }
#SettingsPanel QLineEdit, #SettingsPanel QComboBox { min-height:20px; }
#ProgressPanel { background:#202125; border:1px solid #383940; border-radius:4px; }
#ProgressTitle { color:#E8E6EA; font:bold 11px 'Segoe UI'; }
#ProgressHint, #ProgressElapsed { color:#AAA8B3; font:11px 'Segoe UI'; }
"""


def _color(match):
    value = match.group(0)
    color = QColor(value)
    if not color.isValid():
        return value
    r, g, b, _ = color.getRgb()
    light = max(r, g, b)
    if r > 180 and r > g * 1.35:
        return '#FF175D' if b > 45 else '#F07379'
    if light < 65:
        return '#202125'
    if light < 145:
        return '#45464F'
    if light < 210:
        return '#AAA8B3'
    return '#E8E6EA'


def modernize(source):
    """Recolor legacy local rules without changing their geometry or behavior."""
    result = re.sub(r'#[0-9a-fA-F]{6}\b', _color, source)
    result = re.sub(r'rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*(\d+)\s*\)',
                    lambda m: 'rgba(32,33,37,' + m[1] + ')', result)
    result = re.sub(r"(?:'Consolas'|\bConsolas\b)", "'Segoe UI'", result)
    result = re.sub(r'letter-spacing\s*:\s*\d+px', 'letter-spacing:0px', result)
    return result


def _rendered_style(widget, source):
    name = widget.objectName()
    if name == 'ChatBody':
        text_color = '#D5E65F' if selected_theme() == 'silverhand' else '#E8E6EA'
        return "font:14px 'Segoe UI'; color:" + text_color + "; background:transparent;"
    if name == 'ChatAuthor':
        if selected_theme() == 'silverhand':
            color = '#77B4FF' if widget.property('speaker')=='ai' else '#DBE865'
        else:
            color = '#FF175D' if widget.property('speaker')=='ai' else '#AAA8B3'
        return "font:bold 11px 'Segoe UI'; color:" + color + "; background:transparent;"
    if widget.__class__.__name__ in ('VoiceManager', 'Studio'):
        return BASE + TOOL_STYLE
    result = modernize(source)
    if name == 'MiniShell':
        result += MINI_STYLE
    return result


def apply_style(widget, source):
    widget.setProperty('_capri_alpha_style', source)
    # Main-window style already contains a complete theme, including anger colors.
    if widget.property('_capri_main_style'):
        widget.setStyleSheet(source)
    else:
        widget.setStyleSheet(rendered_style(widget, source) if is_modern() else source)


def install_theme(app, theme=None):
    if not hasattr(app, '_capri_original_palette'):
        app._capri_original_palette = QPalette(app.palette())
        app._capri_original_stylesheet = app.styleSheet()
    theme = theme if theme in THEMES else 'holocall'
    app.setProperty('capri_theme', theme)
    palette = QPalette(app._capri_original_palette)
    if theme in ('capri', 'holocall', 'silverhand'):
        for role, color in ((QPalette.Window, '#191A1D'), (QPalette.WindowText, '#E8E6EA'),
                            (QPalette.Base, '#202125'), (QPalette.AlternateBase, '#292A2F'),
                            (QPalette.Text, '#E8E6EA'), (QPalette.Button, '#292A2F'),
                            (QPalette.ButtonText, '#E8E6EA'), (QPalette.Highlight, '#74324F'),
                            (QPalette.HighlightedText, '#FFFFFF')):
            palette.setColor(role, QColor(color))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor('#92939D'))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor('#92939D'))
    if theme == 'silverhand':
        for role, color in ((QPalette.Window, '#080F1E'), (QPalette.WindowText, '#DCE6FF'),
                            (QPalette.Base, '#101D35'), (QPalette.AlternateBase, '#172945'),
                            (QPalette.Text, '#DCE6FF'), (QPalette.Button, '#172945'),
                            (QPalette.ButtonText, '#DCE6FF'), (QPalette.Highlight, '#3865C1'),
                            (QPalette.HighlightedText, '#FFFFFF')):
            palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(holo_style(BASE) if theme in ('holocall', 'silverhand') else BASE if theme == 'capri' else app._capri_original_stylesheet)
    for widget in app.allWidgets():
        original = widget.property('_capri_alpha_style')
        if original is not None and not widget.property('_capri_main_style'):
            widget.setStyleSheet(rendered_style(widget, original) if theme in ('capri', 'holocall', 'silverhand') else original)
        widget.update()

# Layout-specific hierarchy, shared by main, settings and auxiliary windows.
DESIGN = """
QWidget { font-size:14px; }
#DesignHeader { border-bottom:1px solid #383940; }
#DesignBrand { color:#F5F3F6; font-size:38px; font-weight:800; }
QPushButton#DesignNav { background:transparent; border:0; border-radius:0;
 border-bottom:3px solid transparent; padding:17px 10px; font-size:16px; color:#AAA8B3; }
QPushButton#DesignNav:checked { border-bottom-color:#FF175D; color:#F5F3F6; }
QPushButton#DesignNav:hover { color:white; }
QPushButton#DesignWindowControl { background:transparent; border:0; padding:3px;
 min-width:26px; font-size:25px; color:#D8D6DE; }
#DesignFooter { border-top:1px solid #383940; }
#DesignMuted, #ChatTimestamp { color:#96949F; font-size:12px; }
#DesignStatus { color:#87D6A8; font-size:12px; }
#HoloPanel { border:0; border-right:1px solid #383940; }
#HoloTitle { font:bold 38px 'Bahnschrift'; color:#F5F3F6; }
#State { font:13px 'Segoe UI'; color:#87D6A8; padding:0; }
#Section { font:bold 25px 'Segoe UI'; color:#F5F3F6; padding:0; }
QPushButton#DesignClear { color:#AAA8B3; background:transparent; border:0; font-size:12px; }
QPushButton[design_control='true'] { background:transparent; border:0;
 border-top:1px solid #383940; border-radius:0; padding:2px; font:12px 'Segoe UI'; }
QPushButton[design_control='true']:hover { background:#292A2F; color:white; }
#ChatPanel QLineEdit { background:#202125; border:1px solid #45464F; font-size:16px; padding:0 16px; }
#ChatPanel QPushButton[kind='primary'] { background:#292A2F; border:1px solid #45464F; border-radius:4px; }
#SettingsPanel { padding:14px 28px; }
#SettingsPanel QLabel#SettingsHeading { font:bold 28px 'Segoe UI'; padding:10px 0 0 0; }
#SettingsPanel QLabel { font:13px 'Segoe UI'; }
#SettingsPanel QLabel#DesignMuted { color:#96949F; font:12px 'Segoe UI'; padding:0 0 12px 0; }
#SettingsPanel QLineEdit, #SettingsPanel QComboBox { padding:8px 10px; font:14px 'Segoe UI'; }
#SettingsPanel QPushButton { font:12px 'Segoe UI'; padding:8px 10px; }
#SettingsPanel QPushButton#DesignCategory { text-align:left; padding:12px 10px;
 border:0; border-left:3px solid transparent; border-radius:0; color:#AAA8B3; background:transparent; font-size:14px; }
#SettingsPanel QPushButton#DesignCategory:checked { color:#F5F3F6; border-left-color:#FF175D; background:#242125; }
#SettingsPanel QTabWidget::pane { border:0; }
QLabel#ToolTitle { font:bold 30px 'Segoe UI'; color:#F5F3F6; padding:0 0 8px 0; }
QLabel#ToolDescription { font:14px 'Segoe UI'; color:#AAA8B3; padding:0 0 18px 0; }
"""
MAIN += DESIGN
BASE += """
QLabel#ToolTitle { font:bold 30px 'Segoe UI'; color:#F5F3F6; padding:0 0 8px 0; }
QLabel#ToolDescription { font:14px 'Segoe UI'; color:#AAA8B3; padding:0 0 14px 0; }
"""

TOOL_STYLE = """
QWidget { font:14px 'Segoe UI'; }
QLabel#Title, QLabel#ToolTitle { font:bold 30px 'Segoe UI'; color:#F5F3F6; }
QLabel#ToolDescription { color:#AAA8B3; font:14px 'Segoe UI'; }
QFrame#Panel { border:0; border-right:1px solid #383940; padding:8px; }
QPushButton { min-height:24px; padding:8px 12px; }
QPushButton[kind='primary'] { background:#B52B5C; color:white; border-color:#D94C7C; }
QTableWidget { gridline-color:#292A2F; border:0; }
QHeaderView::section { font:12px 'Segoe UI'; padding:12px 8px; }
QTabBar::tab { font-size:16px; padding:14px 24px; }
"""
MINI_STYLE = """
#MiniShell { background:transparent; border:0; border-radius:6px; }
#MiniTitle { font:bold 24px 'Bahnschrift'; color:#F5F3F6; }
#MiniState { font:12px 'Segoe UI'; color:#87D6A8; padding:8px 0; }
#MiniSpeech { background:transparent; border:0; border-top:1px solid #383940;
 border-radius:0; font:16px 'Segoe UI'; padding:14px 0; color:#E8E6EA; }
#MiniShell QPushButton { background:transparent; border:0; color:#E8E6EA; font:12px 'Segoe UI'; padding:5px; }
#MiniShell #MiniMicButton, #MiniShell #MiniChatButton, #MiniShell #MiniHideButton,
#MiniShell QPushButton#MiniSettingsButton, #MiniShell QPushButton#MiniExpandButton { background:transparent; border:0; color:#E8E6EA; }
#MiniShell QPushButton:hover, #MiniShell #MiniChatButton:checked { background:#35363D; }
"""


HOLO_RULES = """
QWidget { font-family:'Bahnschrift','Segoe UI'; }
QPushButton, QToolButton, QLineEdit, QComboBox, QGroupBox { border-radius:0; }
#DesignBrand, #HoloTitle, #MiniTitle { color:#F56B70; }
#DesignHeader, #DesignFooter { border-color:#913C43; }
#DesignStatus, #State, #MiniState { color:#82DCD5; }
#MiniShell { border:0; border-radius:0; }
#MiniTitle { font:bold 17px 'Bahnschrift'; }
#DesignNav:checked { color:#F56B70; border-bottom-color:#F56B70; }
#HoloPanel { border-right:1px solid #913C43; }
#ChatPanel QLineEdit { border:1px solid #913C43; border-radius:0; }
#SettingsPanel QPushButton#DesignCategory:checked { border-left-color:#F56B70; }

QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background:#82DCD5; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background:#9FF2EC; }
QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed { background:#B7FFFA; }
"""


def is_holocall():
    return selected_theme() in ('holocall', 'silverhand')


def holo_style(style):
    if '{' not in style:
        style = '* {' + style + '}'
    colors = {'#191A1D':'#08181B', '#202125':'#0D2328', '#292A2F':'#153036',
              '#383940':'#39565C', '#45464F':'#4C686D', '#FF175D':'#F56B70',
              '#B52B5C':'#863C44', '#74324F':'#61383E', '#543044':'#61383E',
              '#87D6A8':'#82DCD5', '#E8E6EA':'#BDE6E2', '#AAA8B3':'#87AEAD'}
    for old,new in colors.items():style=style.replace(old,new)
    style += HOLO_RULES
    return silverhand_style(style) if selected_theme() == 'silverhand' else style


def bubble_style(speaker: str, theme: str) -> str:
    """Theme-specific readable speech bubbles; Alpha retains its original style."""
    palettes = {
        'capri': {
            'ai': ('rgba(46,32,48,235)', '#87546C', '#DF5F94'),
            'user': ('rgba(28,41,58,238)', '#51799F', '#7EA7D7'),
            'system': ('rgba(34,37,43,235)', '#65707B', '#AAB6C5'),
        },
        'holocall': {
            'ai': ('rgba(34,24,38,240)', '#A45361', '#F17B8D'),
            'user': ('rgba(18,42,47,241)', '#50888E', '#8BD4DD'),
            'system': ('rgba(22,35,39,238)', '#52757D', '#88ABB4'),
        },
        'silverhand': {
            'ai': ('rgba(13,26,48,239)', '#5277B8', '#7BAEFF'),
            'user': ('rgba(21,42,74,241)', '#76A1E7', '#D3E65E'),
            'system': ('rgba(19,32,51,240)', '#6C7849', '#D4DF65'),
        },
    }
    bg, border, accent = palettes.get(theme, palettes['capri']).get(speaker, palettes.get(theme, palettes['capri'])['system'])
    return ('QFrame#Bubble { background-color:' + bg + '; border:1px solid ' + border +
            '; border-left:2px solid ' + accent + '; border-radius:' +
            ('2px' if theme == 'silverhand' else '6px') + '; }')


def rendered_style(widget, source):
    if widget.objectName() == 'Bubble':
        return bubble_style(widget.property('speaker') or 'system', selected_theme())
    style = _rendered_style(widget, source)
    return holo_style(style) if is_holocall() else style


# Silverhand's in-game HUD palette: near-black olive surfaces, yellow-green
# information and restrained electric blue for selections. No game assets/fonts.
# This palette is intentionally independent of Holocall's pink/cyan identity.
SILVERHAND_COLORS = {
    # Saturated Johnny-style cobalt selection, electric-blue labels and navy.
    # Muted yellow/olive survives only as a small secondary HUD accent.
    '#F4C2D4': '#CAD9FF', '#242125': '#0E192D',
    '#E45384': '#7DA7FF', '#D94C7C': '#6F9DFB',
    '#F56B70': '#82A9FF', '#C9515D': '#5279D9',
    '#913C43': '#3D62AE', '#863C44': '#233B70', '#61383E': '#1B305D',
    '#08181B': '#080F1E', '#0D2328': '#101D35', '#153036': '#172945',
    '#39565C': '#294B85', '#4C686D': '#3A5F9C',
    '#82DCD5': '#75A0FF', '#BDE6E2': '#DCE6FF', '#87AEAD': '#A9BFEA',
    '#8FB6C0': '#91B4EF', '#75DCE9': '#7DA7FF',
    '#C5EAF0': '#EDF3FF', '#3C6069': '#375F9E',
    '#F3D34A': '#C9D178', '#B39C35': '#A5AE65',
    '#85752F': '#58633A', '#615521': '#38412A', '#4D4828': '#283023',
    '#10191C': '#080F1E', '#14272C': '#101D35', '#1C343B': '#172945',
}

SILVERHAND_RULES = """
/* Silverhand: charcoal/navy glass, bright HUD blue controls, acid-yellow data.
   Deliberately thin lines and square facets like the supplied game captures. */
QWidget { font-family:'Bahnschrift','Segoe UI'; }
#Root, #ChatContent, #ChatScroll, #BodyScroll { background:transparent; }
QMainWindow, QDialog, QMessageBox, #SettingsPanel { background:#080D1C; }
#DesignHeader { background:#0C1525; border-top:1px solid #D0E555; border-bottom:1px solid #4969AF; }
#DesignFooter { background:#0A1121; border-top:1px solid #768842; }
#DesignNav { color:#94B6FF; font-size:15px; border-radius:0; }
#DesignNav:checked { background:#172E55; color:#DBEE69; border-bottom:2px solid #6B9DFF; }
#DesignNav:hover, #DesignWindowControl:hover { background:#1A3766; color:#B4D2FF; }
#DesignStatus, #State, #MiniState { color:#D3E55B; }
#DesignMuted, #ChatTimestamp, #QuickLabel { color:#86A9E9; }
#HoloPanel { border-right:1px solid #5974B6; background:#0C1628; }
#ChatPanel { background:#0A1425; border:0; }
#ChatPanel QLineEdit { background:#101E35; border:1px solid #577FC4; color:#E1E9FF; }
#ChatPanel QLineEdit:focus { border-color:#B5D5FF; }
#Section, #HoloTitle, #MiniTitle, #SettingsPanel QLabel#SettingsHeading { color:#D5E65F; }
QPushButton, QToolButton, QLineEdit, QComboBox, QGroupBox { border-radius:0; }
QPushButton { background:#10213C; border:1px solid #3E65A8; color:#9DBEFF; }
QPushButton:hover { background:#1D3D70; border-color:#77A9FF; color:#FFFFFF; }
QPushButton:checked, QPushButton:pressed { background:#254F8C; color:#EAF2FF; border-color:#D7E95F; }
QPushButton#DesignCategory:checked, #SettingsPanel QPushButton#DesignCategory:checked {
 background:#19365E; color:#E0EE6F; border-left:2px solid #78A7FF; }
#SettingsPanel QLabel { color:#D5E65F; }
#SettingsPanel QLabel#Micro, #ProgressHint { color:#B9C96B; }
#SettingsPanel QLineEdit, #SettingsPanel QComboBox { background:#101E35; border:1px solid #365B99; }
#SettingsPanel QLineEdit:focus, #SettingsPanel QComboBox:focus { border-color:#7AA9FB; }
#MiniShell { background:#080D1C; border:1px solid #5273B2; border-top:1px solid #D1E454; border-radius:0; }
#MiniSpeech { background:#101C32; border-top:1px solid #496DAA; color:#C5DDFF; }
#MiniHistory { background:#0D182A; border:1px solid #466AA8; color:#E9F0FF; }
#MiniShell QPushButton:hover, #MiniShell #MiniChatButton:checked { background:#204779; color:#EDF4FF; }
#MiniShell #MiniChatButton, #MiniShell #MiniSendButton, #MiniShell #MiniExpandButton {
 background:#193B70; color:#D1E6FF; border:1px solid #75A9FA; border-radius:0; }
#MiniShell #MiniMicButton { border:1px solid #36DDA0; }
#MiniShell #MiniMicButton:hover { background:#155845; }
#ProgressPanel { background:#0D182A; border:1px solid #466AA8; }
#ProgressTitle { color:#D8E965; }
#ChatAuthor { color:#79AEFF; }
#ChatPanel QPushButton[kind='primary'], QPushButton[kind='primary'] {
 background:#1B4379; border:1px solid #76A9FF; color:#E5EEFF; }
#ChatPanel QPushButton[kind='primary']:hover, QPushButton[kind='primary']:hover {
 background:#336ABC; border-color:#B2D0FF; }
QProgressBar::chunk { background:#548EF0; }
QSlider::sub-page:horizontal { background:#5F91F0; }
QTabBar::tab:selected { color:#D6E763; border-bottom:2px solid #619BFF; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked { background:#5687DA; border-color:#BDDBFF; }
QAbstractItemView::item:selected, QMenu::item:selected { background:#254E85; color:#DFF1FF; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background:#D5E65F; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background:#E4F173; }
QScrollBar::handle:vertical:pressed, QScrollBar::handle:horizontal:pressed { background:#B4C252; }
"""


def silverhand_style(style):
    # All matched replacements are performed in one pass: cascading replacements
    # would otherwise turn the desired blue selection back into an older hue.
    import re
    tokens = re.compile('|'.join(re.escape(key) for key in sorted(SILVERHAND_COLORS, key=len, reverse=True)), re.I)
    colors = {key.upper(): value for key, value in SILVERHAND_COLORS.items()}
    result = tokens.sub(lambda match: colors[match.group(0).upper()], style)
    return result + SILVERHAND_RULES


def hud_author(speaker, original):
    """Presentation only: never rename the actual LLM persona or stored memory."""
    return 'LINK' if selected_theme() == 'silverhand' and speaker == 'ai' else original


def hud_chrome(text):
    """Keep the Silverhand HUD free of Capri branding, not chat message text."""
    if selected_theme() != 'silverhand':
        return text
    conversions = (
        ('Capri online. Możemy pogadać.', 'Połączenie aktywne. Możemy rozmawiać.'),
        ('Capri online. Ready when you are.', 'Link active. Ready when you are.'),
        ('Capri online.', 'Połączenie aktywne.'),
        ('HEJ CAPRI', 'FRAZA WYBUDZAJĄCA'),
        ('Hej Capri', 'Fraza wybudzająca'),
        ('CAPRI • PULPIT', 'NAKŁADKA • PULPIT'),
        ('CAPRI • ZACHOWANIE', 'ZACHOWANIE SYSTEMU'),
        ('PAMIĘĆ CAPRI', 'PAMIĘĆ SYSTEMU'),
        ('CHARAKTER CAPRI', 'CHARAKTER ROZMOWY'),
        ('EKSPRESJA CAPRI', 'EKSPRESJA GŁOSU'),
        ('Capri zna Cię jako:', 'Nazwa profilu:'),
    )
    for original, replacement in conversions:
        text = text.replace(original, replacement)
    return re.sub(r'(?i)\bcapri\b', lambda match: 'SYSTEM' if match.group().isupper() else 'system', text)
