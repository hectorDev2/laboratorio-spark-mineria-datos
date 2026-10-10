#!/usr/bin/env python3
"""EDA y modelos MLlib para el clúster Spark Standalone del laboratorio."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "laboratorio-spark-mpl"))
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyspark import StorageLevel
from pyspark.ml import Pipeline
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.feature import Bucketizer, OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler
from pyspark.sql import DataFrame, SparkSession, functions as F, types as T

from laboratorio_spark.scripts.analytics import ALL_COLUMNS, NORTE, SUR

INT_COLUMNS = {
    "id_registro", "anio", "mes", "habitaciones", "banos", "antiguedad_anios",
    "piso", "ascensor", "estacionamiento", "areas_comunes", "cerca_colegio",
    "cerca_transporte", "dias_publicado", "edad_jefe_hogar", "num_integrantes",
    "num_hijos", "perceptores_ingreso", "score_crediticio", "primera_vivienda",
    "tiene_mascotas", "plazo_credito_anios", "elegible_mivivienda",
    "cubre_cuota_inicial", "puede_pagar_contado", "num_visitas", "compra", "alquila",
}
STRING_COLUMNS = {
    "departamento", "ciudad", "distrito", "nivel_zona", "inmobiliaria",
    "tipo_inmueble", "estado_inmueble", "estado_civil",
    "nivel_educativo", "situacion_laboral", "vivienda_actual", "motivo_busqueda",
    "canal_contacto",
}


def explicit_schema():
    fields = []
    for name in ALL_COLUMNS:
        dtype = T.StringType() if name in STRING_COLUMNS else T.IntegerType() if name in INT_COLUMNS else T.DoubleType()
        fields.append(T.StructField(name, dtype, True))
    return T.StructType(fields)


def add_macroregion(df):
    return df.withColumn(
        "macroregion",
        F.when(F.col("departamento").isin(*SUR), "Sur")
        .when(F.col("departamento").isin(*NORTE), "Norte")
        .otherwise("Otro"),
    )


def write_csv(df, path: Path, order_by=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = df.orderBy(*order_by) if order_by else df
    temporary = path.parent / f".{path.stem}_spark"
    if temporary.exists():
        shutil.rmtree(temporary)
    frame.coalesce(1).write.mode("overwrite").option("header", True).csv(str(temporary))
    next(temporary.glob("part-*.csv")).replace(path)
    shutil.rmtree(temporary)


def indicator_table(df, grouping):
    return df.groupBy(*grouping).agg(
        F.count("*").alias("registros"),
        F.percentile_approx("precio_m2_soles", .5, 10000).alias("mediana_precio_m2_soles"),
        F.percentile_approx("alquiler_mensual_soles", .5, 10000).alias("mediana_alquiler_soles"),
        F.percentile_approx("ingreso_familiar_mensual", .5, 10000).alias("mediana_ingreso_soles"),
        F.avg("compra").alias("tasa_compra"),
        F.avg("alquila").alias("tasa_alquiler"),
    )


def eda_region(df, region, output_dir: Path):
    frame = df.filter(F.col("macroregion") == region).persist(StorageLevel.MEMORY_AND_DISK)
    count = frame.count()
    nulls = frame.agg(*[F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c) for c in frame.columns])
    nulls = nulls.select(F.explode(F.array(*[F.struct(F.lit(c).alias("columna"), F.col(c).alias("nulos")) for c in frame.columns])).alias("x")).select("x.*")
    duplicates = frame.groupBy(*ALL_COLUMNS).count().filter("count > 1").agg(F.coalesce(F.sum(F.col("count") - 1), F.lit(0)).alias("filas_duplicadas"))
    districts = indicator_table(frame, ["departamento", "distrito"])
    types = frame.groupBy("tipo_inmueble").agg(F.count("*").alias("registros"), F.avg("compra").alias("tasa_compra"), F.avg("alquila").alias("tasa_alquiler"))
    summary = frame.select("precio_venta_soles", "precio_m2_soles", "alquiler_mensual_soles", "ingreso_familiar_mensual", "ahorros_soles", "score_crediticio").summary()
    slug = region.lower()
    write_csv(nulls, output_dir / slug / "nulos.csv", ["columna"])
    write_csv(duplicates, output_dir / slug / "duplicados.csv")
    write_csv(districts, output_dir / slug / "indicadores_distrito.csv", ["departamento", "distrito"])
    write_csv(types, output_dir / slug / "tasas_tipo_inmueble.csv", ["tipo_inmueble"])
    write_csv(summary, output_dir / slug / "resumen_numerico.csv")
    (output_dir / slug / "conteo_total.json").write_text(json.dumps({"macroregion": region, "registros": count}, indent=2), encoding="utf-8")
    return {"frame": frame, "districts": districts, "types": types}


def plot_regions(results, graph_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    graph_dir.mkdir(parents=True, exist_ok=True)
    district_frames = {region: value["districts"].orderBy(F.desc("mediana_precio_m2_soles")).limit(12).toPandas() for region, value in results.items()}
    ceiling = max(frame["mediana_precio_m2_soles"].max() for frame in district_frames.values()) * 1.08
    for region, frame in district_frames.items():
        frame = frame.sort_values("mediana_precio_m2_soles")
        fig, ax = plt.subplots(figsize=(11, 7))
        ax.barh(frame["departamento"] + " · " + frame["distrito"], frame["mediana_precio_m2_soles"], color="#176B87")
        ax.set_xlim(0, ceiling); ax.set_xlabel("Mediana del precio por m² (S/)"); ax.set_title(f"{region}: distritos con mayor precio por m²"); ax.grid(axis="x", alpha=.22)
        fig.tight_layout(); fig.savefig(graph_dir / f"{region.lower()}_precio_m2_distrito.png", dpi=180, bbox_inches="tight"); plt.close(fig)
    rate_frames = {region: value["types"].toPandas().sort_values("tipo_inmueble") for region, value in results.items()}
    ceiling = max(max(frame["tasa_compra"].max(), frame["tasa_alquiler"].max()) for frame in rate_frames.values()) * 112
    for region, frame in rate_frames.items():
        position = np.arange(len(frame)); width = .38
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(position - width / 2, frame["tasa_compra"] * 100, width, label="Compra", color="#16857B")
        ax.bar(position + width / 2, frame["tasa_alquiler"] * 100, width, label="Alquiler", color="#EC6B56")
        ax.set_xticks(position, frame["tipo_inmueble"], rotation=15, ha="right"); ax.set_ylim(0, ceiling); ax.set_ylabel("Tasa (%)"); ax.set_title(f"{region}: cierre por tipo de inmueble"); ax.legend(); ax.grid(axis="y", alpha=.22)
        fig.tight_layout(); fig.savefig(graph_dir / f"{region.lower()}_tasas_tipo_inmueble.png", dpi=180, bbox_inches="tight"); plt.close(fig)


def cusco_segments(df, output_dir: Path):
    cusco = df.filter(F.col("departamento") == "Cusco").persist(StorageLevel.MEMORY_AND_DISK)
    bucketizer = Bucketizer(splits=[float("-inf"), .25, .35, .50, float("inf")], inputCol="ratio_endeudamiento_compra", outputCol="debt_index", handleInvalid="keep")
    mapping = F.create_map(*sum(([F.lit(float(i)), F.lit(label)] for i, label in enumerate(["< 0.25", "0.25–0.35", "0.35–0.50", ">= 0.50"])), []))
    cusco = bucketizer.transform(cusco).withColumn("tramo_endeudamiento", mapping[F.col("debt_index")])
    for name in ["tramo_endeudamiento", "cubre_cuota_inicial", "situacion_laboral", "tipo_inmueble", "motivo_busqueda", "num_integrantes", "distrito"]:
        values = cusco.groupBy(name).agg(F.count("*").alias("registros"), F.avg("compra").alias("tasa_compra"), F.avg("alquila").alias("tasa_alquiler"))
        write_csv(values, output_dir / "cusco" / f"segmento_{name}.csv", [name])
    return cusco


def train_model(cusco, label, output_dir: Path):
    categorical = ["situacion_laboral", "tipo_inmueble", "motivo_busqueda", "distrito", "vivienda_actual", "nivel_educativo"]
    numeric = ["ratio_endeudamiento_compra", "ratio_alquiler_ingreso", "cubre_cuota_inicial", "puede_pagar_contado", "num_visitas", "num_integrantes", "primera_vivienda", "indice_demanda_turistica", "indice_seguridad", "distancia_centro_km"]
    indexers = [StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep") for c in categorical]
    encoder = OneHotEncoder(inputCols=[f"{c}_idx" for c in categorical], outputCols=[f"{c}_ohe" for c in categorical], handleInvalid="keep", dropLast=True)
    numeric_vector = VectorAssembler(inputCols=numeric, outputCol="numeric_raw", handleInvalid="skip")
    scaler = StandardScaler(inputCol="numeric_raw", outputCol="numeric_scaled", withMean=True, withStd=True)
    vector = VectorAssembler(inputCols=[f"{c}_ohe" for c in categorical] + ["numeric_scaled"], outputCol="features", handleInvalid="skip")
    model = Pipeline(stages=[*indexers, encoder, numeric_vector, scaler, vector, LogisticRegression(labelCol=label, featuresCol="features", maxIter=80, regParam=.01)])
    train, test = cusco.randomSplit([.7, .3], seed=2026)
    fitted = model.fit(train); predictions = fitted.transform(test).cache()
    auc = BinaryClassificationEvaluator(labelCol=label, metricName="areaUnderROC").evaluate(predictions)
    attrs = predictions.schema["features"].metadata.get("ml_attr", {}).get("attrs", {})
    names = [x["name"] for x in sorted((x for group in attrs.values() for x in group), key=lambda x: x["idx"])]
    coefficients = fitted.stages[-1].coefficients.toArray().tolist()
    effects = sorted(zip(names, coefficients), key=lambda item: abs(item[1]), reverse=True)[:5]
    result = {"objetivo": label, "auc_roc": auc, "train_rows": train.count(), "test_rows": test.count(), "top_5": [{"variable": name, "coeficiente": coef, "odds_ratio": math.exp(max(-700, min(700, coef)))} for name, coef in effects]}
    path = output_dir / "cusco" / f"modelo_logistico_{label}.json"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    predictions.unpersist()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="laboratorio_spark/cluster/data")
    parser.add_argument("--output-dir", default="laboratorio_spark/resultados/spark")
    parser.add_argument("--graph-dir", default="laboratorio_spark/graficos/spark")
    parser.add_argument("--skip-ml", action="store_true")
    args = parser.parse_args()

    spark = SparkSession.builder.appName("LaboratorioMineriaInmobiliaria").config("spark.sql.shuffle.partitions", "12").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    reader = spark.read.option("header", True).option("encoding", "UTF-8").schema(explicit_schema())
    paths = [str(Path(args.input_dir) / f"dataset_inmobiliario_peru_v2_parte{i}.csv") for i in (1, 2)]
    df = add_macroregion(reader.csv(paths[0]).unionByName(reader.csv(paths[1]))).persist(StorageLevel.MEMORY_AND_DISK)
    output = Path(args.output_dir); output.mkdir(parents=True, exist_ok=True)
    verification = {"filas": df.count(), "columnas_origen": len(ALL_COLUMNS), "columnas_con_macroregion": len(df.columns), "particiones": df.rdd.getNumPartitions(), "master": spark.sparkContext.master, "spark_version": spark.version}
    (output / "verificacion.json").write_text(json.dumps(verification, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(verification, indent=2, ensure_ascii=False))
    results = {region: eda_region(df, region, output) for region in ("Sur", "Norte")}
    comparison = indicator_table(df.filter(F.col("macroregion").isin("Sur", "Norte")), ["macroregion"])
    write_csv(comparison, output / "comparacion_sur_norte.csv", ["macroregion"])
    plot_regions(results, Path(args.graph_dir))
    cusco = cusco_segments(df, output)
    if not args.skip_ml:
        train_model(cusco, "compra", output); train_model(cusco, "alquila", output)
    for value in results.values(): value["frame"].unpersist()
    cusco.unpersist(); df.unpersist(); spark.stop()


if __name__ == "__main__":
    main()
