"""Layout implementation for Basic; original widget tree retained for Alpha."""
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
                              QHBoxLayout, QBoxLayout, QLayout, QSizePolicy, QAbstractButton, QGroupBox)
from capri_theme import is_modern, is_holocall, selected_theme, hud_author, hud_chrome


def icon(name):
    pix = QPixmap(28, 28); pix.fill(Qt.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor('#9FC1FF' if selected_theme() == 'silverhand' else '#E8E6EA'), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if name == 'mic':
        p.drawRoundedRect(QRectF(10, 3, 8, 14), 4, 4)
        p.drawArc(QRectF(6, 7, 16, 15), 180*16, 180*16)
        p.drawLine(14,22,14,26);p.drawLine(9,26,19,26)
    elif name == 'voice':
        p.drawLine(4,11,8,11);p.drawLine(8,11,13,6);p.drawLine(13,6,13,22)
        p.drawLine(13,22,8,17);p.drawLine(8,17,4,17);p.drawLine(4,17,4,11)
        p.drawArc(QRectF(12,8,9,12),-75*16,150*16)
        p.drawArc(QRectF(11,3,16,22),-65*16,130*16)
    elif name == 'say':
        for x,y in ((6,9),(14,15),(22,7)):
            p.drawLine(x,3,x,25);p.setBrush(QColor('#191A1D'));p.drawEllipse(QRectF(x-3,y,6,6))
    elif name == 'chat':
        p.drawRoundedRect(QRectF(3,5,22,16),2,2);p.drawLine(8,21,5,25)
    elif name == 'expand':
        for x,y,a,b in ((4,4,1,1),(24,4,-1,1),(4,24,1,-1),(24,24,-1,-1)):
            p.drawLine(x,y,x+a*6,y);p.drawLine(x,y,x,y+b*6)
    elif name == 'send':
        p.drawLine(4,14,23,14);p.drawLine(16,7,23,14);p.drawLine(16,21,23,14)
    p.end();return QIcon(pix)


def label(text, name):
    w=QLabel(text);w.setObjectName(name);return w


class CapriDesign:
    def __init__(self, w):
        self.w=w; self.modern=None
        self.header=QWidget();self.header.setObjectName('DesignHeader')
        bar=QHBoxLayout(self.header);bar.setContentsMargins(28,10,22,10);bar.setSpacing(20)
        brand=label('CAPRI','DesignBrand');self.brand=brand;f=QFont('Bahnschrift',30,QFont.Bold);f.setStretch(68);brand.setFont(f)
        # No duplicate logo in the upper-left corner. Navigation occupies this space.
        brand.hide()
        self.nav=[]
        for title,index in [('Rozmowa',-1),('Głos',self.index_for('Głos')),('Mózg',self.index_for('Mózg')),('Ustawienia',0)]:
            b=QPushButton(title);b.setObjectName('DesignNav');b.setCheckable(True)
            b.clicked.connect(lambda checked=False,i=index:self.navigate(i));bar.addWidget(b);self.nav.append(b)
        bar.addStretch()
        for text,tip,action in [('↗','Przełącz na nakładkę',lambda:w.resize_overlay(True)),('−','Ukryj',w.hide),('×','Zamknij',w.quit_app)]:
            b=QPushButton(text);b.setObjectName('DesignWindowControl');b.setToolTip(tip);b.clicked.connect(action);bar.addWidget(b)
        w.central.layout().insertWidget(0,self.header)
        self.footer=QWidget();self.footer.setObjectName('DesignFooter')
        foot=QHBoxLayout(self.footer);foot.setContentsMargins(28,10,28,10)
        self.local=label('Tryb lokalny','DesignMuted');foot.addWidget(self.local);foot.addStretch()
        self.status=label('● Gotowa','DesignStatus');foot.addWidget(self.status)
        w.central.layout().addWidget(self.footer)
        self.controls=QWidget();self.controls.setObjectName('DesignControls')
        self.control_layout=QHBoxLayout(self.controls);self.control_layout.setContentsMargins(0,18,0,8);self.control_layout.setSpacing(8)
        self.agent=QWidget();agent=QHBoxLayout(self.agent);agent.setContentsMargins(0,4,0,0)
        self.agent_layout=agent
        self.chat_heading=QWidget();heading=QHBoxLayout(self.chat_heading);heading.setContentsMargins(0,0,0,18)
        self.clear=QPushButton('Wyczyść');self.clear.setObjectName('DesignClear');self.clear.clicked.connect(w.reset_conversation)
        heading.addWidget(w.dialog_label);heading.addStretch();heading.addWidget(self.clear)
        w.chat_right_layout.insertWidget(0,self.chat_heading)
        # Sidebar provides one consistent place for every settings category.
        self.settings_host=QWidget();self.settings_row=QHBoxLayout(self.settings_host)
        self.settings_row.setContentsMargins(0,0,0,0);self.settings_row.setSpacing(26)
        self.sidebar=QWidget();self.sidebar.setFixedWidth(180);side=QVBoxLayout(self.sidebar)
        side.setContentsMargins(0,8,16,0);side.setSpacing(5)
        self.categories=[]
        for i in range(w.settings_tabs.count()):
            b=QPushButton('Wydajność / testy' if w.settings_tabs.tabText(i)=='Wydajność • eksperymentalne' else w.settings_tabs.tabText(i));b.setObjectName('DesignCategory');b.setCheckable(True)
            b.clicked.connect(lambda checked=False,n=i:w.settings_tabs.setCurrentIndex(n));side.addWidget(b);self.categories.append(b)
        side.addStretch();self.settings_row.addWidget(self.sidebar)
        w.settings.layout().addWidget(self.settings_host,1)
        w.settings_tabs.currentChanged.connect(self.sync_navigation)
        self.help=label('Wybierz kategorię po lewej. Zmiany zapisują się automatycznie.','DesignMuted')
        w.settings.layout().insertWidget(1,self.help)
        self.mini_expand=QPushButton();self.mini_expand.setIcon(icon('expand'))
        self.mini_expand.setToolTip('Otwórz pełne okno');self.mini_expand.setAccessibleName('Otwórz pełne okno')
        self.mini_expand.clicked.connect(lambda:w.resize_overlay(False))
        self.mini_mute=QPushButton();self.mini_mute.setIcon(icon('voice'))
        self.mini_mute.setToolTip('Włącz lub wyłącz głos');self.mini_mute.setAccessibleName('Włącz lub wyłącz głos')
        self.mini_mute.clicked.connect(w.toggle_voice)
        w.mini_footer_layout.insertWidget(2,self.mini_expand,1)
        w.mini_footer_layout.insertWidget(3,self.mini_mute,1)
        self.set_theme()

    def style_mini(self):
        w=self.w;modern=is_modern()
        self.mini_expand.setVisible(modern);self.mini_mute.setVisible(modern)
        w.mini_btn_hide.setVisible(not modern)
        scale = max(0.8, min(1.5, int(w.cfg.get('mini_scale', 100)) / 100.0))
        for button,kind,title in ((w.mini_btn_mic,'mic','Mikrofon'),(w.mini_btn_chat,'chat','Pokaż rozmowę')):
            button.setIcon(icon(kind) if modern else QIcon())
            button.setIconSize(QSize(round(23*scale), round(23*scale)))
            button.setAccessibleName(title)
            button.setText('' if modern else
                           ('■ STOP' if w.recording else '● MÓW') if kind=='mic' else
                           ('CZAT ▲' if w.mini_chat_open else 'CZAT'))
        # Do not override scaled margins with unscaled theme constants.
        w._style_mini_controls()
        if modern:
            w.mini_title.setText('LINK' if selected_theme()=='silverhand' else 'CAPRI')
            w.mini_state.setText(self.status.text())

    def index_for(self,name):
        return self.w.settings_tabs.indexOf(self.w._settings_pages.get(name)) if name in self.w._settings_pages else 0

    def navigate(self,index):
        w=self.w
        if w.cfg.get('compact'):w.resize_overlay(False)
        if index == -1:
            if w.settings_visible:w.toggle_settings()
        else:
            if not w.settings_visible:w.toggle_settings(force_open=True)
            w.settings_tabs.setCurrentIndex(index)
        self.sync_navigation()

    def sync_navigation(self,*args):
        w=self.w
        current=w.settings_tabs.currentIndex()
        selected=0 if not w.settings_visible else 1 if w.settings_tabs.widget(current) is w._settings_pages.get('Głos') else 2 if w.settings_tabs.widget(current) is w._settings_pages.get('Mózg') else 3
        for i,b in enumerate(self.nav):b.setChecked(i==selected)
        for i,b in enumerate(self.categories):b.setChecked(i==current)
        if is_modern():
            title=w.settings_tabs.tabText(current)
            w.settings_header.setText(title)
            descriptions={'AI i rozmowa':'Model, język i styl rozmowy.',
                'Pamięć i profil':'Wspomnienia i sposób, w jaki Capri zwraca się do Ciebie.',
                'Wydajność • eksperymentalne':'Opcjonalne testy wydajności. Możesz przywrócić sprawdzoną konfigurację.',
                'Agent i pulpit':'Dostęp do komputera, internetu i aplikacji.',
                'Mikrofon':'Rozpoznawanie mowy i wybudzanie „Hej Capri”.',
                'Głos':'Brzmienie, próbki i ekspresja głosu.',
                'Wygląd':'Motyw, awatary i zachowanie nakładki.',
                'Silniki TTS':'Konfiguracja silników i akceleracji głosu.'}
            # English is a first-class locale: category help remains legible.
            if w.lang == 'en':
                english_help = {
                    'General': 'Language, version, licenses, and application files.',
                    'Brain': 'Model quality, provider, and API settings.',
                    'Personality & Memory': 'Capri’s personality and local memory.',
                    'Listening (STT)': 'Microphone, transcription, and wake phrase.',
                    'Voice': 'Voice synthesis, samples, and expression.',
                    'Appearance': 'Theme, avatars, and overlay behavior.',
                    'PC Agent & Desktop': 'Computer, internet, and application access.',
                    'Performance • Experimental': 'Optional performance features and safe defaults.',
                }
                self.help.setText(english_help.get(title, 'Configure this category.'))
            else:
                descriptions.update({
                    'Ogólne':'Język aplikacji, wersja i informacje prawne.',
                    'Mózg':'Profile modeli rozmowy, Ollama i zewnętrzne API.',
                    'Osobowość i pamięć':'Osobowość, wspomnienia i sposób zwracania się do Ciebie.',
                    'Nasłuch (STT)':'Mikrofon, rozpoznawanie mowy i fraza wybudzająca.',
                })
                self.help.setText(hud_chrome(descriptions.get(title,'')))


    def set_theme(self):
        w=self.w;modern=is_modern()
        if modern != self.modern:
            self.modern=modern
            left=w.left_panel.layout()
            for b in (w.btn_mic,w.btn_whisper,w.btn_voice):
                (self.control_layout if modern else w.chat_controls).addWidget(b)
                b.setMinimumWidth(0 if modern else 95)
                b.setMinimumHeight(62 if modern else 38)
                b.setProperty('design_control',modern)
                b.setIcon(icon('mic' if b==w.btn_mic else 'say' if b==w.btn_whisper else 'voice') if modern else QIcon())
                b.setIconSize(QSize(21,21))
            for b in (w.btn_agent,w.btn_agent_stop):
                (self.agent_layout if modern else w.chat_agentbar).addWidget(b)
                b.setMinimumWidth(0)
            if modern:
                left.addWidget(self.controls);left.addWidget(self.agent)
                self.settings_row.addWidget(w.settings_tabs,1)
            else:
                w.settings.layout().addWidget(w.settings_tabs,1)
            w.settings_tabs.show()
            for b in (w.btn_mic,w.btn_whisper,w.btn_voice,w.btn_agent): b.show()
            self.controls.setVisible(modern);self.agent.setVisible(modern)
            self.settings_host.setVisible(modern);self.help.setVisible(modern)
            w.settings_tabs.tabBar().setVisible(not modern)
            w.left_panel.setFixedWidth(328 if modern else 312)
            w.body_widget.setMinimumSize(900 if modern else 770,520 if modern else 540)
            w.chat_right_layout.setContentsMargins(30,24,30,24) if modern else w.chat_right_layout.setContentsMargins(14,13,14,13)
            w.chat_stack.setSpacing(9 if modern else 13)
            w.chat_stack.setContentsMargins(0,6,0,6) if modern else w.chat_stack.setContentsMargins(7,8,7,7)
            w.message.setMinimumHeight(54 if modern else 41)
            w.btn_send.setMinimumHeight(54 if modern else 38)
            w.btn_send.setFixedWidth(56 if modern else 90)
            w.btn_send.setIcon(icon('send') if modern else QIcon())
            w.btn_send.setAccessibleName('Wyślij wiadomość')
            w.btn_send.setText('' if modern else w.translate('send'))
            # Restore layout alignment for already displayed conversation rows.
            for row in w.chat_content.findChildren(QWidget,'BubbleRow'):self.chat_row(row)
            for i in range(w.settings_tabs.count()):
                page=w.settings_tabs.widget(i);grid=page.widget().layout()
                grid.setContentsMargins(4,14,22,24) if modern else grid.setContentsMargins(11,12,16,18)
                grid.setAlignment(Qt.AlignTop if modern else Qt.Alignment())
                grid.setVerticalSpacing(20 if modern else 11)
                grid.setHorizontalSpacing(24 if modern else 15)
                grid.setColumnMinimumWidth(0,180 if modern else 155)
        self.form_labels()
        self.reflow()
        self.sync_navigation()

    def form_labels(self):
        w=self.w
        names = {'l_gif':'Animacja podczas mówienia','l_tts_engine':'Silnik głosu',
                 'l_volume':'Głośność','l_phrase':'Tekst do wypowiedzenia',
                 'l_backend':'Silnik AI','l_local_model':'Model rozmowy',
                 'l_dialogue_mode':'Styl rozmowy','l_stt_model':'Model rozpoznawania mowy',
                 'l_lang':'Język','l_import_mode':'Import próbek',
                 'l_audio_cleanup':'Czyszczenie nagrań','l_voice_reference':'Próbka głosu'}
        for name,text in names.items():
            item=getattr(w,name,None)
            if item is None:continue
            if is_modern():
                if item.text() and item.text()!=text:
                    item.setProperty('_design_label',item.text())
                if w.lang=='pl':item.setText(text)
            # Alpha labels are restored by apply_language before this pass.

    def reflow(self):
        w=self.w;modern=is_modern();compact=w.cfg.get('compact',False)
        self.header.setVisible(modern and not compact);self.footer.setVisible(modern and not compact)
        w.header_widget.setVisible(not modern and not compact)
        w.top_rule.setVisible(not modern and not compact)
        w.footer.setVisible(not modern and not compact)
        w.btn_quick_toggle.setVisible(not modern and not compact)
        w.quick_bar.setVisible(not modern and not compact and w.cfg.get('quick_controls_expanded',False))
        self.chat_heading.layout().setContentsMargins(0,0,0,18 if modern else 0)
        w.agent_badge.setVisible(not modern)
        w.l_sub.setVisible(not modern)
        w.l_title.setVisible(not modern)
        self.clear.setVisible(modern)
        self.chat_heading.setVisible(True)
        if not compact:
            w.central.layout().setContentsMargins(0,0,0,0) if modern else w.central.layout().setContentsMargins(22,19,22,18)
            w.central.layout().setSpacing(0 if modern else 11)
            left=w.left_panel.layout()
            # Only move the shared avatar while it belongs to the full window.
            if not w._mini_avatar_parked:
                left.removeWidget(w.avatar);left.insertWidget(0 if modern else 2,w.avatar,0 if modern else 1)
            w.avatar.setMinimumSize(270,290 if modern else 326)
            w.avatar.setMaximumHeight(310 if modern else 16777215)
            left.setContentsMargins(26,24,26,18) if modern else left.setContentsMargins(17,16,17,15)
            if modern:
                for item in (w.l_title,w.l_state,w.wave,self.controls,self.agent):left.removeWidget(item)
                left.insertWidget(1,w.l_title);left.insertWidget(2,w.l_state);left.insertWidget(3,w.wave)
                left.addWidget(self.controls);left.addWidget(self.agent)
                left.setStretch(left.indexOf(w.wave),1)
            else:
                left.removeWidget(w.l_title);left.insertWidget(0,w.l_title)
                left.removeWidget(w.l_sub);left.insertWidget(1,w.l_sub)
                left.removeWidget(w.wave);left.insertWidget(3,w.wave)
                left.removeWidget(w.l_state);left.insertWidget(4,w.l_state)
        self.update_state()
        self.style_mini()
        # Icons are QPixmaps: unlike Qt stylesheet colors they need regeneration
        # when cycling Silverhand / Holocall / Basic in the same process.
        if modern:
            for button, glyph in ((w.btn_mic, 'mic'), (w.btn_whisper, 'say'),
                                  (w.btn_voice, 'voice'), (w.btn_send, 'send'),
                                  (w.mini_btn_mic, 'mic'), (w.mini_btn_chat, 'chat'),
                                  (self.mini_expand, 'expand'), (self.mini_mute, 'voice')):
                button.setIcon(icon(glyph))
        self.refresh_silverhand_chrome()

    def update_state(self):
        w=self.w
        if not is_modern():return
        is_en = w.lang == 'en'
        states = ({'standby':'Ready','online':'Ready','thinking':'Thinking…','synth':'Preparing voice…',
                   'playing':'Speaking…','record':'Listening…','transcribing':'Transcribing…','voice_prep':'Loading voice…'} if is_en else
                  {'standby':'Gotowa','online':'Gotowa','thinking':'Myślę…','synth':'Przygotowuję głos…',
                   'playing':'Mówię…','record':'Słucham…','transcribing':'Rozpoznaję mowę…','voice_prep':'Ładuję głos…'})
        self.status.setText('● '+states.get(w.ui_status,w.translate(w.ui_status)))
        mode = ('Local mode' if is_en else 'Tryb lokalny') if w.cfg.get('chat_provider')!='external' else ('External API' if is_en else 'Zewnętrzne API')
        prefix = {'holocall':'HOLOCALL / ', 'silverhand':'SILVERHAND / '}.get(selected_theme(),'')
        self.local.setText(prefix + mode)
        w.l_state.setText(self.status.text())
        w.btn_mic.setText('Stop' if w.recording else ('Microphone' if is_en else 'Mikrofon'))
        w.btn_whisper.setText('Say' if is_en else 'Powiedz')
        w.btn_voice.setText(('Voice' if is_en else 'Głos') if w.cfg.get('auto_voice') else ('Muted' if is_en else 'Wyciszony'))
        w.btn_voice.setToolTip(('Mute voice' if is_en else 'Wyłącz głos') if w.cfg.get('auto_voice') else ('Enable voice' if is_en else 'Włącz głos'))
        w.btn_agent.setText(('PC Agent: ' if is_en else 'Agent PC: ')+('auto' if w.agent_unattended else ('on' if is_en else 'wł.') if w.agent_enabled else ('off' if is_en else 'wył.')))
        w.btn_agent.setToolTip(w.agent_badge.text())
        w.btn_agent_stop.setText('Stop')
        w.btn_send.setText('')
        w.mini_title.setText('LINK' if selected_theme()=='silverhand' else 'CAPRI')
        w.mini_state.setText(self.status.text())

    def refresh_silverhand_chrome(self):
        """Refresh current widgets when switching themes without changing chat data."""
        w=self.w
        is_silver = selected_theme() == 'silverhand'
        self.brand.setText('')  # Neither CAPRI nor CONTACTS is a header label.
        self.brand.hide()
        w.mini_title.setText('LINK' if is_silver else 'CAPRI')
        w.message.setPlaceholderText(('Wprowadź wiadomość…' if w.lang=='pl' else 'Enter message…')
                                     if is_silver else w.translate('placeholder'))
        w.mini_input.setPlaceholderText(('Wiadomość…' if w.lang=='pl' else 'Message…')
                                        if is_silver else ('Napisz do Capri…' if w.lang=='pl' else 'Message to Capri…'))
        w.setWindowTitle('SILVERHAND // LINK' if is_silver else 'CAPRI // NEURAL LINK')
        if not w._mini_last_ai and w.mini_speech.text() in ('Capri online.', 'Połączenie aktywne.'):
            w.mini_speech.setText('Połączenie aktywne.' if is_silver else 'Capri online.')
        for body in w.chat_content.findChildren(QLabel, 'ChatBody'):
            original = body.property('_silverhand_startup_original')
            if original is not None:
                body.setText(hud_chrome(original) if is_silver else original)
        for author in w.chat_content.findChildren(QLabel, 'ChatAuthor'):
            who=author.property('speaker')
            if who == 'ai':
                author.setText(hud_author('ai',w.translate('ai')))
            elif who == 'user':
                author.setText(w.translate('you'))
        if hasattr(w, '_render_mini_history'):
            w._render_mini_history()
        # Labels and buttons in the settings pages must follow the same branding
        # policy. Store original strings for exact recovery on other themes.
        for widget in w.findChildren(QLabel) + w.findChildren(QAbstractButton) + w.findChildren(QGroupBox):
            if widget.objectName() in ('ChatAuthor', 'ChatBody', 'MiniSpeech') or widget is self.brand:
                continue
            text = widget.text() if hasattr(widget, 'text') else widget.title()
            previous = widget.property('_silverhand_chrome_original')
            if is_silver:
                if 'capri' in text.lower():
                    # The locale may have changed while Silverhand was active.
                    if previous is None or text != hud_chrome(previous):
                        previous = text
                        widget.setProperty('_silverhand_chrome_original', previous)
                if previous is not None and text != hud_chrome(previous):
                    if hasattr(widget, 'setText'):
                        widget.setText(hud_chrome(previous))
                    else:
                        widget.setTitle(hud_chrome(previous))
            elif previous is not None:
                if text == hud_chrome(previous):
                    if hasattr(widget, 'setText'):
                        widget.setText(previous)
                    else:
                        widget.setTitle(previous)
                widget.setProperty('_silverhand_chrome_original', None)
        # The theme selector keeps its canonical itemData, changing only UI text.
        default_idx = w.look_select.findData('capri')
        if default_idx >= 0:
            w.look_select.setItemText(default_idx, 'Domyślny' if is_silver else 'Basic')
        if w.settings_visible:
            self.sync_navigation()

    def chat_row(self,row):
        modern=is_modern();card=row.findChild(QFrame,'Bubble')
        if card is None:return
        lay=row.layout()
        while lay.count():lay.takeAt(0)
        if row.property('speaker')=='user':lay.addStretch(1)
        lay.addWidget(card,0)
        if row.property('speaker')!='user':lay.addStretch(1)
        card.setMaximumWidth(500 if modern else 470)
        for name in ('ChatBody', 'ChatAuthor'):
            text=card.findChild(QLabel,name)
            if text:text.setAlignment((Qt.AlignRight if row.property('speaker')=='user' else Qt.AlignLeft) | Qt.AlignTop)
        card.layout().setContentsMargins(11,6,11,7) if modern else card.layout().setContentsMargins(11,8,11,11)
        card.layout().setSpacing(2 if modern else 5)
        stamp=card.findChild(QLabel,'ChatTimestamp')
        if stamp:stamp.setVisible(modern)
        if modern:
            # A one-word message must never become a 500px-wide rectangle.
            # Measure actual rendered glyphs to respect Windows DPI/fonts.
            body=card.findChild(QLabel,'ChatBody')
            author=card.findChild(QLabel,'ChatAuthor')
            lines=(body.text().splitlines() or ['']) if body else ['']
            content_px=max((body.fontMetrics().horizontalAdvance(line) for line in lines),default=0) if body else 0
            header_px=(author.fontMetrics().horizontalAdvance(author.text()) if author else 0)
            stamp_px=(stamp.fontMetrics().horizontalAdvance(stamp.text()) + 15 if stamp else 0)
            viewport = self.w.chat_view.viewport().width() if hasattr(self.w, 'chat_view') else 530
            width=max(160, min(500, max(180, viewport-38), max(content_px+26, header_px+stamp_px+36)))
            # Do not exceed the viewport even if the text has one long word.
            width=min(width, max(160, viewport-38))
            card.setFixedWidth(width)
            if body:
                # Qt word-wrap height can be stale after changing a fixed bubble
                # width or theme. Reserve the measured height explicitly.
                inner_width=max(65, width-card.layout().contentsMargins().left()-card.layout().contentsMargins().right()-8)
                measured=body.fontMetrics().boundingRect(0,0,inner_width,100000,
                    Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextExpandTabs, body.text()).height()
                needed=max(body.fontMetrics().height(), measured+5)
                body.setMinimumHeight(needed)
                heading_height=max(author.fontMetrics().height() if author else 14,
                                   stamp.fontMetrics().height() if stamp else 14)
                card.setMinimumHeight(needed+heading_height+card.layout().contentsMargins().top()
                                      +card.layout().contentsMargins().bottom()+card.layout().spacing()+9)
                card.updateGeometry()
                row.updateGeometry()
        else:
            card.setMinimumWidth(0)
            card.setMaximumWidth(470)
