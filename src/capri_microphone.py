"""One Windows microphone choice shared by manual STT, Parakeet and wake listening.

Never switch a specifically selected (now disconnected) device to a different mic:
otherwise enabling voice capture could unexpectedly record from another input.
"""
from __future__ import annotations


def list_input_devices(sd):
    """Return stable user-facing labels and JSON-safe descriptors; no streams opened."""
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    result = []
    for index, info in enumerate(devices):
        if int(info.get('max_input_channels', 0)) < 1:
            continue
        host_idx = int(info.get('hostapi', -1))
        host = hostapis[host_idx].get('name', '') if 0 <= host_idx < len(hostapis) else ''
        name = str(info.get('name', 'Mikrofon'))
        descriptor = {'name': name, 'hostapi': str(host), 'index': index}
        result.append((f'{name}  [{host}]' if host else name, descriptor))
    return result


def resolve_input_device(sd, choice=None):
    """Return portaudio index or None (system default), never silent misrouting."""
    if choice is None:
        return None
    if not isinstance(choice, dict) or not isinstance(choice.get('name'), str):
        raise RuntimeError('Niepoprawny zapis wyboru mikrofonu. Wybierz urządzenie ponownie.')
    matches = [(label, data) for label, data in list_input_devices(sd)
               if data['name'] == choice['name'] and data['hostapi'] == choice.get('hostapi', '')]
    if not matches:
        raise RuntimeError('Wybrany mikrofon jest odłączony lub niedostępny: '
                           + choice['name'] + '. Zmień go w Ustawienia → Nasłuch (STT).')
    preferred_index = choice.get('index')
    for _label, data in matches:
        if data['index'] == preferred_index:
            return data['index']
    # PortAudio indices can change on hot-plug, but a unique name/host remains stable.
    if len(matches) == 1:
        return matches[0][1]['index']
    raise RuntimeError('Kilka mikrofonów ma identyczną nazwę. Odśwież listę i wybierz ponownie.')


def test_input_device(sd, choice=None, seconds=0.6):
    """Short, explicit test without storing or uploading the captured sound."""
    import numpy as np
    index = resolve_input_device(sd, choice)
    info = sd.query_devices(index, kind='input') if index is not None else sd.query_devices(kind='input')
    rate = int(info.get('default_samplerate', 48000))
    if not 8000 <= rate <= 192000:
        rate = 48000
    # sd.rec would use global default if device were omitted; pass the chosen index.
    frames = sd.rec(max(1, int(rate * seconds)), samplerate=rate, channels=1,
                    dtype='int16', device=index)
    sd.wait()
    rms = float(np.sqrt(np.mean(np.square(frames.astype(np.float32))))) if frames.size else 0.0
    return rms
