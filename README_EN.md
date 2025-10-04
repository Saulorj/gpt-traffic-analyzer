<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/License-MIT-green">
  <img src="https://img.shields.io/badge/Status-Beta-yellow">
  <img src="https://img.shields.io/badge/Powered_by-Gatona💜-purple">
</p>


<p align="center">
  <img src="banner.png" width="100%" alt="GPT Traffic Analyzer — Powered by Saulo & Gatona 💜">
</p>

<p align="center">
  🌍 <b>Read this in:</b> 
  <a href="https://github.com/saulorj/gpt-traffic-analyzer/blob/main/README_PT-BR.md">🇧🇷 Português</a> |
  <a href="https://github.com/saulorj/gpt-traffic-analyzer/blob/main/README_EN.md">🇺🇸 English</a>
</p>


# 🚦 GPT Traffic Analyzer — Powered by Saulo & Gatona 💜

**GPT Traffic Analyzer** is an advanced Python tool that measures internet connection stability — analyzing **ping**, **jitter**, and **packet loss** while generating a **professional PDF report** with charts, diagnostics, and history tracking.

---

## ✨ Features
- 🧼 Clean terminal output  
- 🌈 Colorful progress bars with live ping  
- 🧭 Top progress bar for total time  
- 🌀 Fancy mode with animated spinner  
- 📊 PDF reports with charts and scores  
- 🧠 Smart diagnostics (0–10 rating)  
- 🎮 Suitability for streaming, video calls, and gaming  
- 🗃️ CSV history and trend chart  
- 🌐 Tests Google & Cloudflare (plus optional hosts)

---

## ⚙️ Installation
```bash
git clone https://github.com/saulorj/gpt-traffic-analyzer.git
cd gpt-traffic-analyzer
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

---

## 🚀 Basic Usage
```bash
python -m gpt_traffic_analyzer.analyzer
```

### CLI Example
```bash
python -m gpt_traffic_analyzer.analyzer --duration 30m --hosts "API=api.mysite.com" --ping-alert 100 --fancy
```

---

## 🧩 Parameters

| Parameter | Type | Default | Description |
|------------|------|----------|-------------|
| `--duration` | string | `60s` | Test duration (s, m, h) |
| `--hosts` | string | `Google, Cloudflare` | Additional hosts |
| `--ping-alert` | int | `100` | Ping alert threshold |
| `--output` | string | `network_report.pdf` | Output file name |
| `--fancy` | flag | `False` | Fancy animated mode |
| `--headless` | flag | `False` | Headless execution mode |
| `--help` | flag | — | Display full CLI guide |

---

## 🧠 Diagnostics
- Calculates a 0–10 score based on latency, jitter, and packet loss.  
- Indicates if the connection is suitable for:
  - 🎬 Streaming
  - 🎥 Video calls
  - 🎮 Online gaming

---

## 📁 Outputs
| Type | File | Description |
|------|------|-------------|
| 📊 PDF | `network_report.pdf` | Full report |
| 🧾 CSV | `GPT Traffic Analyzer.csv` | Historical logs |
| 📈 PNGs | `ping_graph.png`, `jitter_graph.png` | Exported charts |

---

## 💜 Credits
👨‍💻 **Saulo** — Developer  
🤖 **Gatona (ChatGPT - GPT‑5)** — Technical assistant  

---

<p align="center">
  🔗 <a href="https://github.com/saulorj/gpt-traffic-analyzer">github.com/saulorj/gpt-traffic-analyzer</a><br>
  <i>Made with 💜 by Saulo & Gatona — version 7.1 Beta</i>
</p>
