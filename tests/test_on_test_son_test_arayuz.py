import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

import analiz as A


class OnTestSonTestArayuzTest(unittest.TestCase):
    def test_ornek_veride_varsayilan_puanlar(self):
        app = AppTest.from_file("../app.py").run()
        self.assertFalse(app.exception)
        on = next(s for s in app.selectbox if s.label == "Ön test sütunu")
        son = next(s for s in app.selectbox if s.label == "Son test sütunu")
        self.assertEqual(on.value, "on_test_puani")
        self.assertEqual(son.value, "son_test_puani")
        self.assertTrue(any(m.label == "Ölçüm çifti" and m.value == "120" for m in app.metric))

    def test_eksik_varsayilan_sutunlarda_farkli_secimler(self):
        for silinecek in (["on_test_puani"], ["son_test_puani"],
                          ["on_test_puani", "son_test_puani"]):
            with self.subTest(silinecek=silinecek):
                df = A.ornek_veri().drop(columns=silinecek)
                with patch.object(A, "ornek_veri", return_value=df):
                    app = AppTest.from_file("../app.py").run()
                self.assertFalse(app.exception)
                on = next(s for s in app.selectbox if s.label == "Ön test sütunu")
                son = next(s for s in app.selectbox if s.label == "Son test sütunu")
                self.assertNotEqual(on.value, son.value)
                if "on_test_puani" not in silinecek:
                    self.assertEqual(on.value, "on_test_puani")
                if "son_test_puani" not in silinecek:
                    self.assertEqual(son.value, "son_test_puani")

    def test_sayisal_az_kategorili_sutunlar_ve_bagimsiz_hata(self):
        df = A.ornek_veri()
        df["on"] = np.tile([1, 2, 3, 4], 30)
        df["son"] = np.tile([2, 3, 4, 5], 30)
        with patch.object(A, "ornek_veri", return_value=df):
            app = AppTest.from_file("../app.py").run()
            on = next(s for s in app.selectbox if s.label == "Ön test sütunu")
            son = next(s for s in app.selectbox if s.label == "Son test sütunu")
            self.assertIn("on", on.options)
            self.assertNotIn("yontem", on.options)
            on.select("on")
            son.select("son")
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any(m.value == "Wilcoxon işaretli sıralar testi" for m in app.metric))

            next(s for s in app.selectbox if s.label == "2. değişken").select("yontem")
            app.run()
            self.assertTrue(any(m.value == "Wilcoxon işaretli sıralar testi" for m in app.metric))
            self.assertTrue(any("iki farklı değişken" in w.value for w in app.warning))

            next(s for s in app.selectbox if s.label == "Son test sütunu").select("on")
            app.run()
            self.assertTrue(any("iki farklı sütun" in w.value for w in app.warning))

    def test_iki_sayisal_sutun_yoksa_uyari(self):
        df = pd.DataFrame({"grup": ["a", "b"] * 5, "puan": range(10)})
        with patch.object(A, "ornek_veri", return_value=df):
            app = AppTest.from_file("../app.py").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("en az iki sayısal sütun" in w.value for w in app.warning))


if __name__ == "__main__":
    unittest.main()
