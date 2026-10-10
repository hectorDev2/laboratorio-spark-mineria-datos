import unittest

from laboratorio_spark.scripts.analytics import ALL_COLUMNS, PracticeAggregator, debt_bucket, macroregion


def sample(**values):
    row = {
        "departamento": "Cusco", "distrito": "Wanchaq", "tipo_inmueble": "Casa",
        "precio_m2_soles": "4000", "compra": "1", "alquila": "0",
        "ratio_endeudamiento_compra": "0.25", "cubre_cuota_inicial": "1",
    }
    row.update(values)
    return row


class MappingTests(unittest.TestCase):
    def test_accented_departments(self):
        self.assertEqual(macroregion("Apurímac"), "Sur")
        self.assertEqual(macroregion("Áncash"), "Norte")
        self.assertEqual(macroregion("San Martín"), "Norte")

    def test_debt_boundaries(self):
        self.assertEqual(debt_bucket(0.249), "< 0.25")
        self.assertEqual(debt_bucket(0.25), "0.25–0.35")
        self.assertEqual(debt_bucket(0.35), "0.35–0.50")
        self.assertEqual(debt_bucket(0.50), ">= 0.50")

    def test_schema_has_59_unique_names(self):
        self.assertEqual(len(ALL_COLUMNS), 59)
        self.assertEqual(len(set(ALL_COLUMNS)), 59)


class AggregatorTests(unittest.TestCase):
    def test_region_rates_and_median(self):
        agg = PracticeAggregator()
        agg.add(sample())
        agg.add(sample(compra="0", alquila="1", precio_m2_soles="6000"))
        out = agg.finalize()
        self.assertEqual(out["regions"]["Sur"]["count"], 2)
        self.assertEqual(out["regions"]["Sur"]["purchase_rate"], 0.5)
        self.assertEqual(out["districts"]["Sur"]["Cusco · Wanchaq"]["median_price_m2"], 5000)

    def test_outside_regions_is_not_aggregated(self):
        agg = PracticeAggregator(); agg.add(sample(departamento="Lima")); out = agg.finalize()
        self.assertEqual(out["regions"]["Sur"]["count"], 0)
        self.assertEqual(out["regions"]["Norte"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
