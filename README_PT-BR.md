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
  🌍 <b>Leia em:</b>
  <a href="https://github.com/saulorj/gpt-traffic-analyzer/blob/main/README_PT-BR.md">🇧🇷 Português</a> |
  <a href="https://github.com/saulorj/gpt-traffic-analyzer/blob/main/README_EN.md">🇺🇸 English</a>
</p>


# 🚦 GPT Traffic Analyzer — Powered by Saulo & Gatona 💜

O **GPT Traffic Analyzer** é uma ferramenta avançada em Python para analisar a estabilidade da sua conexão de internet.
Ele mede **ping**, **jitter** e **perda de pacotes**, gerando um relatório **PDF profissional** com gráficos, diagnósticos e histórico automático.

---

## ✨ Recursos
- 🧼 Terminal limpo e interface agradável
- 🌈 Barras de progresso coloridas com ping em tempo real
- 🧭 Barra geral superior com progresso total
- 🌀 Modo `--fancy` com spinner animado
- 📊 Relatório PDF com gráficos e notas
- 🧠 Diagnóstico inteligente (nota 0–10)
- 🎮 Avaliação para streaming, videoconferência e jogos
- 🗃️ Histórico CSV e painel de tendência
- 🌐 Google e Cloudflare sempre inclusos (mais hosts opcionais)

---

## ⚙️ Instalação
```bash
git clone https://github.com/saulorj/gpt-traffic-analyzer.git
cd gpt-traffic-analyzer
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

---

## 🚀 Uso básico
```bash
python -m gpt_traffic_analyzer.analyzer
```

### Execução CLI
```bash
python -m gpt_traffic_analyzer.analyzer --duration 30m --hosts "API=api.meusite.com" --ping-alert 100 --fancy
```
## ▶️ Exemplos de uso
```bash
python main.py --host 8.8.8.8 --count 50 --interval 0.2 --lang pt
python main.py --host google.com --count 60 --save-csv results.csv --lang en
```

## 🧪 Rodar os testes
```bash
pytest -v
```

## 🧠 Notes
- On Windows, ping interval cannot be controlled precisely.
- On Linux/macOS, use `sudo` if ping requires privileges.
- PDF and charts are saved automatically in the working directory.
---

## 🧩 Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|------------|------|--------|------------|
| `--duration` | string | `60s` | Tempo total do teste (s, m, h) |
| `--hosts` | string | `Google, Cloudflare` | Hosts adicionais |
| `--ping-alert` | int | `100` | Limite de alerta de ping |
| `--output` | string | `relatorio_teste.pdf` | Caminho e nome do relatório |
| `--fancy` | flag | `False` | Modo visual animado |
| `--headless` | flag | `False` | Executa sem interface gráfica |
| `--help` | flag | — | Mostra o guia completo |

---

## 🧠 Diagnóstico
- Calcula nota 0–10 com base em ping, jitter e perda.
- Mostra se a conexão é adequada para:
  - 🎬 Streaming
  - 🎥 Videoconferência
  - 🎮 Jogos online

---

## 📁 Saídas
| Tipo | Arquivo | Descrição |
|------|----------|-----------|
| 📊 PDF | `relatorio_teste.pdf` | Relatório completo |
| 🧾 CSV | `GPT Traffic Analyzer.csv` | Histórico de execuções |
| 📈 PNGs | `ping_graph.png`, `jitter_graph.png` | Gráficos exportados |

---

## 💜 Créditos
👨‍💻 **Saulo** — Desenvolvedor
🤖 **Gatona (ChatGPT - GPT‑5)** — Assistente técnica

---

<p align="center">
  🔗 <a href="https://github.com/saulorj/gpt-traffic-analyzer">github.com/saulorj/gpt-traffic-analyzer</a><br>
  <i>Feito com 💜 por Saulo & Gatona — versão 7.1 Beta</i>
</p>
