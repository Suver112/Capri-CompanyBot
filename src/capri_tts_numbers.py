"""Offline number-to-words for Polish speech synthesis.

Used only for speech requests; displayed messages and reference transcripts
are never modified. Standard library only.
"""
from __future__ import annotations
import re

UNITS = 'zero jeden dwa trzy cztery pięć sześć siedem osiem dziewięć'.split()
TEENS = 'dziesięć jedenaście dwanaście trzynaście czternaście piętnaście szesnaście siedemnaście osiemnaście dziewiętnaście'.split()
TENS = ['', '', 'dwadzieścia', 'trzydzieści', 'czterdzieści', 'pięćdziesiąt', 'sześćdziesiąt', 'siedemdziesiąt', 'osiemdziesiąt', 'dziewięćdziesiąt']
HUNDREDS = ['', 'sto', 'dwieście', 'trzysta', 'czterysta', 'pięćset', 'sześćset', 'siedemset', 'osiemset', 'dziewięćset']
SCALES = [('', '', ''), ('tysiąc', 'tysiące', 'tysięcy'), ('milion', 'miliony', 'milionów'), ('miliard', 'miliardy', 'miliardów'), ('bilion', 'biliony', 'bilionów')]
MONTHS = ['', 'stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca', 'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia']
ORD_M = {1:'pierwszy',2:'drugi',3:'trzeci',4:'czwarty',5:'piąty',6:'szósty',7:'siódmy',8:'ósmy',9:'dziewiąty',10:'dziesiąty',11:'jedenasty',12:'dwunasty',13:'trzynasty',14:'czternasty',15:'piętnasty',16:'szesnasty',17:'siedemnasty',18:'osiemnasty',19:'dziewiętnasty',20:'dwudziesty',30:'trzydziesty',40:'czterdziesty',50:'pięćdziesiąty',60:'sześćdziesiąty',70:'siedemdziesiąty',80:'osiemdziesiąty',90:'dziewięćdziesiąty'}
ORD_M[30] = 'trzydziesty'


def pl_int(n: int) -> str:
    if n < 0:
        return 'minus ' + pl_int(-n)
    if n == 0:
        return 'zero'
    if n > 999_999_999_999_999:
        return ' '.join(UNITS[int(x)] for x in str(n))
    chunks = []
    group = 0
    while n:
        v = n % 1000
        if v:
            h, rem = divmod(v, 100)
            words = [HUNDREDS[h]] if h else []
            if rem >= 20:
                t, u = divmod(rem, 10)
                words.append(TENS[t])
                if u: words.append(UNITS[u])
            elif rem >= 10:
                words.append(TEENS[rem - 10])
            elif rem:
                words.append(UNITS[rem])
            if group:
                suffix = SCALES[group][0 if v == 1 else (1 if v % 10 in (2,3,4) and v % 100 not in (12,13,14) else 2)]
                if v == 1:
                    words = [suffix]
                else:
                    words.append(suffix)
            chunks.append(' '.join(words))
        n //= 1000
        group += 1
    return ' '.join(reversed(chunks))


def pl_ordinal(n: int, *, form: str = 'm') -> str:
    if n < 1 or n > 99:
        return pl_int(n)
    if n in ORD_M:
        words = [ORD_M[n]]
    else:
        tens, rest = divmod(n, 10)
        words = [ORD_M[tens * 10], ORD_M[rest]]
    def inflect(word: str) -> str:
        if word == 'drugi':
            return {'f':'druga', 'fg':'drugiej', 'n':'drugie', 'gen':'drugiego', 'loc':'drugim'}.get(form, word)
        if word == 'trzeci':
            return {'f':'trzecia', 'fg':'trzeciej', 'n':'trzecie', 'gen':'trzeciego', 'loc':'trzecim'}.get(form, word)
        if form == 'f':
            return word[:-1] + 'a'
        if form == 'fg':
            return word[:-1] + 'ej'
        if form == 'n':
            return word[:-1] + 'e'
        if form == 'gen':
            return word[:-1] + 'ego'
        if form == 'loc':
            return word[:-1] + 'ym'
        return word
    return ' '.join(inflect(w) for w in words)


def pl_year(n: int) -> str:
    # Common natural reading for dates from the last two millennia.
    if 2001 <= n <= 2099:
        return 'dwa tysiące ' + pl_ordinal(n - 2000, form='gen')
    if n == 2000:
        return 'dwutysięcznego'
    if 1901 <= n <= 1999:
        tail = n % 100
        return 'tysiąc dziewięćset ' + pl_ordinal(tail, form='gen')
    return pl_int(n)


def pl_year_loc(n: int) -> str:
    if 2001 <= n <= 2099:
        return 'dwa tysiące ' + pl_ordinal(n - 2000, form='loc')
    if n == 2000:
        return 'dwutysięcznym'
    if 1901 <= n <= 1999:
        return 'tysiąc dziewięćset ' + pl_ordinal(n - 1900, form='loc')
    return pl_int(n)


def plural(n: int, one: str, few: str, many: str) -> str:
    if n == 1: return one
    if n % 10 in (2,3,4) and n % 100 not in (12,13,14): return few
    return many


def pl_fraction(digits: str) -> str:
    # Pronounce each decimal digit separately; preserves leading zeros.
    return ' '.join(UNITS[int(d)] for d in digits)


def to_spoken_pl(text: str) -> str:
    if not re.search(r'\d', text): return text
    # Mask technical multi-dot sequences before converting simple numbers.
    protected: list[str] = []
    def mask(val: str) -> str:
        k = len(protected)
        protected.append(val)
        return f'ZZZCAPRINUM{k}ZZZ'

    def iso_date(m):
        year, month, day = map(int, m.groups())
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f'{pl_ordinal(day, form="gen")} {MONTHS[month]} {pl_year(year)} roku'
        return m.group()
    text = re.sub(r'(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)', iso_date, text)

    def date(m):
        day, month, year = map(int, m.groups())
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f'{pl_ordinal(day, form="gen")} {MONTHS[month]} {pl_year(year)} roku'
        return m.group()
    text = re.sub(r'(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)', date, text)
    # A spoken year needs locative form after 'w ... roku'.
    text = re.sub(r'\b(w|we)\s+(19\d\d|20\d\d)\s+(roku|r\.)',
                  lambda m: m.group(1) + ' ' + pl_year_loc(int(m.group(2))) + ' ' + m.group(3),
                  text, flags=re.IGNORECASE)

    def clock(m):
        at = m.group(1) or ''
        hour, minute = int(m.group(2)), int(m.group(3))
        sec = m.group(4)
        if hour > 23 or minute > 59: return m.group()
        hour_word = pl_ordinal(hour, form='fg' if at else 'f') if hour else ('zerowej' if at else 'zerowa')
        mins = ('zero ' + pl_int(minute)) if minute < 10 else pl_int(minute)
        suffix = (f' {pl_int(int(sec))} sekund' if sec else '')
        return f'{at}{hour_word} {mins}{suffix}'
    text = re.sub(r'(?<!\w)(o\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?(?!\d)', clock, text, flags=re.IGNORECASE)

    def currency(m):
        n = int(m.group(1).replace(' ', '').replace('\u00a0', '').replace('.', ''))
        decimals = m.group(2)
        unit = m.group(3).lower()
        if unit in ('zł','pln'):
            if decimals and int(decimals) != 0:
                main = f'{pl_int(n)} {plural(n, "złoty", "złote", "złotych")}' if n else ''
                grosz = int(decimals.ljust(2, '0'))
                c = f'{pl_int(grosz)} {plural(grosz, "grosz", "grosze", "groszy")}'
                return (main + ' i ' + c) if main else c
            return pl_int(n) + ' ' + plural(n, 'złoty', 'złote', 'złotych')
        if unit in ('usd','$'):
            label = plural(n, 'dolar', 'dolary', 'dolarów')
        else:
            label = 'euro'
        result = pl_int(n) + ' ' + label
        if decimals and int(decimals): result += ' i ' + pl_int(int(decimals.ljust(2, '0'))) + ' centów'
        return result
    text = re.sub(r'(?<![\w\d])((?:\d{1,3}(?:[ .\u00a0]\d{3})+)|\d+)(?:[,.](\d{1,2}))?\s*(zł|PLN|EUR|euro|USD|\$|€)(?!\w)', currency, text, flags=re.IGNORECASE)

    def perc(m):
        whole, decimals = m.group(1), m.group(2)
        spoken = pl_int(int(whole))
        if decimals is not None:
            spoken += ' przecinek ' + pl_fraction(decimals)
        return spoken + ' ' + ('procenty' if decimals is None and int(whole) % 10 in (2,3,4) and int(whole) % 100 not in (12,13,14) else 'procent')
    text = re.sub(r'(?<![\w\d])(\d+)(?:[,.](\d+))?\s*%', perc, text)

    text = re.sub(r'(?<!\w)(-?\d+)\s*°\s*C\b', lambda m: pl_int(int(m.group(1))) + ' stopni Celsjusza', text, flags=re.IGNORECASE)

    # Common measurement units. Do not make Fish pronounce letters separately.
    def unit(m):
        val = int(m.group(1))
        name = m.group(2).lower()
        if name in ('km/h', 'km\\h'):
            return pl_int(val) + ' ' + plural(val, 'kilometr', 'kilometry', 'kilometrów') + ' na godzinę'
        forms = {'cm': ('centymetr','centymetry','centymetrów'),
                 'km': ('kilometr','kilometry','kilometrów'),
                 'kg': ('kilogram','kilogramy','kilogramów'),
                 'gb': ('gigabajt','gigabajty','gigabajtów'),
                 'mb': ('megabajt','megabajty','megabajtów'),
                 'tb': ('terabajt','terabajty','terabajtów')}
        return pl_int(val) + ' ' + plural(val, *forms[name])
    text = re.sub(r'(?<![\w\d])(\d+)\s*(km/h|cm|km|kg|GB|MB|TB)(?!\w)', unit, text, flags=re.IGNORECASE)

    # Millions with half units ('3,5 miliona') sound unnatural as decimals.
    text = re.sub(r'(?<!\w)(\d+)[,.]5(?=\s+(?:miliona|miliony|milionów|miliarda|miliardów|tysiąca|tysięcy)\b)',
                  lambda m: pl_int(int(m.group(1))) + ' i pół', text, flags=re.IGNORECASE)

    # Space-grouped thousands: '1 000', '12 500 000'.
    text = re.sub(r'(?<!\w)\d{1,3}(?:[ \u00a0]\d{3})+(?!\d)',
                  lambda m: pl_int(int(re.sub(r'\s', '', m.group()))), text)

    # Software versions / IP addresses, e.g. 1.0.5 or 192.168.1.1.
    text = re.sub(r'(?<![\w\d])\d+(?:\.\d+){2,}(?!\d)', lambda m: mask(' kropka '.join(pl_int(int(v)) for v in m.group().split('.'))), text)
    # Thousands separators; remove dots only for 1.000 or 1.000.000.
    text = re.sub(r'(?<!\w)\d{1,3}(?:\.\d{3})+(?![\d.])', lambda m: pl_int(int(m.group().replace('.', ''))), text)

    def decimals(m):
        a,b = m.groups()
        return pl_int(int(a.replace('−', '-'))) + ' przecinek ' + pl_fraction(b)
    text = re.sub(r'(?<![\w\d])([-−]?\d+)[,.](\d+)(?!\w)', decimals, text)

    # Ordinals commonly used in dialogue and lore: "2. sezon", "3. miejsce".
    def ordinal(m):
        n = int(m.group(1)); noun = m.group(2)
        neutral = noun.lower() in ('miejsce','piętro')
        return pl_ordinal(n, form='n' if neutral else 'm') + ' ' + noun
    text = re.sub(r'(?<!\w)(\d{1,2})\.\s+(sezon|odcinek|raz|dzień|poziom|miejsce|piętro)\b', ordinal, text, flags=re.IGNORECASE)

    def integer(m):
        raw = m.group()
        if len(raw.lstrip('-−')) >= 13:
            sign = 'minus ' if raw[0] in '-−' else ''
            return sign + pl_fraction(raw.lstrip('-−'))
        return pl_int(int(raw.replace('−','-')))
    text = re.sub(r'(?<![\w\d])[-−]?\d+(?!\w)', integer, text)
    for idx, value in enumerate(protected):
        text = text.replace(f'ZZZCAPRINUM{idx}ZZZ', value)
    return text


EN_UNITS = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
EN_TENS = ['', '', 'twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety']

def en_int(n: int) -> str:
    if n < 0: return 'minus ' + en_int(-n)
    if n < 20: return EN_UNITS[n]
    if n < 100:
        return EN_TENS[n // 10] + (' ' + EN_UNITS[n % 10] if n % 10 else '')
    for size, word in ((10**12,'trillion'),(10**9,'billion'),(10**6,'million'),(1000,'thousand'),(100,'hundred')):
        if n >= size:
            q, r = divmod(n, size)
            return en_int(q) + ' ' + word + (' ' + en_int(r) if r else '')
    return str(n)


def to_spoken_en(text: str) -> str:
    text = re.sub(r'(?<!\w)(-?\d+)(?:[,.](\d+))?\s*%',
                  lambda m: en_int(int(m.group(1))) + (' point ' + ' '.join(EN_UNITS[int(c)] for c in m.group(2)) if m.group(2) else '') + ' percent', text)
    text = re.sub(r'(?<!\w)(\d+)[,.](\d+)(?!\w)', lambda m: en_int(int(m.group(1))) + ' point ' + ' '.join(EN_UNITS[int(c)] for c in m.group(2)), text)
    text = re.sub(r'(?<![\w\d])-?\d+(?!\w)', lambda m: en_int(int(m.group())), text)
    return text


def normalize_for_speech(text: str, language: str = 'pl') -> str:
    """Convert numbers in TTS text only (never display/store this form)."""
    return to_spoken_pl(text) if language == 'pl' else to_spoken_en(text) if language == 'en' else text
