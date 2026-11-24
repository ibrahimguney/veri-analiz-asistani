import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import analiz as A


class CokluRegresyonArayuzTest(unittest.TestCase):
    def test_varsayilanlar_sonuc_ve_indirme(self):
        app = AppTest.from_file("../app.py").run()
        self.assertFalse(app.exception)
        self.assertTrue(any(t.label == "📐 Çoklu regresyon" for t in app.tabs))
        y = next(s for s in app.selectbox if s.label == "Bağımlı değişken")
        xs = next(s for s in app.multiselect if s.label == "Bağımsız değişkenler")
        self.assertEqual(y.value, "sinav_puani")
        self.assertEqual(xs.value, ["haftalik_calisma_saati", "yontem", "cinsiyet"])
        self.assertTrue(any(m.label == "Regresyon gözlem sayısı" and m.value == "120"
                            for m in app.metric))
        self.assertTrue(any("referans kategori" in m.value for m in app.markdown))
        self.assertTrue(any("Çoklu regresyon raporunu indir" in b.label
                            for b in app.get("download_button")))
        self.assertGreaterEqual(len(app.get("plotly_chart")), 4)
        xs.set_value(["haftalik_calisma_saati"])
        app.run()
        self.assertFalse(app.exception)
        xs = next(s for s in app.multiselect if s.label == "Bağımsız değişkenler")
        self.assertEqual(xs.value, ["haftalik_calisma_saati"])
        xs.set_value([])
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("en az bir bağımsız değişken" in w.value for w in app.warning))

    def test_eksik_veri_ve_bagimsiz_hata(self):
        df = A.ornek_veri()
        df.loc[0, "yontem"] = None
        with patch.object(A, "ornek_veri", return_value=df):
            app = AppTest.from_file("../app.py").run()
            self.assertFalse(app.exception)
            self.assertTrue(any(m.label == "Regresyon gözlem sayısı" and m.value == "119"
                                for m in app.metric))
            next(s for s in app.selectbox if s.label == "2. değişken").select("yontem")
            app.run()
            self.assertTrue(any(m.label == "Regresyon gözlem sayısı" for m in app.metric))

    def test_bagimli_sayisal_olmali(self):
        df = pd.DataFrame({"a": ["x", "y"] * 5, "b": ["u", "v"] * 5})
        with patch.object(A, "ornek_veri", return_value=df):
            app = AppTest.from_file("../app.py").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("sayısal bir bağımlı değişken" in w.value for w in app.warning))


if __name__ == "__main__":
    unittest.main()
