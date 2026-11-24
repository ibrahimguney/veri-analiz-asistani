"""APA 7 tarzı Word raporları üretme yardımcıları."""
from __future__ import annotations

from datetime import date
from io import BytesIO
import re

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 12,
})
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


def _sayi(deger: float, basamak: int = 2, sifir: bool = True) -> str:
    metin = f"{deger:.{basamak}f}".replace(".", ",")
    if not sifir and abs(deger) < 1:
        metin = metin.replace("0,", ",").replace("-0,", "-,")
    return metin


def _istatistik(s: dict, veri: pd.DataFrame) -> str:
    tur, test, n = s["tur"], s["test"], s["n"]
    p = float(s["p"])
    p_text = "< ,001" if p < 0.001 else f"= {_sayi(p, 3, False)}"
    if tur == "regresyon":
        ozet = s["tablolar"]["Model özeti"].iloc[0]
        parametre = int(ozet["Parametre"])
        df1, df2 = parametre - 1, n - parametre
        fval = float(ozet["F"])
        return (f"F({df1}, {df2}) = {_sayi(fval)}, p {p_text}, "
                f"R² = {_sayi(float(ozet['R²']), 2, False)}")
    if tur == "korelasyon":
        deger = float(re.search(r"=\s*(-?\d+(?:[,.]\d+)?)", s["istatistik"]).group(1).replace(",", "."))
        symbol = "rₛ" if "Spearman" in test else "r"
        return f"{symbol}({n - 2}) = {_sayi(deger, 2, False)}, p {p_text}"
    if tur == "eslestirilmis" and "t-testi" in test:
        tval = float(re.search(r"=\s*(-?\d+(?:[,.]\d+)?)", s["istatistik"]).group(1).replace(",", "."))
        return f"t({n - 1}) = {_sayi(tval)}, p {p_text}, {s['etki']}"
    if tur == "eslestirilmis" and "Wilcoxon" in test:
        return f"{s['istatistik']}, p {p_text}, {s['etki']}"
    if tur == "grup" and "ANOVA" in test:
        k = len(s["tablolar"]["Grup özeti"])
        fval = float(re.search(r"=\s*(-?\d+(?:[,.]\d+)?)", s["istatistik"]).group(1).replace(",", "."))
        eta = re.search(r"η²\s*=\s*([\d,.-]+)", s["etki"])
        eta_text = f", η² = {_sayi(float(eta.group(1).replace(',', '.')), 2, False)}" if eta else ""
        return f"F({k - 1}, {n - k}) = {_sayi(fval)}, p {p_text}{eta_text}"
    if tur == "grup" and "Welch" in test:
        groups = [part.dropna().to_numpy(dtype=float)
                  for _, part in veri.groupby(s["x"], observed=True)[s["y"]]]
        from scipy import stats

        result = stats.ttest_ind(groups[0], groups[1], equal_var=False)
        tval = float(re.search(r"=\s*(-?\d+(?:[,.]\d+)?)", s["istatistik"]).group(1).replace(",", "."))
        return f"t({_sayi(float(result.df))}) = {_sayi(tval)}, p {p_text}, {s['etki']}"
    if tur == "capraz" and "Ki-kare" in test:
        return f"{s['istatistik']}, p {p_text}, {s['etki']}"
    return f"{s['istatistik']}, p {p_text}, {s['etki']}"


def _test_nedeni(s: dict) -> str:
    tur, test = s["tur"], s["test"]
    if tur == "regresyon":
        return ("Sayısal bağımlı değişken ile birden fazla yordayıcının ilişkisini "
                "birlikte değerlendirmek için çoklu doğrusal regresyon (OLS) seçildi.")
    if tur == "grup":
        if "Welch" in test:
            return ("İki bağımsız grubun sayısal ortalamalarını karşılaştırmak için "
                    "Welch t-testi seçildi; bu yöntem eşit varyans varsaymaz.")
        if "Mann-Whitney" in test:
            return ("İki grubun normal dağılmayan sayısal değerlerini karşılaştırmak "
                    "için Mann–Whitney U testi seçildi.")
        if "ANOVA" in test:
            return ("Normal dağılıma uyan üç veya daha fazla grubun ortalamalarını "
                    "karşılaştırmak için tek yönlü ANOVA seçildi.")
        return ("Üç veya daha fazla grupta normallik koşulu sağlanmadığından "
                "Kruskal–Wallis testi seçildi.")
    if tur == "korelasyon":
        return s.get("notlar", ["İki sayısal değişken arasındaki ilişki değerlendirildi."])[0]
    if tur == "eslestirilmis":
        return next((note for note in s.get("notlar", [])
                     if "kullanıldı" in note.lower() or "testi" in note.lower()),
                    "Aynı kişilerin eşleştirilmiş ön ve son ölçümleri karşılaştırıldı.")
    if tur == "capraz":
        return next((note for note in s.get("notlar", [])
                     if "fisher" in note.lower()),
                    "İki kategorik değişken arasındaki ilişkiyi incelemek için ki-kare testi seçildi.")
    return "Değişken türleri ve analiz tasarımına uygun test seçildi."


def _grafik(s: dict, veri: pd.DataFrame) -> BytesIO:
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    tur = s["tur"]
    if tur == "korelasyon":
        x, y = s["x"], s["y"]
        d = veri[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
        ax.scatter(d[x], d[y], alpha=0.65)
        if len(d) >= 2 and d[x].nunique() > 1:
            coef = np.polyfit(d[x], d[y], 1)
            xs = np.linspace(d[x].min(), d[x].max(), 100)
            ax.plot(xs, np.polyval(coef, xs), color="darkorange")
        ax.set(xlabel=x, ylabel=y)
    elif tur == "grup":
        x, y = s["x"], s["y"]
        d = veri[[x, y]].dropna()
        gruplar = [group[y].to_numpy(dtype=float) for _, group in d.groupby(x, observed=True)]
        labels = [str(name) for name, _ in d.groupby(x, observed=True)]
        ax.boxplot(gruplar, showfliers=True)
        ax.set_xticks(range(1, len(labels) + 1), labels)
        ax.set(xlabel=x, ylabel=y)
        ax.tick_params(axis="x", rotation=20)
    elif tur == "capraz":
        x, y = s["x"], s["y"]
        counts = pd.crosstab(veri[x], veri[y])
        counts.plot(kind="bar", ax=ax)
        ax.set(xlabel=x, ylabel="Frekans")
        ax.legend(title=y)
        ax.tick_params(axis="x", rotation=20)
    elif tur == "eslestirilmis":
        x, y = s["x"], s["y"]
        d = veri[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
        positions = [0, 1]
        for row in d.itertuples(index=False, name=None):
            ax.plot(positions, row, color="steelblue", alpha=0.18, linewidth=0.7)
        ax.scatter(positions, [d[x].mean(), d[y].mean()], color="darkorange", zorder=3)
        ax.set_xticks(positions, [x, y])
        ax.set_ylabel("Ölçüm")
    else:
        ax.scatter(s["tahmin"], s["artik"], alpha=0.65)
        ax.axhline(0, color="darkorange", linewidth=1)
        ax.set(xlabel="Tahmin edilen değer", ylabel="Artık")
        ax.set_title("Artıklar ve tahmin edilen değerler")
    fig.tight_layout()
    image = BytesIO()
    fig.savefig(image, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    image.seek(0)
    return image


def _tablo_cizgileri(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "bottom", "insideH"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:color"), "000000")
    for edge in ("left", "right", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "nil")
    for cell in table.rows[0].cells:
        tc_pr = cell._tc.get_or_add_tcPr()
        cell_borders = tc_pr.first_child_found_in("w:tcBorders")
        if cell_borders is None:
            cell_borders = OxmlElement("w:tcBorders")
            tc_pr.append(cell_borders)
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:color"), "000000")
        cell_borders.append(bottom)


def _format_deger(kolon: str, deger) -> str:
    if pd.isna(deger):
        return "—"
    lower = kolon.lower().strip()
    if (lower == "p" or lower.startswith("p ") or lower.endswith(" p")
            or lower.startswith("p (")) and isinstance(deger, (int, float, np.integer, np.floating)):
        return _sayi(float(deger), 3, sifir=False)
    if isinstance(deger, (int, np.integer)) or kolon.lower() in {"n", "gözlem", "frekans", "parametre"}:
        return str(int(deger))
    if isinstance(deger, (float, np.floating)):
        return _sayi(float(deger), 2)
    return str(deger)


def _ekle_tablo(doc: Document, sayi: int, baslik: str, frame: pd.DataFrame) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    p.add_run(f"Tablo {sayi}").bold = True
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    p.add_run(baslik).italic = True
    table = doc.add_table(rows=1, cols=len(frame.columns))
    table.autofit = True
    for i, column in enumerate(frame.columns):
        table.rows[0].cells[i].text = str(column)
    for _, row in frame.iterrows():
        cells = table.add_row().cells
        for i, column in enumerate(frame.columns):
            cells[i].text = _format_deger(str(column), row[column])
    _tablo_cizgileri(table)


def word_raporu(analizler: list[dict], baslik: str, yazar: str,
                dosya_adi: str, gozlem_sayisi: int | str) -> bytes:
    """Analiz sepetini tek bir APA 7 tarzı DOCX raporuna dönüştürür."""
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    for style_name in ("Title", "Heading 1", "Heading 2"):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(12)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(72)
    run = p.add_run(baslik or "Analiz Raporu")
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    doc.add_paragraph(yazar or "Yazar belirtilmedi").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(date.today().strftime("%d.%m.%Y")).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Veri dosyası: {dosya_adi}")
    doc.add_paragraph(f"Gözlem sayısı: {gozlem_sayisi}")
    doc.add_page_break()

    tablo_no = 0
    for index, item in enumerate(analizler, 1):
        s = item["sonuc"]
        data = item["veri"]
        doc.add_heading(item.get("baslik") or f"Analiz {index}: {s['x']} – {s['y']}", level=1)
        doc.add_paragraph(f"Kullanılan test: {s['test']}.")
        doc.add_paragraph("Test seçimi: " + _test_nedeni(s))
        doc.add_paragraph("APA istatistiği: " + _istatistik(s, data))
        doc.add_paragraph(" ".join(s.get("yorum", [])))
        for table_name, frame in s.get("tablolar", {}).items():
            if frame.empty:
                continue
            tablo_no += 1
            _ekle_tablo(doc, tablo_no, table_name, frame)
        doc.add_paragraph("Şekil " + str(index))
        doc.add_picture(_grafik(s, data), width=Inches(6.2))
        doc.add_paragraph()

    output = BytesIO()
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(12)
            run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(12)
                        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
    doc.save(output)
    return output.getvalue()
