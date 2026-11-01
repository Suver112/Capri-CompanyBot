"""Lightweight continuity hints for ordinary roleplay. No canned replies or database writes."""
from __future__ import annotations
import re
import unicodedata


def _fold(text: str) -> str:
    v = unicodedata.normalize('NFKD', str(text).casefold().replace('ł','l'))
    return ''.join(c for c in v if not unicodedata.combining(c))


def continuity_note(history: list[dict], language: str = 'pl') -> str:
    """Return only process guidance, never fabricated conversation facts."""
    turns = [m for m in history[-14:] if m.get('role') in ('user','assistant')
             and isinstance(m.get('content'), str) and m['content'].strip()]
    if not turns or turns[-1]['role'] != 'user':
        return ''
    current = _fold(turns[-1]['content'])
    prior = turns[:-1]
    if not prior:
        return ''
    last_user = next((m['content'] for m in reversed(prior) if m['role']=='user'), '')
    last_bot = next((m['content'] for m in reversed(prior) if m['role']=='assistant'), '')
    offer_pattern = (r'(?:\b(?:chcesz|chcialabys|chcialbys|masz ochote|wanna|want to)\b.{0,60}\b(?:zart|dowcip|joke)\b|'
                     r'\b(?:mam|opowiem ci|mog[eę] ci opowiedziec|can i tell you)\b.{0,50}\b(?:zart|dowcip|joke)\b)')
    ask_joke = bool(re.search(offer_pattern, current))
    if ask_joke:
        if language == 'pl':
            return ('OTWARTY WĄTEK: użytkownik pyta, czy TY chcesz USŁYSZEĆ jego żart. '
                    'Odpowiedz na propozycję i pozwól mu opowiedzieć, nie opowiadaj własnego żartu.')
        return 'OPEN THREAD: User offers to TELL you a joke. React and let the user deliver it; do not tell your own joke.'
    prior_offer = bool(re.search(offer_pattern, _fold(last_user)))
    if prior_offer and last_bot:
        if language == 'pl':
            return ('KONTYNUACJA: poprzednio użytkownik zaproponował Ci żart. '
                    'Jego najnowsza wypowiedź może być treścią lub puentą tego żartu. '
                    'Reaguj na to, co naprawdę opowiada, nie proponuj ponownie własnego żartu.')
        return 'CONTINUATION: User previously offered a joke. Current message may be its setup or punchline; react rather than offering your own.'
    short = len(current.split()) <= 6 or current.strip(' !?.') in ('tak','nie','no','mhm','haha','xd','dlaczego','czemu','serio','dalej','a ty')
    if short:
        if language == 'pl':
            return ('CIĄG DALSZY: to krótka odpowiedź w rozpoczętej rozmowie. '
                    'Powiąż ją z poprzednią wypowiedzią Capri i wcześniejszą wypowiedzią użytkownika. '
                    'Nie interpretuj jej jako nowego, niezależnego zadania.')
        return 'FOLLOW-UP: Link the short utterance to the preceding exchange; do not start a fresh topic.'
    return ('ROZMOWA TRWA: trzymaj się rozpoczętego wątku i jego uczestników. '
            'Nie wymyślaj relacji ani wspomnień użytkownika.' if language == 'pl' else
            'ONGOING CONVERSATION: Keep continuity and real participants; do not invent shared memories.')
