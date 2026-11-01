"""Non-verbal prosody hints only for Fish S2-Pro (never inserted into chat)."""
from __future__ import annotations
import re

# Fish supports open-ended English instructions in brackets. Restrict our own
# output to a small tested set, and never allow user-supplied [instructions]
# to bypass the classifier.
PAUSE = re.compile(r"(?<=[.!?…])\s+")


def _emotion(sentence: str, language: str) -> str | None:
    low = sentence.lower().strip()
    if not low:
        return None
    # No automatic whispering based on words such as "sekret" or "cicho".
    if re.search(r"\b(przykro|smutn|żałuj|tęskn|stracił|sorry|miss you|sad|regret)\w*", low):
        return '[sad]'
    if re.search(r"\b(wkurz|przestań|cholera|szlag|dość|idiot|angry|stop it|damn)\w*", low):
        return '[angry]'
    if re.search(r"\b(ha+|hehe|haha|ojej|no proszę|genialnie|jasne, że|och tak|well well|oh please|nice try)\b", low):
        return '[chuckle]'
    if re.search(r"\b(naprawdę|serio|co takiego|niemożliwe|jak to|really|what the|no way)\b", low) or (low.endswith('?') and low.startswith(('co?', 'what?'))):
        return '[surprised]'
    if '!' in sentence or re.search(r"\b(super|świetnie|hurra|wow|udało|fantastyczn|amazing|awesome|yes!)\w*", low):
        return '[excited]'
    if '…' in sentence or '...' in sentence:
        return '[low voice]'
    return None


def fish_emotional_text(text: str, language: str = 'pl', *,
                        intensity: int = 65, whisper: bool = False,
                        enabled: bool = True, forced_emotion: str | None = None) -> str:
    """Apply sparse, sentence-specific expressive cues without mangling Polish.

    The strength changes the tag budget, not Fish's hidden model parameters.
    Tags are non-deterministic hints; effects depend on voice reference and S2.
    """
    text = re.sub(r'\[[^\]\n]{1,80}\]', '', text).strip()
    if not text:
        return text
    if whisper:
        return '[whisper] ' + text
    # Explicit in-character emotional state wins over sentence keyword lookup.
    # The tag affects Fish only; never add it to the displayed dialogue.
    if forced_emotion == 'irritated':
        # Modest annoyance: one delivery cue rather than shouting every sentence.
        return '[angry] ' + text
    if forced_emotion == 'angry':
        # Reinforce the delivery at each new sentence. One tag at the start of
        # a long passage can be lost by neural models after the first phrase.
        # Tags remain private to the voice engine, never shown in chat.
        sentences = [part.strip() for part in PAUSE.split(text) if part.strip()]
        return ' '.join('[angry] ' + sentence for sentence in sentences)
    if not enabled or intensity <= 0:
        return text
    # Explicit cue from the conversation, applied once per utterance rather
    # than at each sentence. Only well-established Fish delivery hints.
    contextual_tags = {
        'flirty': '[chuckle]', 'bashful': '[chuckle]', 'smug': '[chuckle]',
        'playful': '[chuckle]', 'excited': '[excited]', 'sad': '[sad]',
        'surprised': '[surprised]', 'relieved': '[low voice]',
    }
    if forced_emotion in contextual_tags:
        return contextual_tags[forced_emotion] + ' ' + text
    intensity = min(100, max(0, int(intensity)))
    sentences = [part.strip() for part in PAUSE.split(text) if part.strip()]
    result = []
    last_tag = None
    for idx, sentence in enumerate(sentences):
        tag = _emotion(sentence, language)
        if intensity < 35 and tag not in ('[whisper]', '[sad]', '[angry]'):
            tag = None
        # Distinct emotions can switch between sentences; avoid incessant
        # re-tagging equivalent consecutive lines, which tends to exaggerate.
        if tag and tag != last_tag and (intensity >= 65 or idx == 0 or tag in ('[whisper]', '[sad]')):
            sentence = tag + ' ' + sentence
            last_tag = tag
        elif tag is None:
            last_tag = None
        result.append(sentence)
    return ' '.join(result)
