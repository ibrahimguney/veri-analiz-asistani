import unittest
from io import BytesIO

import analiz as A
import rapor as R
from docx import Document
from streamlit.testing.v1 import AppTest


class WordRaporuTest(unittest.TestCase):
    def test_rapor_docx_baslik_tablo_gorsel_ve_apa_bicimi(self):
        df = A.ornek_veri()
        sonuc = A.analiz(df, "yontem", "sinav_puani")
        icerik = R.word_raporu(
            [{"sonuc": sonuc, "veri": df[[sonuc["x"], sonuc["y"]]],
              "baslik": "Yöntem ve sınav puanı"}],
            "Öğrenci Başarı Raporu", "Ayşe Örnek", "ogrenci_verisi.csv", len(df),
        )

        belge = Document(BytesIO(icerik))
        paragraflar = [paragraph.text for paragraph in belge.paragraphs]
        self.assertIn("Öğrenci Başarı Raporu", paragraflar)
        self.assertIn("Yöntem ve sınav puanı", paragraflar)
        self.assertIn("Ayşe Örnek", paragraflar)
        self.assertTrue(any("ogrenci_verisi.csv" in text for text in paragraflar))
        self.assertTrue(any("Gözlem sayısı: 120" in text for text in paragraflar))
        self.assertGreaterEqual(len(belge.tables), 1)
        self.assertEqual(len(belge.inline_shapes), 1)
        self.assertTrue(any("APA istatistiği:" in text and "p =" in text for text in paragraflar))

    def test_rapor_tum_analiz_sepetini_ekler(self):
        df = A.ornek_veri()
        sonuc = A.on_test_son_test(df, "on_test_puani", "son_test_puani")
        belge = Document(BytesIO(R.word_raporu(
            [{"sonuc": sonuc, "veri": df[[sonuc["x"], sonuc["y"]]],
              "baslik": "Ön test – son test"}],
            "Rapor", "Yazar", "örnek veri", len(df),
        )))
        self.assertTrue(any("Ön test – son test" in p.text for p in belge.paragraphs))
        self.assertEqual(len(belge.tables), 1)
        self.assertEqual(len(belge.inline_shapes), 1)

    def test_apptest_analizi_sepete_ekler_ve_word_indirmesini_gosterir(self):
        app = AppTest.from_file("../app.py").run()
        self.assertFalse(app.exception)
        next(button for button in app.button if button.label == "➕ Rapora ekle").click()
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["rapor_analizleri"]), 1)
        self.assertTrue(any("Word raporu indir" in button.label
                            for button in app.get("download_button")))


if __name__ == "__main__":
    unittest.main()
