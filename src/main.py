
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Network Latency & Stability Analyzer (PT/EN i18n)
-----------------------------------------------------------
Features:
- Ping test runner (cross-platform: Windows / Linux / macOS)
- Aggregates latency metrics (avg, min, max, jitter) & packet loss
- Stability score and verdict
- Generates a PDF report (localized) with charts and summary
- CLI language selection: --lang pt | en (default: pt)
- Preserves existing visual style intent; easy to extend

Usage:
  python main.py --host 8.8.8.8 --count 50 --interval 0.2 --lang en
  python main.py --host 1.1.1.1 --count 30 --lang pt
  python main.py --host google.com --count 60 --save-csv results.csv --lang en

Requirements (install once):
  pip install reportlab matplotlib numpy pandas

Notes:
- This script calls the native `ping` command. On Windows, it pings in one shot.
  On Unix-like systems, it runs count-based pings. Admin privileges not required.
- If `ping` is unavailable in your PATH, please install it or run from an environment
  where it exists.
"""

import argparse
import csv
import os
import platform
import re
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# -----------------------------
# Internationalization (PT/EN)
# -----------------------------

I18N = {
    "pt": {
        "app_title": "Analisador de Latência e Estabilidade de Rede",
        "starting_test": "Iniciando teste de ping para {host} ({count} pacotes, intervalo {interval}s)...",
        "running": "Executando...",
        "done": "Concluído.",
        "no_rtt": "Nenhum RTT coletado. Verifique a conectividade ou permissões.",
        "summary": "Resumo",
        "host": "Alvo",
        "packets": "Pacotes",
        "sent": "Enviados",
        "received": "Recebidos",
        "lost": "Perdidos",
        "loss": "Perda",
        "latency_ms": "Latência (ms)",
        "avg": "Média",
        "min": "Mín",
        "max": "Máx",
        "jitter": "Jitter (desvio-médio)",
        "stability_score": "Pontuação de Estabilidade",
        "verdict": "Veredito",
        "excellent": "Excelente",
        "good": "Boa",
        "fair": "Regular",
        "poor": "Ruim",
        "very_poor": "Muito Ruim",
        "chart_latency": "Latência por pacote (ms)",
        "chart_hist": "Distribuição da latência (histograma)",
        "gen_pdf": "Gerando PDF...",
        "pdf_ready": "Relatório PDF gerado em: {path}",
        "saved_csv": "Resultados salvos em CSV: {path}",
        "params": "Parâmetros",
        "timestamp": "Data/Hora",
        "os": "Sistema",
        "version": "Versão Python",
        "interval_s": "Intervalo (s)",
        "count": "Quantidade",
        "lang": "Idioma",
        "report_title": "Relatório de Latência e Estabilidade",
        "method": "Metodologia",
        "method_text": (
            "Coletamos tempos de ida e volta (RTT) usando o utilitário do sistema `ping`. "
            "Calculamos média, mínimo, máximo e jitter (média do valor absoluto da variação entre pacotes). "
            "A pontuação de estabilidade combina perda de pacotes e jitter."
        ),
        "stability_text": (
            "A pontuação de estabilidade varia de 0 a 100. Quanto maior, melhor. "
            "Valores acima de 85 indicam rede estável para a maioria das aplicações."
        ),
        "footnote": "© {year} Relatório gerado automaticamente."
    },
    "en": {
        "app_title": "Network Latency & Stability Analyzer",
        "starting_test": "Starting ping test to {host} ({count} packets, interval {interval}s)...",
        "running": "Running...",
        "done": "Done.",
        "no_rtt": "No RTT collected. Check connectivity or permissions.",
        "summary": "Summary",
        "host": "Target",
        "packets": "Packets",
        "sent": "Sent",
        "received": "Received",
        "lost": "Lost",
        "loss": "Loss",
        "latency_ms": "Latency (ms)",
        "avg": "Avg",
        "min": "Min",
        "max": "Max",
        "jitter": "Jitter (mean absolute delta)",
        "stability_score": "Stability Score",
        "verdict": "Verdict",
        "excellent": "Excellent",
        "good": "Good",
        "fair": "Fair",
        "poor": "Poor",
        "very_poor": "Very Poor",
        "chart_latency": "Latency per packet (ms)",
        "chart_hist": "Latency distribution (histogram)",
        "gen_pdf": "Generating PDF...",
        "pdf_ready": "PDF report generated at: {path}",
        "saved_csv": "Results saved to CSV: {path}",
        "params": "Parameters",
        "timestamp": "Timestamp",
        "os": "OS",
        "version": "Python Version",
        "interval_s": "Interval (s)",
        "count": "Count",
        "lang": "Language",
        "report_title": "Latency & Stability Report",
        "method": "Methodology",
        "method_text": (
            "We collect round-trip times (RTT) using the system `ping` utility. "
            "We compute average, min, max, and jitter (mean absolute delta between packets). "
            "The stability score combines packet loss and jitter."
        ),
        "stability_text": (
            "Stability score ranges from 0 to 100. Higher is better. "
            "Values above 85 indicate a stable network for most applications."
        ),
        "footnote": "© {year} Report generated automatically."
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Translate helper with fallback to English if key missing."""
    if lang not in I18N:
        lang = "en"
    s = I18N[lang].get(key, I18N["en"].get(key, key))
    return s.format(**kwargs) if kwargs else s


# -----------------------------
# Ping runner & parsing
# -----------------------------

RTT_REGEXES = [
    re.compile(r'time[=<]?\s*(\d+(?:\.\d+)?)\s*ms', re.IGNORECASE),   # linux/mac common
    re.compile(r'time[=<]?\s*(\d+)\s*ms', re.IGNORECASE),            # windows common
]


def run_ping(host: str, count: int, interval: float) -> Tuple[List[float], int, int]:
    """
    Run ping to `host` for `count` probes. Returns (rtts_ms, sent, received).
    Cross-platform handling of native ping output.
    """
    system = platform.system().lower()
    if system == "windows":
        # Windows: ping -n <count> -w timeout(ms)
        # Interval between pings on Windows can't be set easily; we accept default.
        cmd = ["ping", "-n", str(count), host]
    else:
        # Linux/mac: ping -c <count> -i <interval>
        cmd = ["ping", "-c", str(count), "-i", str(interval), host]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        output = proc.stdout
    except FileNotFoundError:
        print("`ping` command not found in PATH.", file=sys.stderr)
        return [], count, 0

    # Parse RTTs
    rtts = []
    for line in output.splitlines():
        for rx in RTT_REGEXES:
            m = rx.search(line)
            if m:
                try:
                    rtts.append(float(m.group(1)))
                    break
                except ValueError:
                    pass

    # Infer packet stats if possible
    sent = count
    received = len(rtts)

    # Attempt to parse explicit packet stats from output (optional)
    # Linux summary example: "packets transmitted, X received, Y% packet loss"
    m = re.search(r'(\d+)\s+packets\s+transmitted,\s+(\d+)\s+received', output, re.IGNORECASE)
    if m:
        sent = int(m.group(1))
        received = int(m.group(2))

    # Windows summary example: "Packets: Sent = X, Received = Y, Lost = Z (W% loss)"
    m = re.search(r'Packets:\s*Sent\s*=\s*(\d+),\s*Received\s*=\s*(\d+),\s*Lost\s*=\s*(\d+)', output, re.IGNORECASE)
    if m:
        sent = int(m.group(1))
        received = int(m.group(2))

    return rtts, sent, received


# -----------------------------
# Metrics & scoring
# -----------------------------

def compute_metrics(rtts: List[float], sent: int, received: int) -> Dict[str, Any]:
    loss_pct = 0.0 if sent == 0 else (sent - received) * 100.0 / sent
    if rtts:
        avg = float(np.mean(rtts))
        min_v = float(np.min(rtts))
        max_v = float(np.max(rtts))
        # jitter: mean absolute delta between consecutive RTTs
        deltas = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
        jitter = float(np.mean(deltas)) if deltas else 0.0
    else:
        avg = min_v = max_v = jitter = float("nan")
    score, verdict = stability_score(loss_pct, jitter)
    return {
        "loss_pct": loss_pct,
        "avg": avg,
        "min": min_v,
        "max": max_v,
        "jitter": jitter,
        "score": score,
        "verdict": verdict,
    }


def stability_score(loss_pct: float, jitter_ms: float) -> Tuple[float, str]:
    """
    Stability score: 0..100 (higher is better).
    Heuristic:
      - Base 100
      - Subtract loss impact: loss_weight * loss_pct
      - Subtract jitter impact: jitter_weight * log1p(jitter_ms)
    Tuned to reward low loss and low jitter.
    """
    loss_weight = 2.2        # each 1% loss penalizes 2.2 points
    jitter_weight = 9.0      # log-scale penalty for jitter

    score = 100.0
    score -= loss_weight * loss_pct
    score -= jitter_weight * np.log1p(max(0.0, jitter_ms))
    score = max(0.0, min(100.0, score))

    if score >= 90:
        verdict = "excellent"
    elif score >= 80:
        verdict = "good"
    elif score >= 65:
        verdict = "fair"
    elif score >= 45:
        verdict = "poor"
    else:
        verdict = "very_poor"
    return score, verdict


# -----------------------------
# PDF report generation
# -----------------------------

def make_charts(lang: str, rtts: List[float], out_dir: Path) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_path = out_dir / "latency_timeseries.png"
    hist_path = out_dir / "latency_hist.png"

    # Time series chart
    plt.figure()
    plt.plot(range(1, len(rtts)+1), rtts, marker="o", linewidth=1)
    plt.xlabel("#")
    plt.ylabel(t(lang, "latency_ms"))
    plt.title(t(lang, "chart_latency"))
    plt.tight_layout()
    plt.savefig(ts_path, dpi=160)
    plt.close()

    # Histogram
    plt.figure()
    bins = min(30, max(5, int(np.sqrt(max(1, len(rtts))))))
    plt.hist(rtts, bins=bins)
    plt.xlabel(t(lang, "latency_ms"))
    plt.ylabel("freq")
    plt.title(t(lang, "chart_hist"))
    plt.tight_layout()
    plt.savefig(hist_path, dpi=160)
    plt.close()

    return ts_path, hist_path


def draw_label_value(c: canvas.Canvas, x: float, y: float, label: str, value: str):
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, f"{label}: ")
    c.setFont("Helvetica", 10)
    c.drawString(x + 90, y, value)


def generate_pdf(lang: str, host: str, args: argparse.Namespace, metrics: Dict[str, Any],
                 ts_img: Path, hist_img: Path, rtts: List[float]) -> Path:
    # File name localized
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = "relatorio" if lang == "pt" else "report"
    pdf_path = Path(f"{name}_{host}_{timestamp}.pdf")

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    margin = 1.8 * cm
    x0 = margin
    y = height - margin

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(x0, y, t(lang, "report_title"))
    y -= 0.8 * cm

    # App title
    c.setFont("Helvetica", 12)
    c.drawString(x0, y, t(lang, "app_title"))
    y -= 0.6 * cm

    # Parameters block
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0, y, t(lang, "params"))
    y -= 0.5 * cm

    draw_label_value(c, x0, y, t(lang, "timestamp"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "host"), host)
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "os"), platform.platform())
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "version"), sys.version.split()[0])
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "interval_s"), f"{args.interval}")
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "count"), f"{args.count}")
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "lang"), args.lang)
    y -= 0.8 * cm

    # Summary metrics
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0, y, t(lang, "summary"))
    y -= 0.5 * cm

    draw_label_value(c, x0, y, t(lang, "packets") + f" ({t(lang,'sent')}/{t(lang,'received')}/{t(lang,'lost')})",
                     f"{metrics.get('sent', args.count)}/{len(rtts)}/{args.count - len(rtts)}")
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "loss"), f"{metrics['loss_pct']:.2f}%")
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "latency_ms") + f" ({t(lang,'avg')}/{t(lang,'min')}/{t(lang,'max')})",
                     f"{metrics['avg']:.2f}/{metrics['min']:.2f}/{metrics['max']:.2f}" if rtts else "-/-/-")
    y -= 0.5 * cm
    draw_label_value(c, x0, y, t(lang, "jitter"), f"{metrics['jitter']:.2f}" if rtts else "-")
    y -= 0.5 * cm
    verdict_key = metrics["verdict"]
    verdict_localized = t(lang, verdict_key)
    draw_label_value(c, x0, y, t(lang, "stability_score"),
                     f"{metrics['score']:.1f} • {t(lang, 'verdict')}: {verdict_localized}")
    y -= 0.8 * cm

    # Charts
    img_w = (width - 2*margin)
    img_h = 7.0 * cm

    try:
        c.drawImage(ImageReader(str(ts_img)), x0, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
        y -= img_h + 0.5 * cm
        c.drawImage(ImageReader(str(hist_img)), x0, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
        y -= img_h + 0.6 * cm
    except Exception as e:
        # If images fail, continue
        c.setFont("Helvetica", 10)
        c.drawString(x0, y, f"[charts unavailable: {e}]")
        y -= 0.6 * cm

    # Methodology & Stability text
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0, y, t(lang, "method"))
    y -= 0.45 * cm
    c.setFont("Helvetica", 10)
    text_obj = c.beginText(x0, y)
    text_obj.textLines(t(lang, "method_text"))
    c.drawText(text_obj)
    y -= 2.0 * cm

    text_obj = c.beginText(x0, y)
    text_obj.textLines(t(lang, "stability_text"))
    c.drawText(text_obj)
    y -= 1.2 * cm

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(x0, margin / 2, t(lang, "footnote", year=datetime.now().year))

    c.showPage()
    c.save()
    return pdf_path


# -----------------------------
# CSV saving (optional)
# -----------------------------

def save_csv(path: Path, rtts: List[float]):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["seq", "rtt_ms"])
        for i, r in enumerate(rtts, start=1):
            writer.writerow([i, f"{r:.3f}"])


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Network Latency & Stability Analyzer (PT/EN)")
    p.add_argument("--host", default="8.8.8.8", help="Host/IP to ping (default: 8.8.8.8)")
    p.add_argument("--count", type=int, default=50, help="Number of pings (default: 50)")
    p.add_argument("--interval", type=float, default=0.2, help="Interval between pings in seconds (default: 0.2)")
    p.add_argument("--lang", choices=["pt", "en"], default="pt", help="Language (pt or en). Default: pt")
    p.add_argument("--save-csv", default="", help="Optional path to save raw RTTs as CSV")
    return p.parse_args()


def main():
    args = parse_args()
    lang = args.lang

    print(t(lang, "starting_test", host=args.host, count=args.count, interval=args.interval))
    print(t(lang, "running"))

    rtts, sent, received = run_ping(args.host, args.count, args.interval)

    if not rtts:
        print(t(lang, "no_rtt"))
        # still compute metrics with no data
    else:
        # Trim to `received` in case parser found more lines than summary reported
        rtts = rtts[:received]

    # Compute metrics
    m = compute_metrics(rtts, sent, received)
    m["sent"] = sent  # keep in dict for PDF
    m["received"] = received

    # Make charts
    charts_dir = Path("charts_cache")
    ts_img, hist_img = make_charts(lang, rtts, charts_dir)

    # PDF
    print(t(lang, "gen_pdf"))
    pdf_path = generate_pdf(lang, args.host, args, m, ts_img, hist_img, rtts)
    print(t(lang, "pdf_ready", path=pdf_path))

    # Optional CSV
    if args.save_csv:
        save_csv(Path(args.save_csv), rtts)
        print(t(lang, "saved_csv", path=args.save_csv))

    print(t(lang, "done"))


if __name__ == "__main__":
    main()
