"""Tests for method v4 (CHANGELOG v4). Standard-library unittest; run from the repo root:

    python3 -m unittest discover -s tests -v

Unit tests (1-4) use synthetic rows. Regression tests (5-9) need out/town_pace.csv and out/summary.json
from a v4 build and compare them with the v3.2 snapshot of the same inputs, so they are skipped when the
current outputs come from other data vintages.
"""
import json, math, re, sys, unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import build

V32 = ROOT / "data" / "history" / "town_pace_v3.2_c2026-09_d2026-01.csv"
V32_SUMMARY = {"dca_pace_usable": 0.3828, "census_pace_all": 0.4424}   # v3.2 published figures at these inputs


def row(**kw):
    base = {"matched": True, "prospective_need": 100.0,
            "cw_comparable": False, "dw_comparable": False, "cw_measurable": False, "dw_measurable": False,
            "cw_class": None, "dw_class": None}
    base.update(kw)
    return pd.Series(base)


class T1RatioClass(unittest.TestCase):
    def test_edges(self):
        for r, k in [(0.4999, "well_below"), (0.5, "below"), (0.7999, "below"), (0.8, "about_same"),
                     (1.2499, "about_same"), (1.25, "above"), (1.9999, "above"), (2.0, "well_above"), (0, "well_below")]:
            self.assertEqual(build.ratio_class(r), k, r)
        self.assertIsNone(build.ratio_class(float("nan")))
        self.assertIsNone(build.ratio_class(None))


class T2Combine(unittest.TestCase):
    def c(self, **kw): return build.combine(row(**kw))

    def test_order(self):
        both = dict(cw_comparable=True, dw_comparable=True, cw_measurable=True, dw_measurable=True)
        self.assertEqual(self.c(matched=False, **both, cw_class="below", dw_class="below"), ("no_data", False))
        self.assertEqual(self.c(prospective_need=0.0, **both, cw_class="below", dw_class="below"), ("exempt", False))
        self.assertEqual(self.c(**both, cw_class="above", dw_class="above"), ("above", False))
        # one band apart: the band nearer "about the same", marked
        self.assertEqual(self.c(**both, cw_class="well_below", dw_class="below"), ("below", True))
        self.assertEqual(self.c(**both, cw_class="about_same", dw_class="above"), ("about_same", True))
        self.assertEqual(self.c(**both, cw_class="well_above", dw_class="above"), ("above", True))
        # two or more bands apart
        self.assertEqual(self.c(**both, cw_class="below", dw_class="above"), ("disagree", False))
        self.assertEqual(self.c(**both, cw_class="well_below", dw_class="well_above"), ("disagree", False))
        # one comparable source
        self.assertEqual(self.c(dw_comparable=True, dw_measurable=True, dw_class="well_below", cw_measurable=True),
                         ("well_below", False))
        # measurable but under 10 expected homes on every such source
        self.assertEqual(self.c(cw_measurable=True, dw_measurable=True), ("too_few", False))
        # usable with no baseline, or not usable
        self.assertEqual(self.c(), ("reporting_gap", False))


def mini_frame(base_avg, w_el, units, usable=True):
    """The v4 ratio step on a one-town frame, using the same expressions as build.main."""
    df = pd.DataFrame({"c_base_avg": [base_avg], "cw_units": [units], "cw_usable": [usable]})
    df["c_base_usable"] = df.c_base_avg.notna()
    df["cw_expected"] = (df.c_base_avg * w_el / 12).round(2)
    df["cw_ratio"] = (df.cw_units / df.cw_expected.where(df.cw_expected > 0)).round(4)
    df["cw_measurable"] = (df.cw_usable & df.c_base_usable).astype(bool)
    df["cw_comparable"] = (df.cw_measurable & (df.cw_expected >= build.MIN_EXPECTED)).fillna(False).astype(bool)
    return df.iloc[0]


class T3ExpectedRatio(unittest.TestCase):
    def test_expected(self):
        r = mini_frame(120, 7, 35)
        self.assertAlmostEqual(r.cw_expected, 70.0)
        self.assertAlmostEqual(r.cw_ratio, 0.5)
        self.assertTrue(r.cw_comparable)

    def test_zero_baseline_never_comparable(self):
        r = mini_frame(0.0, 7, 12)
        self.assertTrue(r.cw_measurable)
        self.assertFalse(r.cw_comparable)
        self.assertTrue(math.isnan(r.cw_ratio))

    def test_small_expected(self):
        self.assertFalse(mini_frame(17, 7, 5).cw_comparable)      # 9.92 expected
        self.assertTrue(mini_frame(18, 7, 5).cw_comparable)       # 10.5 expected

    def test_build_uses_same_expressions(self):
        src = (ROOT / "src" / "build.py").read_text()
        self.assertIn('df[f"{s}_base_avg"] * w_el / 12', src)
        self.assertIn('df[f"{w}_expected"] >= MIN_EXPECTED', src)


class T4LargeProducer(unittest.TestCase):
    def flag(self, peak, cw, dw):
        df = pd.DataFrame({"past_peak": [peak], "cw_comparable": [cw], "dw_comparable": [dw], "matched": [True]})
        return bool(((df.past_peak >= build.LARGE_PRODUCER) & ~df.cw_comparable & ~df.dw_comparable & df.matched).iloc[0])

    def test_flag(self):
        self.assertTrue(self.flag(200, False, False))
        self.assertFalse(self.flag(199, False, False))
        self.assertFalse(self.flag(500, True, False))
        self.assertFalse(self.flag(500, False, True))


def outputs():
    t, s = ROOT / "out" / "town_pace.csv", ROOT / "out" / "summary.json"
    if not (t.exists() and s.exists() and V32.exists()): return None
    summary = json.loads(s.read_text())
    if summary.get("method") != "v4" or (summary["vintage"], summary["dca_vintage"]) != ("2026-09", "2026-01"):
        return None
    return pd.read_csv(t, dtype={"fips": str}).set_index("fips"), summary


@unittest.skipIf(outputs() is None, "needs a v4 build at Census 2026-09 / state 2026-01")
class TRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, cls.s = outputs()
        cls.old = pd.read_csv(V32, dtype={"fips": str}).set_index("fips")

    def test5_shared_columns_unchanged(self):
        cols = ["cw_units", "dw_units", "cw_months", "dw_months", "cw_usable", "dw_usable", "dw_zero_unconfirmed",
                "c_base_avg", "d_base_avg", "c_units", "d_units", "c_usable", "d_usable",
                "co_reported_since_jul2025", "co_2015_2024", "completion_ratio_2015_2024", "pipeline_2024_2025",
                "c_best_year", "d_best_year", "prospective_need"]
        for c in cols:
            pd.testing.assert_series_equal(self.df[c], self.old.loc[self.df.index, c], check_names=False, obj=c)

    def test6_sensitivity_equals_old_pace(self):
        self.assertEqual(self.s["sens_affordable_dca"], V32_SUMMARY["dca_pace_usable"])
        self.assertEqual(self.s["sens_affordable_census"], V32_SUMMARY["census_pace_all"])

    def test7_counts_and_coverage(self):
        self.assertEqual(sum(self.s["class_counts"].values()) + int((~self.df.matched).sum()), 564)
        self.assertEqual(len(self.df), 564)
        for k in ("cov_dca", "cov_census"):
            self.assertGreaterEqual(self.s["cov_any"], self.s[k])
            self.assertGreaterEqual(self.s[k], self.s["cov_both"])

    def test8_jersey_city(self):
        jc = self.df[self.df.municipality.str.fullmatch(r"Jersey City( city)?", case=False)]
        self.assertEqual(len(jc), 1)
        jc = jc.iloc[0]
        self.assertEqual(jc.class_live, "exempt")
        self.assertTrue(jc.gap_large_producer)
        self.assertIn(jc.municipality, self.s["gap_large_names"])

    def test9_removed_keys_and_set_aside(self):
        for k in self.s:
            self.assertNotRegex(k, r"_pace_|below_half|too_early|colored_small_window_target|base_class_counts|_best_")
        self.assertFalse(any(c.endswith("_pace") or c.endswith("_best_20") or c.endswith("_best_100") or c == "class_base"
                             for c in self.df.columns))
        src = (ROOT / "src" / "build.py").read_text()
        uses = [l for l in src.splitlines() if "SET_ASIDE" in l and not l.lstrip().startswith("#")]
        for l in uses:
            self.assertTrue("SET_ASIDE =" in l or "_aff_sens" in l or "own_period" in l or "units * SET_ASIDE" in l
                            or "obligation_sensitivity" in l or "* SET_ASIDE /" in l, l)


if __name__ == "__main__":
    unittest.main()
