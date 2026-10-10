"""Funciones puras y agregador por streaming para resultados descriptivos."""

from collections import defaultdict
import statistics

SUR = ("Puno", "Cusco", "Arequipa", "Tacna", "Moquegua", "Apurímac", "Ayacucho")
NORTE = ("La Libertad", "Tumbes", "Áncash", "San Martín", "Amazonas", "Cajamarca")

ALL_COLUMNS = (
    "id_registro", "anio", "mes", "departamento", "ciudad", "distrito", "nivel_zona",
    "inmobiliaria", "reputacion_inmobiliaria", "tipo_inmueble", "estado_inmueble", "area_m2",
    "habitaciones", "banos", "antiguedad_anios", "piso", "ascensor", "estacionamiento",
    "areas_comunes", "distancia_centro_km", "indice_seguridad", "cerca_colegio",
    "indice_demanda_turistica", "cerca_transporte", "precio_venta_soles", "precio_m2_soles",
    "alquiler_mensual_soles", "mantenimiento_mensual_soles", "dias_publicado", "descuento_pct",
    "edad_jefe_hogar", "estado_civil", "num_integrantes", "num_hijos", "nivel_educativo",
    "situacion_laboral", "perceptores_ingreso", "ingreso_familiar_mensual", "ahorros_soles",
    "deudas_mensuales_soles", "score_crediticio", "vivienda_actual", "primera_vivienda",
    "tiene_mascotas", "motivo_busqueda", "tasa_interes_tea_pct", "plazo_credito_anios",
    "cuota_hipotecaria_estimada", "elegible_mivivienda", "cubre_cuota_inicial",
    "puede_pagar_contado", "ratio_endeudamiento_compra", "ratio_alquiler_ingreso",
    "canal_contacto", "num_visitas", "prob_compra", "prob_alquiler", "compra", "alquila",
)


def macroregion(department):
    if department in SUR:
        return "Sur"
    if department in NORTE:
        return "Norte"
    return "Otro"


def debt_bucket(value):
    if value is None:
        return None
    if value < .25:
        return "< 0.25"
    if value < .35:
        return "0.25–0.35"
    if value < .50:
        return "0.35–0.50"
    return ">= 0.50"


def safe_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _counter():
    return {"count": 0, "purchase": 0.0, "rent": 0.0}


class PracticeAggregator:
    """Agrega fila a fila sin materializar el dataset completo en pandas."""

    def __init__(self):
        self.regions = {"Sur": _counter(), "Norte": _counter()}
        self.district_prices = defaultdict(list)
        self.types = defaultdict(_counter)
        self.cusco_debt = defaultdict(_counter)
        self.cusco_initial = defaultdict(_counter)
        self.rows = 0

    @staticmethod
    def _add(counter, row):
        counter["count"] += 1
        counter["purchase"] += safe_float(row.get("compra")) or 0
        counter["rent"] += safe_float(row.get("alquila")) or 0

    def add(self, row):
        self.rows += 1
        region = macroregion(row.get("departamento"))
        if region in self.regions:
            self._add(self.regions[region], row)
            price = safe_float(row.get("precio_m2_soles"))
            label = f'{row.get("departamento", "")} · {row.get("distrito", "")}'
            if price is not None:
                self.district_prices[(region, label)].append(price)
            self._add(self.types[(region, row.get("tipo_inmueble", "Sin dato"))], row)
        if row.get("departamento") == "Cusco":
            bucket = debt_bucket(safe_float(row.get("ratio_endeudamiento_compra")))
            if bucket:
                self._add(self.cusco_debt[bucket], row)
            self._add(self.cusco_initial[row.get("cubre_cuota_inicial", "Sin dato")], row)

    @staticmethod
    def _rates(values):
        count = values["count"]
        return {"count": count, "purchase_rate": values["purchase"] / count if count else 0,
                "rent_rate": values["rent"] / count if count else 0}

    def finalize(self):
        return {
            "rows": self.rows,
            "regions": {k: self._rates(v) for k, v in self.regions.items()},
            "districts": {region: {
                district: {"count": len(values), "median_price_m2": statistics.median(values)}
                for (r, district), values in self.district_prices.items() if r == region
            } for region in ("Sur", "Norte")},
            "types": {region: {
                kind: self._rates(values) for (r, kind), values in self.types.items() if r == region
            } for region in ("Sur", "Norte")},
            "cusco_debt": {k: self._rates(v) for k, v in self.cusco_debt.items()},
            "cusco_initial": {k: self._rates(v) for k, v in self.cusco_initial.items()},
        }
