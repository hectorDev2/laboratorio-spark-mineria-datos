#!/usr/bin/env python3
"""Genera el informe técnico del laboratorio a partir de agregados auditables."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from laboratorio_spark.scripts.report_helpers import format_count, format_pct

NAVY = colors.HexColor("#143D59")
TEAL = colors.HexColor("#176B87")
CORAL = colors.HexColor("#E07A5F")
INK = colors.HexColor("#263746")
MUTED = colors.HexColor("#647482")
PALE = colors.HexColor("#F2F6F8")


def register_fonts():
    regular = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    bold = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
    if not regular.exists():
        raise RuntimeError("No se encontró una fuente Unicode compatible")
    pdfmetrics.registerFont(TTFont("LabSans", str(regular)))
    pdfmetrics.registerFont(TTFont("LabSansBold", str(bold if bold.exists() else regular)))


def make_styles():
    base = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle("CoverKicker", parent=base["Normal"], fontName="LabSansBold", fontSize=12, leading=15, textColor=TEAL, spaceAfter=10),
        "cover": ParagraphStyle("Cover", parent=base["Title"], fontName="LabSansBold", fontSize=28, leading=33, textColor=NAVY, spaceAfter=14),
        "cover_sub": ParagraphStyle("CoverSub", parent=base["Normal"], fontName="LabSans", fontSize=14, leading=19, textColor=INK),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="LabSansBold", fontSize=19, leading=23, textColor=NAVY, spaceAfter=10),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="LabSansBold", fontSize=13, leading=16, textColor=TEAL, spaceBefore=7, spaceAfter=5),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="LabSans", fontSize=9.3, leading=13.6, textColor=INK, spaceAfter=7),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="LabSans", fontSize=7.6, leading=10, textColor=MUTED, spaceAfter=5),
        "callout": ParagraphStyle("Callout", parent=base["BodyText"], fontName="LabSans", fontSize=9.3, leading=13.5, textColor=NAVY, backColor=PALE, borderColor=colors.HexColor("#D9E5EA"), borderWidth=.6, borderPadding=8, spaceAfter=9),
        "metric": ParagraphStyle("Metric", parent=base["Normal"], fontName="LabSansBold", fontSize=16, leading=19, textColor=NAVY, alignment=TA_CENTER),
        "metric_label": ParagraphStyle("MetricLabel", parent=base["Normal"], fontName="LabSans", fontSize=7.5, leading=9, textColor=MUTED, alignment=TA_CENTER),
    }


def page_decorator(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 1.02 * cm, width, 1.02 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("LabSansBold", 7.5)
    canvas.drawString(1.55 * cm, height - .66 * cm, "MINERÍA DE DATOS · LABORATORIO SPARK")
    canvas.setFont("LabSans", 7.2)
    canvas.drawRightString(width - 1.55 * cm, height - .66 * cm, "CLÚSTER LOCAL MULTIPROCESO")
    canvas.setStrokeColor(colors.HexColor("#CDD7DE"))
    canvas.line(1.55 * cm, 1.10 * cm, width - 1.55 * cm, 1.10 * cm)
    canvas.setFillColor(MUTED)
    canvas.setFont("LabSans", 7.2)
    canvas.drawString(1.55 * cm, .68 * cm, "Práctica de laboratorio · Informe técnico reproducible")
    canvas.drawRightString(width - 1.55 * cm, .68 * cm, f"Página {doc.page}")
    canvas.restoreState()


def table(rows, widths, font=8):
    out = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    out.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "LabSansBold"),
        ("FONTNAME", (0, 1), (-1, -1), "LabSans"),
        ("FONTSIZE", (0, 0), (-1, -1), font),
        ("LEADING", (0, 0), (-1, -1), font + 2.8),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#CBD6DD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return out


def image(path, width=17.2 * cm, max_height=9.0 * cm):
    img = Image(str(path))
    ratio = min(width / img.imageWidth, max_height / img.imageHeight)
    img.drawWidth = img.imageWidth * ratio
    img.drawHeight = img.imageHeight * ratio
    return img


def metric_cards(items, styles):
    cells = []
    for value, label in items:
        cells.append([Paragraph(value, styles["metric"]), Paragraph(label, styles["metric_label"])])
    t = Table([cells], colWidths=[17.1 * cm / len(cells)] * len(cells))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#D7E2E8")),
        ("INNERGRID", (0, 0), (-1, -1), .5, colors.HexColor("#D7E2E8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def top_district_rows(data, region, n=6):
    items = sorted(data["districts"][region].items(), key=lambda x: x[1]["median_price_m2"], reverse=True)[:n]
    return [[label, format_count(values["count"]), f"S/ {values['median_price_m2']:,.0f}".replace(",", " ")] for label, values in items]


def build_report(root: Path, output: Path):
    register_fonts()
    s = make_styles()
    data = json.loads((root / "resultados/agregados_descriptivos.json").read_text(encoding="utf-8"))
    graph = root / "graficos"
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=1.55 * cm, rightMargin=1.55 * cm,
        topMargin=1.48 * cm, bottomMargin=1.42 * cm,
        title="Práctica de laboratorio — Clúster Spark local multiproceso",
        author="Hector Paolo Barazorda",
    )
    story = []

    # Portada
    story += [
        Spacer(1, 2.25 * cm),
        Paragraph("PRÁCTICA DE LABORATORIO", s["cover_kicker"]),
        Paragraph("Clúster Spark local multiproceso", s["cover"]),
        Paragraph("Análisis del mercado inmobiliario del Perú", s["cover_sub"]),
        Spacer(1, .75 * cm),
        image(graph / "topologia_cluster_local.png", 16.8 * cm, 8.2 * cm),
        Spacer(1, .65 * cm),
        table([
            ["ALUMNO", "Hector Paolo Barazorda"],
            ["CURSO", "Minería de Datos"],
            ["DOCENTE", "Julio Vladimir Quispe Sota"],
            ["UNIVERSIDAD", "Universidad Nacional de San Antonio Abad del Cusco"],
            ["ESCUELA PROFESIONAL", "Ingeniería Informática y de Sistemas"],
        ], [4.8 * cm, 12.2 * cm], 8.5),
        PageBreak(),
    ]

    sur, norte = data["regions"]["Sur"], data["regions"]["Norte"]
    cusco_total = sum(x["count"] for x in data["cusco_initial"].values())
    story += [
        Paragraph("Resumen ejecutivo", s["h1"]),
        Paragraph(
            "Esta práctica diseña un entorno Spark Standalone con procesos independientes en una sola computadora y aplica un flujo reproducible de análisis sobre dos archivos CSV inmobiliarios. La topología conserva los roles de un clúster real —master, driver y tres workers—, pero usa la interfaz loopback para evitar depender de equipos conectados a una red física.", s["body"]),
        metric_cards([
            (format_count(data["rows"]), "REGISTROS TOTALES"),
            ("59", "COLUMNAS DE ORIGEN"),
            (format_count(sur["count"]), "REGISTROS SUR"),
            (format_count(norte["count"]), "REGISTROS NORTE"),
            (format_count(cusco_total), "REGISTROS CUSCO"),
        ], s),
        Spacer(1, .35 * cm),
        Paragraph("Resultados principales", s["h2"]),
        Paragraph(
            f"El Norte alcanza una tasa de compra de <b>{format_pct(norte['purchase_rate'])}</b>, por encima del Sur (<b>{format_pct(sur['purchase_rate'])}</b>). En alquiler ocurre lo contrario: el Sur registra <b>{format_pct(sur['rent_rate'])}</b> y el Norte <b>{format_pct(norte['rent_rate'])}</b>. En Cusco, la tasa de compra desciende desde 46,42 % para ratios de endeudamiento menores a 0,25 hasta 1,25 % para ratios iguales o superiores a 0,50.", s["body"]),
        Paragraph("Alcance de las cifras", s["h2"]),
        Paragraph(
            "Las cifras descriptivas incluidas en este documento fueron obtenidas mediante un recorrido secuencial fila a fila de los dos CSV, sin cargar el conjunto completo en pandas. El paquete incorpora guiones PySpark que reproducen las agregaciones en el clúster local multiproceso. No se presentan tiempos, métricas predictivas ni capturas de interfaces que no hayan sido medidos durante una ejecución real.", s["callout"]),
        Paragraph("Objetivos", s["h2"]),
        Paragraph("1) configurar una arquitectura local con procesos Spark independientes; 2) perfilar las macrorregiones Sur y Norte con una misma función; 3) comparar precios y tasas de cierre; 4) estudiar la decisión de compra o alquiler en Cusco; 5) dejar un protocolo de medición de escalabilidad con 1, 2 y 3 workers.", s["body"]),
        PageBreak(),
    ]

    story += [
        Paragraph("1. Arquitectura del laboratorio", s["h1"]),
        image(graph / "topologia_cluster_local.png", 17.0 * cm, 9.0 * cm),
        Paragraph("Figura 1. Topología lógica del laboratorio. Cada daemon mantiene PID, log, directorio de trabajo y puertos propios.", s["small"]),
        table([
            ["Componente", "Dirección", "Responsabilidad", "Recursos propuestos"],
            ["Master", "127.0.0.1:7077", "Registro de workers y planificación", "Proceso JVM"],
            ["Worker 1", "RPC 7078 · UI 8081", "Executor independiente", "1 core · 768 MiB"],
            ["Worker 2", "RPC 7079 · UI 8082", "Executor independiente", "1 core · 768 MiB"],
            ["Worker 3", "RPC 7080 · UI 8083", "Executor independiente", "1 core · 768 MiB"],
            ["Driver", "Cliente local", "Envía la aplicación al master", "Python + PySpark"],
        ], [3.1 * cm, 4.1 * cm, 5.8 * cm, 4.0 * cm]),
        Spacer(1, .3 * cm),
        Paragraph(
            "La separación por procesos es importante: no se reemplaza Spark por hilos Python ni por un único <i>local[*]</i>. El master administra tres workers Standalone y el driver se conecta con <b>spark://127.0.0.1:7077</b>. El uso exclusivo de loopback evita exponer servicios de Spark fuera del equipo.", s["callout"]),
        PageBreak(),
    ]

    story += [
        Paragraph("2. Dataset y metodología", s["h1"]),
        Paragraph("Los dos archivos contienen 500 000 registros y 59 variables. Cada fila representa la evaluación de un inmueble por parte de un hogar, con atributos del inmueble, entorno, perfil socioeconómico, condiciones financieras, comportamiento de búsqueda y desenlaces de compra o alquiler.", s["body"]),
        table([
            ["Bloque", "Ejemplos", "Uso analítico"],
            ["Ubicación", "departamento, ciudad, distrito", "Macrorregión y comparación territorial"],
            ["Inmueble", "tipo, área, habitaciones, antigüedad", "Oferta y heterogeneidad del producto"],
            ["Precio", "venta, precio/m², alquiler, mantenimiento", "Nivel de mercado y asequibilidad"],
            ["Hogar", "ingreso, ahorros, deudas, score", "Capacidad financiera"],
            ["Decisión", "probabilidades, compra, alquila", "Tasas observadas y objetivos ML"],
        ], [3.1 * cm, 6.4 * cm, 7.5 * cm]),
        Paragraph("Definición de macrorregiones", s["h2"]),
        Paragraph("<b>Sur:</b> Puno, Cusco, Arequipa, Tacna, Moquegua, Apurímac y Ayacucho. <b>Norte:</b> La Libertad, Tumbes, Áncash, San Martín, Amazonas y Cajamarca. Los demás departamentos se clasifican como “Otro” y no participan en la comparación principal.", s["body"]),
        Paragraph("Flujo reproducible", s["h2"]),
        table([
            ["Etapa", "Implementación"],
            ["Carga", "Esquema explícito de 59 columnas; unión por nombre de ambas partes"],
            ["Calidad", "Conteos, nulos, duplicados, estadísticos y distribución categórica"],
            ["EDA", "groupBy, avg y percentile_approx; misma función para Sur y Norte"],
            ["Cusco", "Bucketizer y agregación de siete segmentaciones"],
            ["Modelado", "Pipeline MLlib con indexación, one-hot, escalamiento y regresión logística"],
            ["Gráficos", "Solo tablas agregadas pasan a memoria local para su representación"],
        ], [3.4 * cm, 13.6 * cm]),
        Paragraph("Se evita convertir el DataFrame completo a pandas. Esa frontera técnica es clave: Spark distribuye la preparación y la agregación; la librería gráfica recibe únicamente tablas pequeñas.", s["callout"]),
        PageBreak(),
    ]

    story += [
        Paragraph("3. Análisis exploratorio · Sur", s["h1"]),
        image(graph / "sur_precio_m2_distrito.png", 17.0 * cm, 8.0 * cm),
        Paragraph("Figura 2. Doce distritos del Sur con mayor mediana de precio por m².", s["small"]),
        image(graph / "sur_tasas_tipo_inmueble.png", 17.0 * cm, 7.1 * cm),
        Paragraph("Figura 3. Tasas de compra y alquiler por tipo de inmueble en el Sur.", s["small"]),
        PageBreak(),
        Paragraph("3.1 Lectura del Sur", s["h1"]),
        table([["Distrito", "Registros", "Mediana precio/m²"], *top_district_rows(data, "Sur")], [9.0 * cm, 3.6 * cm, 4.4 * cm]),
        Spacer(1, .3 * cm),
        Paragraph("Yanahuara encabeza el ranking con S/ 5 000 por m², seguida por Wanchaq con S/ 4 917 y Cayma con S/ 4 825. El patrón concentra los precios superiores en distritos urbanos consolidados de Arequipa y Cusco.", s["body"]),
        table([
            ["Tipo", "Registros", "Compra", "Alquiler"],
            *[[k, format_count(v["count"]), format_pct(v["purchase_rate"]), format_pct(v["rent_rate"])] for k, v in sorted(data["types"]["Sur"].items())],
        ], [5.0 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm]),
        Spacer(1, .3 * cm),
        Paragraph("Las casas presentan la mayor tasa de compra del Sur (13,21 %). Los minidepartamentos destacan en alquiler con 51,61 %, más del doble de la tasa regional, lo que sugiere un producto orientado a ocupaciones flexibles o presupuestos acotados.", s["callout"]),
        PageBreak(),
    ]

    story += [
        Paragraph("4. Análisis exploratorio · Norte", s["h1"]),
        image(graph / "norte_precio_m2_distrito.png", 17.0 * cm, 8.0 * cm),
        Paragraph("Figura 4. Doce distritos del Norte con mayor mediana de precio por m²; se mantiene la escala del Sur.", s["small"]),
        image(graph / "norte_tasas_tipo_inmueble.png", 17.0 * cm, 7.1 * cm),
        Paragraph("Figura 5. Tasas de compra y alquiler por tipo de inmueble en el Norte.", s["small"]),
        PageBreak(),
        Paragraph("4.1 Lectura del Norte", s["h1"]),
        table([["Distrito", "Registros", "Mediana precio/m²"], *top_district_rows(data, "Norte")], [9.0 * cm, 3.6 * cm, 4.4 * cm]),
        Spacer(1, .3 * cm),
        Paragraph("Víctor Larco Herrera registra la mayor mediana del Norte, S/ 4 154 por m². Trujillo (Cercado) ocupa el segundo lugar con S/ 3 633. Los valores máximos del Norte son inferiores a los tres primeros del Sur.", s["body"]),
        table([
            ["Tipo", "Registros", "Compra", "Alquiler"],
            *[[k, format_count(v["count"]), format_pct(v["purchase_rate"]), format_pct(v["rent_rate"])] for k, v in sorted(data["types"]["Norte"].items())],
        ], [5.0 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm]),
        Spacer(1, .3 * cm),
        Paragraph("El minidepartamento muestra la tasa de compra más alta (19,81 %) y también la mayor tasa de alquiler (39,19 %). Las casas, que reúnen 55 292 registros, alcanzan 16,26 % de compra y 24,76 % de alquiler.", s["callout"]),
        PageBreak(),
    ]

    story += [
        Paragraph("5. Comparación Sur–Norte", s["h1"]),
        metric_cards([
            (format_pct(sur["purchase_rate"]), "COMPRA SUR"),
            (format_pct(norte["purchase_rate"]), "COMPRA NORTE"),
            (format_pct(sur["rent_rate"]), "ALQUILER SUR"),
            (format_pct(norte["rent_rate"]), "ALQUILER NORTE"),
        ], s),
        Spacer(1, .5 * cm),
        table([
            ["Indicador", "Sur", "Norte", "Diferencia Norte − Sur"],
            ["Registros", format_count(sur["count"]), format_count(norte["count"]), format_count(norte["count"] - sur["count"])],
            ["Tasa de compra", format_pct(sur["purchase_rate"]), format_pct(norte["purchase_rate"]), "+3,42 pp"],
            ["Tasa de alquiler", format_pct(sur["rent_rate"]), format_pct(norte["rent_rate"]), "−4,79 pp"],
        ], [5.2 * cm, 3.8 * cm, 3.8 * cm, 4.2 * cm]),
        Paragraph("Interpretación", s["h2"]),
        Paragraph("El Norte exhibe mayor propensión observada a comprar, mientras que el Sur concentra una mayor propensión a alquilar. La diferencia no debe atribuirse a la ubicación por sí sola: el mix de inmuebles, los ingresos, el endeudamiento y la demanda turística pueden actuar como factores asociados.", s["body"]),
        Paragraph("Comparabilidad", s["h2"]),
        Paragraph("Las tasas se calculan con la misma definición y la misma función de agregación. Los rankings distritales usan mediana, una medida menos sensible a valores extremos que el promedio. Los gráficos de precio comparten escala horizontal, lo que evita exagerar visualmente las diferencias regionales.", s["callout"]),
        Paragraph("Implicancia operativa", s["h2"]),
        Paragraph("Una estrategia comercial diferenciada podría priorizar productos de alquiler en el Sur —especialmente minidepartamentos— y reforzar el embudo de compra en el Norte. Antes de tomar decisiones, corresponde controlar simultáneamente las variables socioeconómicas y financieras mediante el pipeline predictivo.", s["body"]),
        PageBreak(),
    ]

    debt_order = ["< 0.25", "0.25–0.35", "0.35–0.50", ">= 0.50"]
    story += [
        Paragraph("6. Cusco · capacidad financiera y decisión", s["h1"]),
        image(graph / "cusco_tramos_endeudamiento.png", 17.0 * cm, 8.0 * cm),
        Paragraph("Figura 6. Tasas de cierre según el ratio de endeudamiento para compra.", s["small"]),
        table([
            ["Tramo de deuda", "Registros", "Compra", "Alquiler"],
            *[[k, format_count(data["cusco_debt"][k]["count"]), format_pct(data["cusco_debt"][k]["purchase_rate"]), format_pct(data["cusco_debt"][k]["rent_rate"])] for k in debt_order],
        ], [4.7 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm]),
        Spacer(1, .25 * cm),
        Paragraph("La relación es monotónica para compra: al crecer el endeudamiento, cae la tasa observada. El tramo inferior a 0,25 compra en 46,42 % de los casos; el tramo desde 0,50 lo hace en apenas 1,25 %. En alquiler, los tramos intermedios superan 50 %, lo que es consistente con hogares que aún sostienen capacidad mensual pero no condiciones favorables para financiar una compra.", s["callout"]),
        PageBreak(),
        Paragraph("6.1 Cuota inicial y segmentaciones", s["h1"]),
        table([
            ["Cubre cuota inicial", "Registros", "Compra", "Alquiler"],
            ["Sí", format_count(data["cusco_initial"]["1"]["count"]), format_pct(data["cusco_initial"]["1"]["purchase_rate"]), format_pct(data["cusco_initial"]["1"]["rent_rate"])],
            ["No", format_count(data["cusco_initial"]["0"]["count"]), format_pct(data["cusco_initial"]["0"]["purchase_rate"]), format_pct(data["cusco_initial"]["0"]["rent_rate"])],
        ], [5.2 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm]),
        Spacer(1, .35 * cm),
        Paragraph("Cubrir la cuota inicial multiplica fuertemente la tasa observada de compra: 14,88 % frente a 1,84 %. La tasa de alquiler permanece prácticamente estable (32,93 % frente a 33,04 %), lo que distingue una barrera específica de acceso a la propiedad.", s["body"]),
        Paragraph("Segmentaciones reproducibles", s["h2"]),
        Paragraph("El guion PySpark produce tablas separadas por tramo de endeudamiento, cobertura de cuota inicial, situación laboral, tipo de inmueble, motivo de búsqueda, número de integrantes y distrito. Cada tabla informa registros, tasa de compra y tasa de alquiler.", s["body"]),
        Paragraph("Criterio analítico", s["h2"]),
        Paragraph("Los resultados describen asociación, no causalidad. La cuota inicial y el ratio de endeudamiento pueden estar relacionados con ingresos, ahorros, estabilidad laboral y elegibilidad crediticia. Por eso el siguiente paso es estimar modelos multivariados y evaluar su rendimiento fuera de la muestra de entrenamiento.", s["callout"]),
        PageBreak(),
    ]

    story += [
        Paragraph("7. Flujo predictivo con Spark MLlib", s["h1"]),
        table([
            ["Paso", "Compra", "Alquiler"],
            ["Objetivo", "compra", "alquila"],
            ["Partición", "70 % entrenamiento / 30 % prueba · semilla 2026", "Igual protocolo"],
            ["Categóricas", "Situación laboral, inmueble, motivo, distrito, vivienda actual, educación", "Mismas familias"],
            ["Numéricas", "Deuda, cuota inicial, contado, visitas, integrantes, entorno", "Incluye ratio alquiler/ingreso"],
            ["Algoritmo", "Regresión logística regularizada", "Regresión logística regularizada"],
            ["Evaluación", "Área bajo ROC en prueba", "Área bajo ROC en prueba"],
        ], [3.1 * cm, 6.95 * cm, 6.95 * cm]),
        Spacer(1, .35 * cm),
        Paragraph("Prevención de fuga de información", s["h2"]),
        Paragraph("Se excluyen <b>prob_compra</b>, <b>prob_alquiler</b> y el objetivo contrario. Incluir esas columnas inflaría artificialmente el rendimiento porque contienen información directa o derivada del desenlace.", s["callout"]),
        Paragraph("Interpretación", s["h2"]),
        Paragraph("El pipeline reporta los cinco coeficientes de mayor magnitud absoluta y sus odds ratios. Para variables numéricas estandarizadas, el odds ratio representa el cambio por una desviación estándar; para indicadores categóricos, compara la categoría codificada con la referencia. No se informa un AUC hasta ejecutar el entrenamiento y producir el archivo de métricas correspondiente.", s["body"]),
        Paragraph("8. Protocolo de escalabilidad", s["h1"]),
        table([
            ["Escenario", "Workers", "Repeticiones", "Resultado a registrar"],
            ["Base · 500 mil filas", "1, 2 y 3", "1 calentamiento + 3 medidas", "Mediana de segundos"],
            ["Ampliado · 5 millones", "1, 2 y 3", "1 calentamiento + 3 medidas", "Mediana de segundos"],
        ], [5.2 * cm, 3.0 * cm, 4.8 * cm, 4.0 * cm]),
        Paragraph("La medición debe mantener constantes el dataset, la consulta, las particiones y los recursos por worker. Con volúmenes pequeños, el costo de planificación, serialización y coordinación puede neutralizar el paralelismo. Por eso no se afirma aceleración sin observaciones temporales obtenidas bajo el protocolo.", s["body"]),
        PageBreak(),
    ]

    story += [
        Paragraph("9. Reproducibilidad", s["h1"]),
        table([
            ["Orden", "Acción", "Comprobación"],
            ["1", "Instalar Java, Spark y Python; crear entorno", "Versiones registradas"],
            ["2", "Iniciar master y tres workers locales", "Procesos y puertos independientes"],
            ["3", "Ejecutar run_spark_analysis.py", "Conteo 500 000 y 59 columnas de origen"],
            ["4", "Revisar resultados y gráficos", "Agregados coherentes con el JSON base"],
            ["5", "Ejecutar run_scalability.py por escenario", "Tres repeticiones y mediana"],
            ["6", "Regenerar este PDF", "Documento y pruebas sin errores"],
        ], [2.0 * cm, 8.2 * cm, 6.8 * cm]),
        Paragraph("Controles incluidos", s["h2"]),
        Paragraph("Las pruebas unitarias validan la clasificación regional, los límites de tramos de deuda, la unicidad de las 59 columnas, el cálculo de tasas y medianas, y las reglas editoriales del informe. Los gráficos usan un backend no interactivo para funcionar en terminales sin sesión gráfica.", s["body"]),
        Paragraph("Limitaciones", s["h2"]),
        Paragraph("El dataset es de carácter académico y no constituye una fuente oficial del mercado peruano. Los resultados son descriptivos; no establecen causalidad. La arquitectura local permite practicar la coordinación de Spark Standalone, pero todos los procesos comparten CPU, memoria y disco físicos. Las métricas de un despliegue en varias máquinas pueden diferir por red, almacenamiento y heterogeneidad del hardware.", s["callout"]),
        Paragraph("10. Conclusiones", s["h1"]),
        Paragraph("El laboratorio integra arquitectura, ingeniería de datos y análisis en un flujo coherente. La separación del master y tres workers conserva la mecánica operativa de Spark Standalone dentro de una sola Mac. Los agregados muestran perfiles regionales distintos: mayor compra en el Norte y mayor alquiler en el Sur. Cusco evidencia que el endeudamiento y la cobertura de la cuota inicial son señales especialmente relevantes para la decisión de compra.", s["body"]),
        Paragraph("La entrega queda preparada para ejecutar EDA, segmentaciones, modelos MLlib y mediciones controladas sin inventar resultados. El valor pedagógico está en conectar cada conclusión con una transformación reproducible y en distinguir con claridad lo calculado, lo medido y lo que todavía requiere ejecución.", s["body"]),
    ]

    doc.build(story, onFirstPage=page_decorator, onLaterPages=page_decorator)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="laboratorio_spark")
    parser.add_argument("--output", default="laboratorio_spark/informe/Informe_Laboratorio_Spark.pdf")
    args = parser.parse_args()
    build_report(Path(args.root), Path(args.output))
    print(args.output)


if __name__ == "__main__":
    main()
