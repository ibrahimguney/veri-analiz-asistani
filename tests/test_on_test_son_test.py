import unittest

import numpy as np
import pandas as pd
from scipy import stats

import analiz as A


class OnTestSonTestTest(unittest.TestCase):
    def test_ornek_veride_esli_puanlar(self):
        for n in (1, 120, 1000):
            for tohum in (0, 42, 99):
                with self.subTest(n=n, tohum=tohum):
                    df = A.ornek_veri(n=n, tohum=tohum)
                    on = df["on_test_puani"]
                    son = df["son_test_puani"]
                    self.assertTrue(pd.api.types.is_numeric_dtype(on))
                    self.assertTrue(pd.api.types.is_numeric_dtype(son))
                    self.assertTrue(on.between(0, 100).all())
                    self.assertTrue(son.between(0, 100).all())
                    if n >= 120:
                        self.assertTrue(5 <= (son - on).mean() <= 8)
                    pd.testing.assert_frame_equal(df, A.ornek_veri(n=n, tohum=tohum))

    def test_ornek_veri_normal_fark_ve_eslestirilmis_t_testi(self):
        df = A.ornek_veri()
        fark = df["son_test_puani"] - df["on_test_puani"]

        self.assertAlmostEqual(fark.mean(), 6, delta=2)
        self.assertAlmostEqual(fark.std(ddof=1), 8, delta=2)
        self.assertTrue((fark < 0).any())
        self.assertEqual(
            A.on_test_son_test(df, "on_test_puani", "son_test_puani")["test"],
            "Eşleştirilmiş t-testi",
        )

    def test_normal_farklarda_eslestirilmis_t_testi(self):
        rng = np.random.default_rng(42)
        on = rng.normal(50, 10, 100)
        fark = rng.normal(3, 2, 100)
        df = pd.DataFrame({"on": on, "son": on + fark})

        sonuc = A.on_test_son_test(df, "on", "son")

        self.assertEqual(sonuc["test"], "Eşleştirilmiş t-testi")
        self.assertAlmostEqual(sonuc["p"], stats.ttest_rel(df["son"], df["on"]).pvalue)
        dz = fark.mean() / fark.std(ddof=1)
        self.assertIn(A.sayi(abs(dz)), sonuc["etki"])
        self.assertTrue(sonuc["anlamli"])
        self.assertIn("ortalama değişim", sonuc["yorum"][1].lower())

    def test_normal_olmayan_farklarda_wilcoxon_ve_sira_etkisi(self):
        fark = np.array([0, 0, -1, -2, 1, 2, 3, 4, 5, 6, 20, 100], dtype=float)
        df = pd.DataFrame({"on": np.arange(len(fark)), "son": np.arange(len(fark)) + fark})

        sonuc = A.on_test_son_test(df, "on", "son")
        siralar = stats.rankdata(abs(fark[fark != 0]))
        nz = fark[fark != 0]
        r = (siralar[nz > 0].sum() - siralar[nz < 0].sum()) / siralar.sum()

        self.assertEqual(sonuc["test"], "Wilcoxon işaretli sıralar testi")
        self.assertAlmostEqual(sonuc["p"], stats.wilcoxon(fark).pvalue)
        self.assertIn(A.sayi(abs(r)), sonuc["etki"])
        self.assertIn("simetrik", " ".join(sonuc["notlar"]))

    def test_eksik_ciftler_ve_sifir_farklar(self):
        df = pd.DataFrame({"on": [1, 2, 3, 4, 5, 6, np.inf],
                           "son": [1, 2, 3, 4, 5, np.nan, 7]})
        sonuc = A.on_test_son_test(df, "on", "son")
        self.assertEqual(sonuc["n"], 5)
        self.assertEqual(sonuc["p"], 1)
        self.assertFalse(sonuc["anlamli"])
        self.assertIn("0,00", sonuc["etki"])
        self.assertIn("2 satır", " ".join(sonuc["notlar"]))
        self.assertIn("normallik değerlendirilemez", " ".join(sonuc["notlar"]))
        self.assertIn("Ölçüm özeti", A.rapor_md(sonuc, 0.05))

    def test_sabit_sifir_olmayan_farklar(self):
        df = pd.DataFrame({"on": range(10), "son": range(1, 11)})
        sonuc = A.on_test_son_test(df, "on", "son")
        self.assertEqual(sonuc["test"], "Wilcoxon işaretli sıralar testi")
        self.assertAlmostEqual(sonuc["p"], stats.wilcoxon(np.ones(10)).pvalue)
        self.assertIn("1,00", sonuc["etki"])

    def test_gecersiz_secimler(self):
        df = pd.DataFrame({"on": [1, 2, 3, 4, 5], "son": [1, 2, 3, 4, np.nan],
                           "metin": ["1"] * 5})
        with self.assertRaisesRegex(ValueError, "farklı"):
            A.on_test_son_test(df, "on", "on")
        with self.assertRaisesRegex(ValueError, "sayısal"):
            A.on_test_son_test(df, "on", "metin")
        with self.assertRaisesRegex(ValueError, "en az 5"):
            A.on_test_son_test(df, "on", "son")


if __name__ == "__main__":
    unittest.main()
