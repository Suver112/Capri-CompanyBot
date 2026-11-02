[🇵🇱 **Przełącz na Polski**](README.pl.md)

<div align="center">

# CAPRI
### CompanyBot

**Your AI-powered desktop voice companion. With personality.**

**Version 0.1.1 · Early Access · Windows**

[**Download Capri**](https://github.com/Suver112/Capri-CompanyBot/releases/tag/Pre-Release) · [**Source Code**](src/) · [**Report an Issue**](https://github.com/Suver112/Capri-CompanyBot/issues)

</div>

> [!IMPORTANT]
> **Unofficial fan project inspired by the Cyberpunk universe.** Capri CompanyBot is not developed, endorsed, approved, supported by, or affiliated with **CD PROJEKT RED**. Relevant characters, names, and trademarks belong to their respective owners. See the [CD PROJEKT RED fan content guidelines](https://www.cdprojektred.com/en/fan-content).

---

## About Capri CompanyBot

**Capri CompanyBot** is an independent desktop application combining conversational AI, voice interaction, conversation memory, and a cyberpunk-inspired interface. Its focus is on an expressive character, local AI processing, and selected desktop actions — rather than a conventional text-only chatbot.

Capri is an **early-access project**. Feature availability depends on your configuration, language model, speech engines, hardware, and connected services.

## Features

| Category | Capabilities |
| --- | --- |
| **Conversational AI** | Local models via Ollama, including Qwen and Bielik; optional external APIs |
| **Context and personality** | Multi-turn context, local memory, personality, and emotional responses |
| **Speech recognition (STT)** | Configurable Whisper- or Parakeet-based recognition |
| **Voice synthesis (TTS)** | Fish S2.cpp and optional speech backends; reference voice samples |
| **Interface** | Basic, Holocall, and Silverhand themes, avatar, and Mini mode |
| **Desktop controls** | Selected commands for applications, games, browser, and media |
| **Integrations** | Optional Spotify integration and other connected services |

> [!NOTE]
> Some features require additional models, separate backends, or external service setup. Hardware acceleration is not guaranteed on all systems. **The 0.1.1 release does not include a ready-to-use CUDA backend.**

## Download and installation

**Operating system:** Windows 10 or 11. Local AI hardware requirements vary significantly with the selected models and speech engines.

1. Visit [**Capri 0.1.1 — Early Access**](https://github.com/Suver112/Capri-CompanyBot/releases/tag/Pre-Release).
2. Download `Capri_Setup.exe` from **Assets**.
3. Run the installer and configure your preferred language model, speech recognition, and voice settings.

Windows or antivirus software may display a warning. Verify that the file comes from the official release and review its signature/checksum before making any security decisions.

**[Release notes and known issues — English / Polski](docs/13_WYDANIE_0_1_1.md)**

The source code is published in [`src/`](src/). This repository is **not** a replacement for the packaged Windows installer and does not contain all external models or Fish weights.

## Run from source

For developers and advanced users setting up Capri manually on Windows.

**Basic prerequisites:** Windows 10/11, Python 3.11, and [Ollama](https://ollama.com/) if you want to run local language models.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/main.py
```

Ollama models, STT/TTS engines, and any API keys must be configured separately. Installing Python dependencies **does not install** Fish S2.cpp or its model weights.

## Frequently asked questions

**Is Capri free?**  
The application is available free of charge. Optional third-party APIs and services may apply their own fees and terms.

**Can Capri run offline?**  
Selected local functions can work offline after the required models and components have been downloaded and configured. Model downloads, Spotify, and cloud services require internet access.

**Do I need an NVIDIA GPU?**  
No. Acceleration options vary by hardware, drivers, and backend. The 0.1.1 release does not include ready-to-use CUDA support, and Vulkan availability depends on your system.

**Where can I report issues?**  
Use [GitHub Issues](https://github.com/Suver112/Capri-CompanyBot/issues) with the Capri version, reproduction steps, expected versus actual behavior, and appropriately redacted logs.

## Documentation and contributions

- [Report bugs or request features](https://github.com/Suver112/Capri-CompanyBot/issues)
- [Contribution guidelines](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)
- [Third-party licenses and notices](THIRD_PARTY_NOTICES.md)

**Do not share API keys, private conversations, personal information, or complete user profiles in issue reports.**

## Credits and legal information

Capri CompanyBot is an **independent, unofficial fan project** and is not affiliated with CD PROJEKT RED.

Capri's artwork was generated using **ChatGPT**. According to the creator, **the included voice is entirely synthetic**: its reference sample was generated using Fish Audio without recordings or the voice of any real person.

The project source code is distributed under [GNU GPL v3](LICENSE). Third-party libraries, engines, models, model weights, and other assets retain their **own license terms**. In particular, the Capri source-code license does **not** imply that Fish S2-Pro weights are GPL-licensed. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

<div align="center">

**Capri CompanyBot · 0.1.1 — Early Access**

*Fan-made · Independent · Not affiliated with CD PROJEKT RED*

</div>
