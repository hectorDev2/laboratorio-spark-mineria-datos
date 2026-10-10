#!/usr/bin/env python3
"""Recorre los CSV y produce agregados descriptivos, gráficos y topología."""

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path

from laboratorio_spark.scripts.analytics import PracticeAggregator

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "laboratorio-spark-mpl"))


def _chart_setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold",
                         "axes.spines.top": False, "axes.spines.right": False})
    return plt


def topology(path):
    plt = _chart_setup()
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    fig, ax = plt.subplots(figsize=(12, 6.2)); fig.patch.set_facecolor("#F4F7FA")
    ax.set_facecolor("#F4F7FA"); ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")
    master = FancyBboxPatch((4.1, 3.85), 3.8, 1.25, boxstyle="round,pad=.08,rounding_size=.12", fc="#143D59", ec="none")
    ax.add_patch(master); ax.text(6, 4.47, "MASTER · 127.0.0.1:7077\nProceso JVM en macOS", ha="center", va="center", color="white", weight="bold", fontsize=12)
    xs = (.55, 4.15, 7.75)
    for idx, x in enumerate(xs, 1):
        box = FancyBboxPatch((x, .68), 3.1, 1.3, boxstyle="round,pad=.08,rounding_size=.12", fc="#176B87", ec="none")
        ax.add_patch(box); ax.text(x+1.55, 1.33, f"WORKER {idx}\n1 core · 768 MiB\n127.0.0.1", ha="center", va="center", color="white", weight="bold", fontsize=11)
        ax.add_patch(FancyArrowPatch((6,3.82),(x+1.55,2.03),arrowstyle="<->",mutation_scale=15,lw=2,color="#E07A5F"))
    ax.text(6,5.72,"Topología del clúster local multiproceso",ha="center",fontsize=20,weight="bold",color="#143D59")
    ax.text(6,5.30,"Una Mac · Spark Standalone 4.2.0 · master + 3 workers",ha="center",fontsize=11,color="#44546A")
    ax.text(6,.18,"Diagrama técnico de procesos y puertos locales",ha="center",fontsize=9,color="#536273")
    path.parent.mkdir(parents=True,exist_ok=True); fig.savefig(path,dpi=180,bbox_inches="tight",facecolor=fig.get_facecolor()); plt.close(fig)


def charts(data, out):
    plt = _chart_setup(); import numpy as np
    out.mkdir(parents=True,exist_ok=True)
    tops={r:sorted(data["districts"][r].items(),key=lambda x:x[1]["median_price_m2"],reverse=True)[:12] for r in ("Sur","Norte")}
    limit=max(v["median_price_m2"] for items in tops.values() for _,v in items)*1.08
    for region,items in tops.items():
        items=list(reversed(items)); fig,ax=plt.subplots(figsize=(11,7))
        ax.barh([x[0] for x in items],[x[1]["median_price_m2"] for x in items],color="#176B87")
        ax.set_xlim(0,limit); ax.set_xlabel("Mediana del precio por m² (S/)"); ax.set_title(f"{region}: distritos con mayor precio por m²"); ax.grid(axis="x",alpha=.22); fig.tight_layout()
        fig.savefig(out/f"{region.lower()}_precio_m2_distrito.png",dpi=180,bbox_inches="tight"); plt.close(fig)
    rate_limit=max(v[k] for r in data["types"].values() for v in r.values() for k in ("purchase_rate","rent_rate"))*112
    for region in ("Sur","Norte"):
        items=sorted(data["types"][region].items()); pos=np.arange(len(items)); width=.38
        fig,ax=plt.subplots(figsize=(10,6)); ax.bar(pos-width/2,[v["purchase_rate"]*100 for _,v in items],width,label="Compra",color="#16857B"); ax.bar(pos+width/2,[v["rent_rate"]*100 for _,v in items],width,label="Alquiler",color="#EC6B56")
        ax.set_xticks(pos,[k for k,_ in items],rotation=15,ha="right"); ax.set_ylim(0,rate_limit); ax.set_ylabel("Tasa (%)"); ax.set_title(f"{region}: cierre por tipo de inmueble"); ax.legend(); ax.grid(axis="y",alpha=.22); fig.tight_layout()
        fig.savefig(out/f"{region.lower()}_tasas_tipo_inmueble.png",dpi=180,bbox_inches="tight"); plt.close(fig)
    order=["< 0.25","0.25–0.35","0.35–0.50",">= 0.50"]; values=[data["cusco_debt"].get(k,{}) for k in order]; pos=np.arange(4); width=.38
    fig,ax=plt.subplots(figsize=(10,6)); ax.bar(pos-width/2,[v.get("purchase_rate",0)*100 for v in values],width,label="Compra",color="#16857B"); ax.bar(pos+width/2,[v.get("rent_rate",0)*100 for v in values],width,label="Alquiler",color="#EC6B56")
    ax.set_xticks(pos,order); ax.set_xlabel("Ratio de endeudamiento para compra"); ax.set_ylabel("Tasa (%)"); ax.set_title("Cusco: cierre por tramo de endeudamiento"); ax.legend(); ax.grid(axis="y",alpha=.22); fig.tight_layout(); fig.savefig(out/"cusco_tramos_endeudamiento.png",dpi=180,bbox_inches="tight"); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--input-dir",default="."); parser.add_argument("--output-dir",default="laboratorio_spark/resultados"); parser.add_argument("--graph-dir",default="laboratorio_spark/graficos"); args=parser.parse_args()
    agg=PracticeAggregator()
    for part in (1,2):
        path=Path(args.input_dir)/f"dataset_inmobiliario_peru_v2_parte{part}.csv"
        with path.open(encoding="utf-8-sig",newline="") as handle:
            for row in csv.DictReader(handle): agg.add(row)
    data=agg.finalize(); result=Path(args.output_dir); result.mkdir(parents=True,exist_ok=True)
    (result/"agregados_descriptivos.json").write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    charts(data,Path(args.graph_dir)); topology(Path(args.graph_dir)/"topologia_cluster_local.png")
    print(f"Filas procesadas: {data['rows']:,}"); print(f"Resultados: {result}")


if __name__=="__main__": main()
