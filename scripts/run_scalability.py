#!/usr/bin/env python3
"""Mide una agregación estable con 1, 2 o 3 workers activos."""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pyspark.sql import SparkSession, functions as F

from laboratorio_spark.scripts.run_spark_analysis import explicit_schema


def aggregate(frame):
    return (frame.groupBy("ciudad", "distrito")
            .agg(F.avg("precio_m2_soles").alias("precio_m2_promedio"), F.count("*").alias("registros"))
            .orderBy("ciudad", "distrito"))


def measure(frame, repetitions=3):
    aggregate(frame).collect()
    times = []
    groups = 0
    for _ in range(repetitions):
        started = time.perf_counter()
        groups = len(aggregate(frame).collect())
        times.append(time.perf_counter() - started)
    return {"grupos": groups, "repeticiones_segundos": times, "mediana_segundos": statistics.median(times)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="laboratorio_spark/cluster/data")
    parser.add_argument("--workers", type=int, required=True, choices=(1, 2, 3))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    spark = SparkSession.builder.appName(f"Escalabilidad-{args.workers}-workers").config("spark.sql.shuffle.partitions", "12").getOrCreate()
    reader = spark.read.option("header", True).schema(explicit_schema())
    paths = [str(Path(args.input_dir) / f"dataset_inmobiliario_peru_v2_parte{i}.csv") for i in (1, 2)]
    frame = reader.csv(paths[0]).unionByName(reader.csv(paths[1])).cache()
    rows = frame.count()
    # StatusTracker incluye al driver. Como cada worker ofrece un solo core y el
    # submit fija un core por executor, el resto corresponde uno a uno a workers.
    workers_verified = max(0, len(spark.sparkContext.statusTracker().getExecutorInfos()) - 1)
    if workers_verified != args.workers:
        frame.unpersist()
        spark.stop()
        raise RuntimeError(
            f"El escenario declara {args.workers} worker(s), pero Spark reporta "
            f"{workers_verified} executor(es) activos. Reiniciá con cluster/start.sh {args.workers}."
        )
    result = {
        "workers_activos_verificados": workers_verified,
        "master": spark.sparkContext.master,
        "spark_version": spark.version,
        "filas": rows,
        **measure(frame),
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    frame.unpersist(); spark.stop()


if __name__ == "__main__":
    main()
