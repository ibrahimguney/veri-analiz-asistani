import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan

import analiz as A


class CokluRegresyonTest(unittest.TestCase):
    def test_katsayilar_referans_beta_ve_rapor(self):
        rng = np.random.default_rng(42)
        n = 150
        x = rng.normal(size=n)
        grup = rng.choice(["A", "B", "C"], n)
        y = 10 + 3 * x + 5 * (grup == "B") - 4 * (grup == "C") + rng.normal(size=n)
        df = pd.DataFrame({"puan": y, "x": x, "grup": grup})
        df.loc[0, "x"] = np.nan
        df.loc[1, "puan"] = np.inf
        sonuc = A.coklu_regresyon(df, "puan", ["x", "grup"])
        d = df.iloc[2:]
        X = np.column_stack([np.ones(len(d)), d.x, d.grup == "B", d.grup == "C"])
        model = sm.OLS(d.puan, X).fit()
        katsayi = sonuc["tablolar"]["Katsayılar"]

        self.assertEqual(sonuc["n"], 148)
        self.assertIn("2 satır", " ".join(sonuc["notlar"]))
        self.assertIn("'A'", " ".join(sonuc["notlar"]))
        np.testing.assert_allclose(katsayi["B"], model.params)
        np.testing.assert_allclose(katsayi["Standart hata"], model.bse)
        np.testing.assert_allclose(katsayi["%95 GA alt"], model.conf_int().iloc[:, 0])
        self.assertAlmostEqual(katsayi.loc[1, "Standartlaştırılmış β"],
                               model.params.iloc[1] * d.x.std() / d.puan.std())
        self.assertTrue(pd.isna(katsayi.loc[2, "Standartlaştırılmış β"]))
        self.assertAlmostEqual(sonuc["p"], model.f_pvalue)
        self.assertAlmostEqual(sonuc["shapiro_p"], stats.shapiro(model.resid).pvalue)
        self.assertTrue(any("'B' grubu" in y for y in sonuc["yorum"]))
        self.assertTrue(any("'C' grubu" in y and "düşük" in y for y in sonuc["yorum"]))
        self.assertTrue(any("nedensellik" in y for y in sonuc["yorum"]))
        rapor = A.rapor_md(sonuc, 0.05)
        self.assertIn("Model özeti", rapor)
        self.assertIn("Katsayılar", rapor)
        self.assertIn("referans kategori", rapor)

    def test_degisken_varyans_hc3_ve_yorum(self):
        rng = np.random.default_rng(8)
        x = rng.uniform(0, 10, 500)
        y = 4 + 2 * x + rng.normal(size=len(x)) * (0.1 + x)
        sonuc = A.coklu_regresyon(pd.DataFrame({"x": x, "y": y}), "y", ["x"])
        X = sm.add_constant(x)
        model = sm.OLS(y, X).fit()
        robust = model.get_robustcov_results(cov_type="HC3", use_t=True)
        self.assertAlmostEqual(sonuc["bp_p"], het_breuschpagan(model.resid, X)[1])
        self.assertLess(sonuc["bp_p"], 0.05)
        tablo = sonuc["tablolar"]["HC3 dayanıklı katsayılar"]
        np.testing.assert_allclose(tablo["Standart hata"], robust.bse)
        np.testing.assert_allclose(tablo["p"], robust.pvalues)
        self.assertIn("HC3", " ".join(sonuc["notlar"]))
        self.assertIn("HC3 dayanıklı katsayılar", A.rapor_md(sonuc, 0.05))

    def test_vif_esikleri_ve_gozlem_uyarisi(self):
        rng = np.random.default_rng(5)
        x = rng.normal(size=35)
        z = x + rng.normal(scale=0.25, size=35)
        y = x + rng.normal(size=35)
        sonuc = A.coklu_regresyon(pd.DataFrame({"x": x, "z": z, "y": y}), "y", ["x", "z"])
        self.assertTrue((sonuc["tablolar"]["VIF"]["VIF"] > 10).all())
        self.assertIn("Ciddi uyarı", " ".join(sonuc["notlar"]))
        with patch("analiz.variance_inflation_factor", side_effect=[5.1, 10.0]):
            sonuc = A.coklu_regresyon(pd.DataFrame({"x": x[:25], "z": z[:25], "y": y[:25]}),
                                      "y", ["x", "z"])
        self.assertEqual(list(sonuc["tablolar"]["VIF"]["Durum"]), ["Uyarı", "Uyarı"])
        self.assertIn("10 katından az", " ".join(sonuc["notlar"]))
        sonuc = A.coklu_regresyon(pd.DataFrame({"x": x[:30], "z": z[:30], "y": y[:30]}),
                                  "y", ["x", "z"])
        self.assertNotIn("10 katından az", " ".join(sonuc["notlar"]))

    def test_sirali_kategori_ve_normallik_ihlali(self):
        rng = np.random.default_rng(16)
        x = rng.normal(size=160)
        grup = pd.Categorical(np.tile(["ilk", "ikinci"], 80),
                               categories=["ilk", "ikinci", "kullanılmayan"], ordered=True)
        y = 2 * x + rng.exponential(size=160)
        sonuc = A.coklu_regresyon(pd.DataFrame({"x": x, "y": y, "grup": grup}),
                                  "y", ["x", "grup"])
        self.assertIn("'ilk'", " ".join(sonuc["notlar"]))
        self.assertNotIn("kullanılmayan", " ".join(sonuc["tablolar"]["Katsayılar"]["Değişken"]))
        self.assertLess(sonuc["shapiro_p"], 0.05)
        self.assertIn("normalliği varsayımı ihlal", " ".join(sonuc["notlar"]))

    def test_gecersiz_ve_tam_uyumlu_veri(self):
        df = pd.DataFrame({"x": range(10), "z": np.arange(10) * 2,
                           "y": np.arange(10) * 3, "grup": ["A"] * 10})
        for xs, mesaj in [([], "en az bir"), (["y"], "farklı"),
                          (["x", "z"], "tam doğrusal"), (["grup"], "iki kategori")]:
            with self.subTest(xs=xs), self.assertRaisesRegex(ValueError, mesaj):
                A.coklu_regresyon(df, "y", xs)
        with self.assertRaisesRegex(ValueError, "sayısal"):
            A.coklu_regresyon(df, "grup", ["x"])
        sonuc = A.coklu_regresyon(df, "y", ["x"])
        self.assertIn("değerlendirilemez", " ".join(sonuc["notlar"]))
        self.assertTrue(np.isnan(sonuc["bp_p"]))


if __name__ == "__main__":
    unittest.main()
