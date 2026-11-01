# -*- coding: utf-8 -*-
"""Spotify authorization utility, run once in a console."""
from capri_spotify_web import connect, CALLBACK

def main():
    print('CAPRI // SPOTIFY: polaczenie konta')
    print('1. Utworz aplikacje w https://developer.spotify.com/dashboard')
    print('2. W Redirect URIs dodaj dokladnie:', CALLBACK)
    print('3. Skopiuj Client ID. Nie wklejaj tu hasla Spotify.')
    value=input('Spotify Client ID: ').strip()
    connect(value)
    print('Polaczono Spotify! Mozesz uruchamiac konkretne utwory przez Capri.')

if __name__ == '__main__':
    try: main()
    except Exception as exc: print('BLAD:',str(exc))
    input('Nacisnij Enter, aby zamknac...')
