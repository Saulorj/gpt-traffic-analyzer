# Coloque aqui o código do GPT Traffic Analyzer v7.1
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GPT Traffic Analyzer v7.1 🚦 — Saulo Gatão Edition
- Limpar tela automático
- Barra geral colorida no topo (+ spinner opcional via --fancy) e % à direita
- Barras por host alinhadas e coloridas (nome + ping + barra)
- Gráficos grandes (1 por página) com explicações didáticas
- Diagnóstico + adequação (streaming/videoconferência/jogos)
- CSV histórico (por host + OVERALL) + painel histórico no PDF
- CLI + modo interativo + headless (cron-friendly)
"""

import os
import re
import sys
import time
import math
import argparse
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)

# ====================== BASELINES ======================

@dataclass
class Baselines:
    ping_good: float = 30.0
    ping_ok: float = 50.0
    ping_reg: float = 100.0
    jitter_good: float = 5.0
    jitter_ok: float = 10.0
    jitter_reg: float = 20.0
    loss_ok: float = 1.0
    loss_reg: float = 3.0

BASE = Baselines()

ANSI_RESET = "\033[0m"
ANSI_COLORS_SEQ = [
    "\033[94m",  # Azul (Google)
    "\033[33m",  # Laranja (Cloudflare)
    "\033[92m",  # Verde
    "\033[93m",  # Amarelo
    "\033[95m",  # Rosa
    "\033[97m",  # Branco
    "\033[96m",  # Azul claro
    "\033[32m",  # Verde claro
    "\033[91m",  # Vermelho
]
ANSI_CYAN_BRIGHT = "\033[96m"  # barra geral

CSV_NAME = "GPT Traffic Analyzer.csv"
SPINNER_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

# ====================== UTIL ======================

def clear_screen():
    try:
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
    except Exception:
        print("\033[2J\033[H", end="")

def human_duration_to_seconds(raw: str) -> int:
    if not raw:
        return 60
    raw = raw.strip().lower()
    m = re.match(r"^(\d+)\s*([hms])?$", raw)
    if not m:
        return 60
    val, unit = int(m.group(1)), (m.group(2) or "s")
    return val * 3600 if unit == "h" else val * 60 if unit == "m" else val

def ping_once(host: str) -> Optional[float]:
    cmd = ["ping", "-n", "1", host] if os.name == "nt" else ["ping", "-c", "1", host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
    except Exception:
        return None
    out = result.stdout
    if "ttl=" not in out.lower() and "ttl=" not in out.upper():
        return None
    m = re.search(r"(?:time|tempo|temps|zeit|tiempo)\s*[=<]?\s*([\d\.,]+)\s*ms", out, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except:
            return None
    if "tempo=" in out.lower():
        try:
            return float(out.lower().split("tempo=")[1].split("ms")[0].strip().replace(",", "."))
        except:
            return None
    return None

def compute_metrics(series: List[Optional[float]]) -> Dict[str, float]:
    arr = pd.Series(series, dtype="float64")
    valid = arr.dropna()
    if valid.empty:
        return dict(sent=int(len(arr)), loss_pct=100.0, mean=np.nan, p95=np.nan, min=np.nan, max=np.nan, jitter=np.nan)
    return {
        "sent": int(len(arr)),
        "loss_pct": float(arr.isna().sum() / len(arr) * 100.0),
        "mean": float(valid.mean()),
        "p95": float(np.percentile(valid, 95)),
        "min": float(valid.min()),
        "max": float(valid.max()),
        "jitter": float(valid.diff().abs().dropna().std())
    }

def score_metric_ping(p: float) -> float:
    if p <= BASE.ping_good: return 10
    if p <= BASE.ping_ok: return 8
    if p <= BASE.ping_reg: return 6
    if p <= 200: return 3
    return 1

def score_metric_jitter(j: float) -> float:
    if j <= BASE.jitter_good: return 10
    if j <= BASE.jitter_ok: return 8
    if j <= BASE.jitter_reg: return 6
    return 1

def score_metric_loss(l: float) -> float:
    if l == 0: return 10
    if l <= BASE.loss_ok: return 8
    if l <= BASE.loss_reg: return 6
    return 1

def verdict_from_scores(ping: float, jitter: float, loss: float) -> str:
    if loss > BASE.loss_reg or ping > BASE.ping_reg or jitter > BASE.jitter_reg:
        return "⚠️ Rede instável (latência/jitter/perda elevados)."
    if loss > BASE.loss_ok or ping > BASE.ping_ok or jitter > BASE.jitter_ok:
        return "ℹ️ Rede ok, mas com leves oscilações."
    return "✅ Conexão excelente e estável."

def adequacy_label(ok: bool) -> str:
    return "Adequada ✅" if ok else "Não recomendada ⚠️"

def suitability(ping: float, jitter: float, loss: float) -> Dict[str, str]:
    streaming = (loss < 1.0 and ping < 100 and jitter < 30)
    videocall = (loss < 1.0 and ping < 80 and jitter < 20)
    gaming = (loss < 1.0 and ping < 40 and jitter < 10)
    return {
        "Streaming": adequacy_label(streaming),
        "Videoconferência": adequacy_label(videocall),
        "Jogos online": adequacy_label(gaming),
    }

# ====================== TESTE (com barras alinhadas + barra geral) ======================

def render_bar(percent: int, width: int, color_ansi: str) -> str:
    fill = int(width * percent / 100)
    bar = "▓" * fill + "░" * (width - fill)
    return f"{color_ansi}{bar}{ANSI_RESET}"

def run_test(hosts: Dict[str, str], duration: int, interval: float = 1.0, fancy: bool = False) -> Tuple[pd.DataFrame, Dict[str, List[Optional[float]]]]:
    clear_screen()
    start = time.time()
    data: List[Dict] = []
    series: Dict[str, List[Optional[float]]] = {n: [] for n in hosts}

    host_list = list(hosts.keys())
    colors_for_hosts = {name: ANSI_COLORS_SEQ[i % len(ANSI_COLORS_SEQ)] for i, name in enumerate(host_list)}
    name_field_width = max(18, max(len(n) for n in host_list))  # alinha nomes
    total_steps = int(math.ceil(duration / interval))
    spinner_idx = 0

    print(f"▶️ GPT Traffic Analyzer v7.1 — executando por {duration}s em {len(hosts)} servidores...\n")

    for step in range(total_steps):
        t_now = time.time() - start
        remain = max(0, duration - int(t_now))

        # ---- cabeçalho + barra geral no topo ----
        overall_pct = min(100, int(((step + 1) / total_steps) * 100))
        overall_bar = render_bar(overall_pct, width=30, color_ansi=ANSI_CYAN_BRIGHT)
        spin = SPINNER_FRAMES[spinner_idx % len(SPINNER_FRAMES)] if fancy else " "
        spinner_idx += 1

        # limpar e posicionar
        print("\033[2J\033[H", end="")
        print(f"⏳ Restam: {remain:02d}s")
        print(f"{spin} Geral (tempo total): {overall_bar}  {overall_pct:3d}%\n")

        # ---- linhas por host (alinhadas) ----
        for name, host in hosts.items():
            val = ping_once(host)
            series[name].append(val)
            data.append({"ts": int(t_now), "host_name": name, "host": host, "ping_ms": val})

            host_pct = overall_pct  # mesmo compasso temporal
            host_bar = render_bar(host_pct, width=28, color_ansi=colors_for_hosts[name])
            val_txt = f"{val:.1f} ms" if val is not None else "timeout"
            name_fmt = f"[{name}]".ljust(name_field_width + 2)  # +2 pelo "[]"
            line = f"{colors_for_hosts[name]}{name_fmt} {val_txt:>9} | {host_bar}  {host_pct:3d}%{ANSI_RESET}"
            print(line)

        # espera até o próximo tick
        elapsed = time.time() - start
        next_tick = (step + 1) * interval
        sleep_left = next_tick - elapsed
        if sleep_left > 0:
            time.sleep(sleep_left)

    print("\n✔️ Teste concluído.\n")
    df = pd.DataFrame(data)
    return df, series

# ====================== GRÁFICOS ======================

def graph_comparative(df: pd.DataFrame, path: str):
    plt.figure(figsize=(11.7, 7.5))
    for n in df["host_name"].unique():
        s = df[df["host_name"] == n].sort_values("ts")
        plt.plot(s["ts"], s["ping_ms"], marker=".", linestyle="-", label=n)
        valid = s["ping_ms"].dropna()
        if not valid.empty:
            plt.axhline(valid.mean(), linestyle="--", alpha=0.9, label=f"Média {n}: {valid.mean():.2f} ms")
    plt.title("Comparativo de Latência (ms) ao longo do tempo")
    plt.xlabel("Tempo (s)")
    plt.ylabel("Ping (ms)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

def graph_bars(metrics: Dict[str, Dict[str, float]], path: str):
    names = list(metrics.keys())
    means = [metrics[n]["mean"] for n in names]
    jitters = [metrics[n]["jitter"] for n in names]
    losses = [metrics[n]["loss_pct"] for n in names]
    x = np.arange(len(names))
    h = 0.25

    plt.figure(figsize=(11.7, 7.5))
    plt.barh(x - h, means, height=h, label="Ping médio (ms)")
    plt.barh(x, jitters, height=h, label="Jitter (ms)")
    plt.barh(x + h, losses, height=h, label="Perda (%)")
    plt.yticks(x, names)
    plt.xlabel("Valor (ms / %)")
    plt.title("Desempenho por Destino (Ping / Jitter / Perda)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

def graph_heatmap(df: pd.DataFrame, path: str):
    if df.empty:
        plt.figure(figsize=(11.7, 7.5))
        plt.title("Heatmap de Latência — sem dados")
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        return
    pivot = df.pivot_table(index="host_name", columns="ts", values="ping_ms", aggfunc="mean")
    plt.figure(figsize=(11.7, 7.5))
    im = plt.imshow(pivot.values, aspect="auto")
    plt.colorbar(im, label="Ping (ms)")
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xlabel("Tempo (s)")
    plt.title("Heatmap de Latência")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

# ====================== CSV HISTÓRICO ======================

def append_history_csv(test_id: str, timestamp: str, metrics: Dict[str, Dict[str, float]], overall_score: float):
    rows = []
    for name, m in metrics.items():
        rows.append({
            "test_id": test_id,
            "timestamp": timestamp,
            "host": name,
            "loss_pct": m["loss_pct"],
            "mean_ms": m["mean"],
            "p95_ms": m["p95"],
            "min_ms": m["min"],
            "max_ms": m["max"],
            "jitter_ms": m["jitter"],
            "overall_score": overall_score
        })
    # OVERALL
    means = [m["mean"] for m in metrics.values() if not (m["mean"] is None or math.isnan(m["mean"]))]
    jitters = [m["jitter"] for m in metrics.values() if not (m["jitter"] is None or math.isnan(m["jitter"]))]
    losses = [m["loss_pct"] for m in metrics.values()]
    rows.append({
        "test_id": test_id,
        "timestamp": timestamp,
        "host": "OVERALL",
        "loss_pct": float(np.mean(losses)) if losses else np.nan,
        "mean_ms": float(np.nanmean(means)) if means else np.nan,
        "p95_ms": np.nan,
        "min_ms": np.nan,
        "max_ms": np.nan,
        "jitter_ms": float(np.nanmean(jitters)) if jitters else np.nan,
        "overall_score": overall_score
    })

    df_new = pd.DataFrame(rows)
    if os.path.exists(CSV_NAME):
        df_old = pd.read_csv(CSV_NAME)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new
    df_all.to_csv(CSV_NAME, index=False)

# ====================== PDF ======================

def build_pdf(output: str, df: pd.DataFrame, metrics: Dict[str, Dict[str, float]], alert_ping: float):
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, leading=11)
    title = styles["Title"]

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )
    story = []

    # Cabeçalho
    story.append(Paragraph("<b>GPT Traffic Analyzer v7.1</b> 🚦", title))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Servidores testados: <b>{', '.join(metrics.keys())}</b>", normal))
    story.append(Spacer(1, 10))

    # Tabela principal
    header = ["Servidor", "Perda (%)", "Média (ms)", "p95 (ms)", "Min", "Máx", "Jitter (ms)"]
    def fmt(v):
        return "—" if (v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))) else f"{v:.2f}"
    rows = [[n, fmt(m["loss_pct"]), fmt(m["mean"]), fmt(m["p95"]), fmt(m["min"]), fmt(m["max"]), fmt(m["jitter"])]
            for n, m in metrics.items()]
    tbl = Table([header] + rows, hAlign="LEFT", colWidths=[120, 60, 60, 60, 50, 50, 60])
    style = [
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke)
    ]
    for i, r in enumerate(rows, start=1):
        try:
            loss = float(str(r[1]).replace(",", "."))
            mean = float(str(r[2]).replace(",", "."))
            jitter = float(str(r[6]).replace(",", "."))
            if loss > 1.0: style.append(("TEXTCOLOR", (1,i), (1,i), colors.red))
            if mean > alert_ping: style.append(("TEXTCOLOR", (2,i), (2,i), colors.red))
            if jitter > BASE.jitter_ok: style.append(("TEXTCOLOR", (6,i), (6,i), colors.red))
        except:
            pass
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 10))

    # Legenda didática
    story.append(Paragraph("<b>Como interpretar</b>", styles["Heading3"]))
    story.append(Paragraph("• <b>Perda (%)</b>: quanto menor, melhor. Acima de 1% já causa travadinhas.", small))
    story.append(Paragraph("• <b>Média</b> e <b>p95</b>: latência típica e limite para 95% das medições (quanto menores, melhor).", small))
    story.append(Paragraph("• <b>Jitter</b>: variação entre pings (quanto menor, mais estável). Valores altos prejudicam voz/vídeo.", small))

    # Imagens grandes (uma por página + texto didático)
    cmp_img = "v71_comparativo.png"
    bars_img = "v71_barras.png"
    heat_img = "v71_heatmap.png"
    graph_comparative(df, cmp_img)
    graph_bars(metrics, bars_img)
    graph_heatmap(df, heat_img)

    # Comparativo
    story.append(PageBreak())
    story.append(Paragraph("<b>Comparativo de Latência (ms)</b>", styles["Heading2"]))
    story.append(Spacer(1, 8))
    story.append(Image(cmp_img, width=17*cm, height=10*cm))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Cada linha mostra a latência por destino ao longo do tempo. Linhas baixas e suaves indicam estabilidade. "
        "Picos e serrilhados sugerem variação momentânea ou congestionamento. Se um destino fica sempre acima dos demais, "
        "pode haver problema de rota até ele.",
        small
    ))

    # Barras
    story.append(PageBreak())
    story.append(Paragraph("<b>Desempenho por Destino (Ping / Jitter / Perda)</b>", styles["Heading2"]))
    story.append(Spacer(1, 8))
    story.append(Image(bars_img, width=17*cm, height=10*cm))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Barras menores são melhores. Ping afeta o tempo de resposta; jitter alto causa cortes em voz/vídeo; perda acima de 1% "
        "tende a gerar travamentos perceptíveis. Use este gráfico para comparar destinos rapidamente.",
        small
    ))

    # Heatmap
    story.append(PageBreak())
    story.append(Paragraph("<b>Heatmap de Latência</b>", styles["Heading2"]))
    story.append(Spacer(1, 8))
    story.append(Image(heat_img, width=17*cm, height=8*cm))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Cores indicam níveis de latência ao longo do tempo (quanto mais claro, maior o ping). Faixas claras recorrentes "
        "indicam períodos de piora. Regiões mais escuras sugerem maior estabilidade.",
        small
    ))

    # Estatísticas finais + diagnóstico
    pings = [m["mean"] for m in metrics.values() if not (m["mean"] is None or math.isnan(m["mean"]))]
    jitters = [m["jitter"] for m in metrics.values() if not (m["jitter"] is None or math.isnan(m["jitter"]))]
    losses = [m["loss_pct"] for m in metrics.values()]
    ping_avg = float(np.nanmean(pings)) if pings else 999.0
    jitter_avg = float(np.nanmean(jitters)) if jitters else 999.0
    loss_avg = float(np.mean(losses)) if losses else 100.0

    nota = (0.4 * score_metric_ping(ping_avg) +
            0.3 * score_metric_jitter(jitter_avg) +
            0.3 * score_metric_loss(loss_avg))
    veredito = verdict_from_scores(ping_avg, jitter_avg, loss_avg)
    suit = suitability(ping_avg, jitter_avg, loss_avg)

    story.append(PageBreak())
    story.append(Paragraph("<b>Resumo e Diagnóstico</b>", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Ping médio:</b> {ping_avg:.2f} ms | <b>Jitter médio:</b> {jitter_avg:.2f} ms | <b>Perda média:</b> {loss_avg:.2f} %", normal))
    story.append(Paragraph(f"<b>Nota geral:</b> {nota:.1f} / 10", normal))
    story.append(Paragraph(f"<b>Diagnóstico:</b> {veredito}", normal))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Adequação por uso</b>", styles["Heading3"]))
    story.append(Paragraph(f"• Streaming: {suit['Streaming']}", normal))
    story.append(Paragraph(f"• Videoconferência: {suit['Videoconferência']}", normal))
    story.append(Paragraph(f"• Jogos online: {suit['Jogos online']}", normal))

    # Painel histórico
    story.append(PageBreak())
    story.append(Paragraph("<b>Painel Histórico</b>", styles["Heading2"]))
    if not os.path.exists(CSV_NAME):
        story.append(Paragraph("Histórico ainda não disponível — execute novos testes para construir comparativos.", normal))
    else:
        hist = pd.read_csv(CSV_NAME)
        hist_overall = hist[hist["host"] == "OVERALL"].copy()
        if hist_overall.empty:
            story.append(Paragraph("Histórico ainda não disponível — execute novos testes para construir comparativos.", normal))
        else:
            hist_overall["timestamp"] = pd.to_datetime(hist_overall["timestamp"])
            hist_overall = hist_overall.sort_values("timestamp").tail(50)

            fig_path = "v71_historico.png"
            plt.figure(figsize=(11.7, 7.5))
            t = hist_overall["timestamp"]
            plt.plot(t, hist_overall["mean_ms"], label="Ping médio (ms)")
            plt.plot(t, hist_overall["jitter_ms"], label="Jitter (ms)")
            plt.plot(t, hist_overall["loss_pct"], label="Perda (%)")
            ax = plt.gca()
            ax2 = ax.twinx()
            ax2.plot(t, hist_overall["overall_score"], linestyle="--", label="Nota (0-10)", color="tab:purple")
            ax.set_title("Tendência Histórica (últimas execuções)")
            ax.set_xlabel("Execuções no tempo")
            ax.set_ylabel("Ping/Jitter/Perda")
            ax2.set_ylabel("Nota (0-10)")
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            plt.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
            plt.tight_layout()
            plt.savefig(fig_path, dpi=150)
            plt.close()
            story.append(Image(fig_path, width=17*cm, height=10*cm))
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                "Este painel mostra a evolução da rede ao longo das execuções. Tendências ascendentes de ping/jitter/perda "
                "indicam piora; a nota resume o conjunto das métricas. Use-o para identificar mudanças de qualidade ao longo do tempo.",
                small
            ))

    doc.build(story)
    print(f"✅ Relatório gerado: {output}")

# ====================== CLI / MAIN ======================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="GPT Traffic Analyzer v7.1 — teste e histórico da sua conexão",
        formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument("--duration", type=str, help="Duração (ex.: 60s, 30m, 2h). Default interativo: 60s")
    p.add_argument("--hosts", type=str, help="Hosts extras: 'Nome=host, Nome2=host2'")
    p.add_argument("--ping-alert", type=float, default=80.0, help="Limiar de ping (ms). Default: 80")
    p.add_argument("--headless", action="store_true", help="Modo sem abrir PDF (ideal para CRON)")
    p.add_argument("--output", type=str, default="GPT Traffic Analyzer.pdf", help="Nome do PDF de saída")
    p.add_argument("--fancy", action="store_true", help="Ativa spinner animado na barra geral")
    return p.parse_args()

def main():
    args = parse_args()
    interactive = not any([
        args.duration, args.hosts, args.headless, args.fancy,
        args.output != "GPT Traffic Analyzer.pdf", args.ping_alert != 80.0
    ])

    if interactive:
        duration = human_duration_to_seconds(input("⏱️ Duração (ex.: 60s, 30m, 2h) [60s]: ").strip() or "60s")
        extra_raw = input("🌐 Hosts extras (Nome=host,...). ENTER = nenhum: ").strip()
        ping_alert = float((input("🔴 Limiar de ping p/ alerta [80]: ").strip() or "80").replace(",", "."))
        headless = False
        output = "GPT Traffic Analyzer.pdf"
        fancy = True  # no modo interativo, ativa o spinner por padrão (fica bonito 😎)
    else:
        duration = human_duration_to_seconds(args.duration or "60s")
        extra_raw = args.hosts or ""
        ping_alert = args.ping_alert
        headless = args.headless
        output = args.output
        fancy = args.fancy

    # Sempre incluir Google e Cloudflare
    hosts = {"Google (8.8.8.8)": "8.8.8.8", "Cloudflare (1.1.1.1)": "1.1.1.1"}
    if extra_raw:
        for item in extra_raw.split(","):
            if "=" in item:
                k, v = [x.strip() for x in item.split("=", 1)]
                if k and v:
                    hosts[k] = v

    # Executa
    df, series = run_test(hosts, duration, interval=1.0, fancy=fancy)
    metrics = {n: compute_metrics(vals) for n, vals in series.items()}

    # Nota/diagnóstico (para CSV)
    pings = [m["mean"] for m in metrics.values() if not (m["mean"] is None or math.isnan(m["mean"]))]
    jitters = [m["jitter"] for m in metrics.values() if not (m["jitter"] is None or math.isnan(m["jitter"]))]
    losses = [m["loss_pct"] for m in metrics.values()]
    ping_avg = float(np.nanmean(pings)) if pings else 999.0
    jitter_avg = float(np.nanmean(jitters)) if jitters else 999.0
    loss_avg = float(np.mean(losses)) if losses else 100.0
    overall_score = (0.4 * score_metric_ping(ping_avg) +
                     0.3 * score_metric_jitter(jitter_avg) +
                     0.3 * score_metric_loss(loss_avg))

    # CSV histórico
    test_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat(timespec="seconds")
    append_history_csv(test_id, timestamp, metrics, overall_score)

    # PDF
    build_pdf(output, df, metrics, ping_alert)

    # abrir (se não headless)
    if not headless:
        try:
            if os.name == "nt":
                os.startfile(output)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.run([opener, output], check=False)
        except Exception:
            pass

if __name__ == "__main__":
    main()
