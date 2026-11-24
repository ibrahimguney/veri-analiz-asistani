"""İstatistiksel analiz fonksiyonları.

Bu modül arayüzden (Streamlit) bağımsızdır; Colab'da veya başka bir
projede de doğrudan içe aktarılıp kullanılabilir:

    import analiz as A
    df = A.ornek_veri()
    sonuc = A.analiz(df, "yontem", "sinav_puani")
    print(sonuc["yorum"])
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------- yardımcılar
def sayi(x, basamak: int = 2) -> str:
    """Sayıyı Türkçe ondalık virgülüyle yazar."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{x:.{basamak}f}".replace(".", ",")


def p_yaz(p: float) -> str:
    return "p < 0,001" if p < 0.001 else f"p = {sayi(p, 3)}"


def dosya_oku(ad: str, icerik: bytes) -> pd.DataFrame:
    """CSV veya Excel okur. Türkçe Excel'den çıkan ';' ayırıcı ve
    ondalık virgül biçimini otomatik tanır."""
    if ad.lower().endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(icerik))

    metin = None
    for kod in ("utf-8-sig", "cp1254"):
        try:
            metin = icerik.decode(kod)
            break
        except UnicodeDecodeError:
            continue
    if metin is None:
        metin = icerik.decode("latin-1")

    ornek = metin[:5000]
    ayirici = max([";", ",", "\t"], key=ornek.count)
    ondalik = "," if ayirici == ";" else "."
    return pd.read_csv(io.StringIO(metin), sep=ayirici, decimal=ondalik)


def degisken_turu(s: pd.Series) -> str:
    """Sayısal sütunlardan az sayıda farklı değeri olanlar (ör. 0/1 kodlama,
    1-5 Likert) kategorik kabul edilir."""
    s = s.dropna()
    if pd.api.types.is_numeric_dtype(s) and s.nunique() > 6:
        return "sayısal"
    return "kategorik"


def normal_mi(x, alfa: float = 0.05) -> bool:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 3 or np.ptp(x) == 0:
        return False
    if len(x) > 5000:
        return stats.normaltest(x).pvalue > alfa
    return stats.shapiro(x).pvalue > alfa


def _buyukluk_r(r: float) -> str:
    r = abs(r)
    if r < 0.1:
        return "çok küçük"
    if r < 0.3:
        return "küçük"
    if r < 0.5:
        return "orta"
    return "büyük"


def _buyukluk_d(d: float) -> str:
    d = abs(d)
    if d < 0.2:
        return "çok küçük"
    if d < 0.5:
        return "küçük"
    if d < 0.8:
        return "orta"
    return "büyük"


def _buyukluk_eta(e: float) -> str:
    if e < 0.01:
        return "çok küçük"
    if e < 0.06:
        return "küçük"
    if e < 0.14:
        return "orta"
    return "büyük"


# ---------------------------------------------------------------- örnek veri
def ornek_veri(n: int = 120, tohum: int = 42) -> pd.DataFrame:
    """Öğretim yöntemleri ve ön test–son test ölçümleri içeren kurgusal veri."""
    rng = np.random.default_rng(tohum)
    yontem = rng.choice(["Geleneksel", "Proje tabanlı", "Ters yüz"], n)
    cinsiyet = rng.choice(["Kız", "Erkek"], n)
    calisma = rng.gamma(4, 1.5, n).round(1)
    etki = pd.Series(yontem).map(
        {"Geleneksel": 0, "Proje tabanlı": 7, "Ters yüz": 12}
    ).to_numpy()
    puan = np.clip(45 + 3 * calisma + etki + rng.normal(0, 10, n), 0, 100).round()
    memnuniyet = rng.integers(1, 6, n)
    on_test = np.clip(rng.normal(55, 12, n), 0, 92).round(1)
    fark = rng.normal(6, 8, n).round(1)
    aykiri = np.abs(fark) >= 100
    while aykiri.any():
        fark[aykiri] = rng.normal(6, 8, aykiri.sum()).round(1)
        aykiri = np.abs(fark) >= 100
    alt_sinir = np.ceil(np.maximum(0, -fark) * 10) / 10
    ust_sinir = np.floor(np.minimum(100, 100 - fark) * 10) / 10
    on_test = np.clip(on_test, alt_sinir, ust_sinir)
    son_test = (on_test + fark).round(1)
    return pd.DataFrame(
        {
            "ogrenci_no": np.arange(1001, 1001 + n),
            "cinsiyet": cinsiyet,
            "yontem": yontem,
            "haftalik_calisma_saati": calisma,
            "sinav_puani": puan,
            "durum": np.where(puan >= 70, "Geçti", "Kaldı"),
            "memnuniyet_1_5": memnuniyet,
            "on_test_puani": on_test,
            "son_test_puani": son_test,
        }
    )


# ---------------------------------------------------------------- betimsel
def betimsel(df: pd.DataFrame) -> pd.DataFrame:
    satirlar = []
    for c in df.columns:
        if degisken_turu(df[c]) != "sayısal":
            continue
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        satirlar.append(
            {
                "Değişken": c,
                "n": len(s),
                "Ortalama": s.mean(),
                "Std. sapma": s.std(),
                "En küçük": s.min(),
                "Medyan": s.median(),
                "En büyük": s.max(),
                "Çarpıklık": s.skew(),
                "Eksik": int(df[c].isna().sum()),
            }
        )
    return pd.DataFrame(satirlar)


def frekans(df: pd.DataFrame, sutun: str) -> pd.DataFrame:
    f = df[sutun].value_counts(dropna=False)
    return pd.DataFrame(
        {"Kategori": f.index.astype(str), "Frekans": f.values,
         "Yüzde": (f.values / f.values.sum() * 100).round(1)}
    )


# ---------------------------------------------------------------- analiz
def analiz(df: pd.DataFrame, x: str, y: str, alfa: float = 0.05) -> dict:
    """İki değişkenin türüne göre uygun testi seçer ve yorumlar.

    sayısal × sayısal   → Pearson / Spearman korelasyonu
    kategorik × sayısal → t-testi / Mann-Whitney / ANOVA / Kruskal-Wallis
    kategorik × kategorik → Ki-kare (gerekirse Fisher)
    """
    if x == y:
        raise ValueError("Lütfen iki farklı değişken seçin.")
    tx, ty = degisken_turu(df[x]), degisken_turu(df[y])
    if tx == ty == "sayısal":
        return _korelasyon(df, x, y, alfa)
    if tx == ty == "kategorik":
        return _ki_kare(df, x, y, alfa)
    grup, sayisal = (x, y) if tx == "kategorik" else (y, x)
    return _grup_karsilastirma(df, grup, sayisal, alfa)


def on_test_son_test(df: pd.DataFrame, on: str, son: str, alfa: float = 0.05) -> dict:
    """Aynı satırdaki ön ve son ölçümleri, farkların dağılımına göre karşılaştırır."""
    if on == son:
        raise ValueError("Lütfen iki farklı sütun seçin.")
    if not all(pd.api.types.is_numeric_dtype(df[c]) and
               not pd.api.types.is_bool_dtype(df[c]) for c in (on, son)):
        raise ValueError("Ön test ve son test sütunları sayısal olmalı.")

    d = df[[on, son]].replace([np.inf, -np.inf], np.nan).dropna()
    n = len(d)
    if n < 5:
        raise ValueError("Bu analiz için en az 5 geçerli ölçüm çifti gerekli.")
    fark = d[son].to_numpy(dtype=float) - d[on].to_numpy(dtype=float)
    if not np.isfinite(fark).all():
        raise ValueError("Ölçüm farkları hesaplanamadı; değerlerin büyüklüğünü kontrol edin.")

    notlar = ["Farklar son test eksi ön test olarak hesaplandı; aynı satırdaki ölçümler eşleştirildi."]
    if len(df) != n:
        notlar.append(f"Eksik veya sonlu olmayan değer içeren {len(df) - n} satır analizden çıkarıldı.")
    if normal_mi(fark, alfa):
        t, p = stats.ttest_1samp(fark, 0)
        dz = fark.mean() / fark.std(ddof=1)
        test = "Eşleştirilmiş t-testi"
        ist = f"t({n - 1}) = {sayi(t)}"
        etki = f"Cohen's dᶻ = {sayi(abs(dz))} ({_buyukluk_d(dz)})"
        notlar.append("Ölçüm farkları normal dağılıma uyduğu için eşleştirilmiş t-testi kullanıldı.")
        notlar.append("Cohen's dᶻ, ortalama farkın farkların standart sapmasına bölümüdür.")
    else:
        sifir_olmayan = fark[fark != 0]
        if len(sifir_olmayan):
            w, p = stats.wilcoxon(fark, alternative="two-sided")
            siralar = stats.rankdata(abs(sifir_olmayan))
            r = (siralar[sifir_olmayan > 0].sum() -
                 siralar[sifir_olmayan < 0].sum()) / siralar.sum()
        else:
            w, p, r = 0.0, 1.0, 0.0
        test = "Wilcoxon işaretli sıralar testi"
        ist = f"W = {sayi(w, 1)}"
        etki = f"Sıra-çift serili r = {sayi(abs(r))} ({_buyukluk_r(r)})"
        if np.ptp(fark) == 0:
            notlar.append("Farklar sabit olduğundan normallik değerlendirilemez; Wilcoxon yöntemi kullanıldı.")
        else:
            notlar.append("Ölçüm farkları normal dağılıma uymadığı için Wilcoxon testi kullanıldı.")
        notlar.append("Sıra-çift serili r, sıfır olmayan farkların pozitif ve negatif sıra toplamlarından hesaplandı.")
        notlar.append("Wilcoxon testi farkların sıfır çevresinde simetrik olduğunu varsayar.")
        if not len(sifir_olmayan):
            notlar.append("Tüm farklar sıfır olduğu için test istatistiği 0 ve p değeri 1 olarak gösterildi.")

    anlamli = p < alfa
    durum = "anlamlı bir fark var" if anlamli else "anlamlı bir fark bulunmadı"
    yorum = [
        f"'{on}' ile '{son}' ölçümleri arasında istatistiksel olarak {durum} "
        f"({ist}, {p_yaz(p)}).",
        f"Ortalama değişim (son test − ön test) {sayi(fark.mean())}; "
        f"medyan değişim {sayi(np.median(fark))}.",
    ]
    ozet = pd.DataFrame({
        "Ölçüm": ["Ön test", "Son test"],
        "Değişken": [on, son],
        "n": [n, n],
        "Ortalama": [d[on].mean(), d[son].mean()],
        "Std. sapma": [d[on].std(), d[son].std()],
        "Medyan": [d[on].median(), d[son].median()],
    })
    return {
        "tur": "eslestirilmis", "test": test, "n": n, "istatistik": ist,
        "p": p, "anlamli": anlamli, "etki": etki, "yorum": yorum,
        "notlar": notlar, "tablolar": {"Ölçüm özeti": ozet}, "x": on, "y": son,
    }


def _korelasyon(df, x, y, alfa):
    d = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(d)
    if n < 5:
        raise ValueError("Bu analiz için en az 5 tam gözlem gerekli.")
    normal = normal_mi(d[x], alfa) and normal_mi(d[y], alfa)
    if normal:
        r, p = stats.pearsonr(d[x], d[y])
        ad, sembol = "Pearson korelasyonu", "r"
        neden = "İki değişken de normal dağılıma uyduğu için Pearson korelasyonu kullanıldı."
    else:
        r, p = stats.spearmanr(d[x], d[y])
        ad, sembol = "Spearman sıra korelasyonu", "rₛ"
        neden = ("Değişkenlerden en az biri normal dağılmadığı için (Shapiro-Wilk) "
                 "parametrik olmayan Spearman korelasyonu kullanıldı.")
    anlamli = p < alfa
    guc = _buyukluk_r(r)
    yon = "pozitif" if r > 0 else "negatif"
    if anlamli:
        yorum = [
            f"'{x}' ile '{y}' arasında {guc} düzeyde, {yon} yönlü ve istatistiksel "
            f"olarak anlamlı bir ilişki var ({sembol} = {sayi(r)}, {p_yaz(p)}).",
            f"Yani '{x}' arttıkça '{y}' "
            + ("de artma eğiliminde." if r > 0 else "azalma eğiliminde."),
            "Not: Korelasyon nedensellik göstermez.",
        ]
    else:
        yorum = [
            f"'{x}' ile '{y}' arasında istatistiksel olarak anlamlı bir ilişki "
            f"bulunmadı ({sembol} = {sayi(r)}, {p_yaz(p)})."
        ]
    return {
        "tur": "korelasyon", "test": ad, "n": n,
        "istatistik": f"{sembol} = {sayi(r)}", "p": p, "anlamli": anlamli,
        "etki": f"{sembol} = {sayi(r)} ({guc})", "yorum": yorum,
        "notlar": [neden], "tablolar": {}, "x": x, "y": y,
    }


def _grup_karsilastirma(df, grup, sayisal, alfa):
    d = df[[grup, sayisal]].copy()
    d[sayisal] = pd.to_numeric(d[sayisal], errors="coerce")
    d = d.dropna()
    d[grup] = d[grup].astype(str)
    gruplar = {k: v[sayisal].to_numpy() for k, v in d.groupby(grup)}
    atilan = [k for k, v in gruplar.items() if len(v) < 2]
    gruplar = {k: v for k, v in gruplar.items() if len(v) >= 2}
    if len(gruplar) < 2:
        raise ValueError("Karşılaştırma için en az 2 gözlemli en az iki grup gerekli.")
    if len(gruplar) > 15:
        raise ValueError(f"'{grup}' değişkeninde çok fazla grup var ({len(gruplar)}). "
                         "Grup değişkeni olarak daha az kategorili bir sütun seçin.")
    d = d[d[grup].isin(gruplar)]
    n = len(d)

    ozet = (d.groupby(grup)[sayisal]
              .agg(n="count", Ortalama="mean", **{"Std. sapma": "std"}, Medyan="median")
              .sort_values("Ortalama", ascending=False)
              .reset_index().rename(columns={grup: "Grup"}))

    normal = all(normal_mi(v, alfa) for v in gruplar.values())
    k = len(gruplar)
    notlar, tablolar = [], {"Grup özeti": ozet}
    if atilan:
        notlar.append(f"Tek gözlemli gruplar analizden çıkarıldı: {', '.join(atilan)}.")
    normal_notu = ("Tüm gruplar normal dağılıma uyduğu için parametrik test kullanıldı."
                   if normal else
                   "En az bir grup normal dağılmadığı için (Shapiro-Wilk) parametrik "
                   "olmayan test kullanıldı.")
    notlar.insert(0, normal_notu)

    adlar = list(gruplar)
    if k == 2:
        a, b = gruplar[adlar[0]], gruplar[adlar[1]]
        if normal:
            t, p = stats.ttest_ind(a, b, equal_var=False)
            ss = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                         / (len(a) + len(b) - 2))
            cd = (a.mean() - b.mean()) / ss if ss > 0 else 0.0
            test = "Bağımsız örneklem t-testi (Welch)"
            ist = f"t = {sayi(t)}"
            etki = f"Cohen's d = {sayi(abs(cd))} ({_buyukluk_d(cd)})"
            notlar.append("Welch düzeltmesi, grup varyanslarının eşit olmasını gerektirmez.")
        else:
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            rb = 2 * u / (len(a) * len(b)) - 1
            test = "Mann-Whitney U testi"
            ist = f"U = {sayi(u, 1)}"
            etki = f"Sıra-çift serili r = {sayi(abs(rb))} ({_buyukluk_r(rb)})"
    else:
        if normal:
            f, p = stats.f_oneway(*gruplar.values())
            tum = d[sayisal].to_numpy()
            ss_ara = sum(len(v) * (v.mean() - tum.mean()) ** 2 for v in gruplar.values())
            ss_top = ((tum - tum.mean()) ** 2).sum()
            eta = ss_ara / ss_top if ss_top > 0 else 0.0
            test = "Tek yönlü varyans analizi (ANOVA)"
            ist = f"F = {sayi(f)}"
            etki = f"η² = {sayi(eta, 3)} ({_buyukluk_eta(eta)})"
        else:
            h, p = stats.kruskal(*gruplar.values())
            eps = h / (n - 1)
            test = "Kruskal-Wallis H testi"
            ist = f"H = {sayi(h)}"
            etki = f"ε² = {sayi(eps, 3)} ({_buyukluk_eta(eps)})"

    anlamli = p < alfa
    en_yuksek, en_dusuk = ozet.iloc[0], ozet.iloc[-1]
    if anlamli:
        yorum = [
            f"'{grup}' gruplarına göre '{sayisal}' değerleri arasında istatistiksel "
            f"olarak anlamlı bir fark var ({ist}, {p_yaz(p)}).",
            f"En yüksek ortalama '{en_yuksek['Grup']}' grubunda ({sayi(en_yuksek['Ortalama'])}), "
            f"en düşük ortalama '{en_dusuk['Grup']}' grubunda ({sayi(en_dusuk['Ortalama'])}).",
            f"Etki büyüklüğü: {etki}.",
        ]
        if k > 2:
            tablolar["İkili karşılaştırmalar"] = _ikili(gruplar, normal)
            yorum.append("Hangi grupların birbirinden farklı olduğu aşağıdaki ikili "
                         "karşılaştırma tablosunda görülebilir.")
    else:
        yorum = [
            f"'{grup}' gruplarına göre '{sayisal}' değerleri arasında istatistiksel "
            f"olarak anlamlı bir fark bulunmadı ({ist}, {p_yaz(p)}).",
            "Gözlenen ortalama farkları rastlantısal olabilir.",
        ]
    return {
        "tur": "grup", "test": test, "n": n, "istatistik": ist, "p": p,
        "anlamli": anlamli, "etki": etki, "yorum": yorum, "notlar": notlar,
        "tablolar": tablolar, "x": grup, "y": sayisal,
    }


def _ikili(gruplar: dict, normal: bool) -> pd.DataFrame:
    adlar = list(gruplar)
    satirlar = []
    if normal:
        sonuc = stats.tukey_hsd(*gruplar.values())
        for i in range(len(adlar)):
            for j in range(i + 1, len(adlar)):
                satirlar.append({
                    "Grup 1": adlar[i], "Grup 2": adlar[j],
                    "Ortalama farkı": gruplar[adlar[i]].mean() - gruplar[adlar[j]].mean(),
                    "p (Tukey)": sonuc.pvalue[i, j],
                })
    else:
        m = len(adlar) * (len(adlar) - 1) / 2
        for i in range(len(adlar)):
            for j in range(i + 1, len(adlar)):
                p = stats.mannwhitneyu(gruplar[adlar[i]], gruplar[adlar[j]],
                                       alternative="two-sided").pvalue
                satirlar.append({
                    "Grup 1": adlar[i], "Grup 2": adlar[j],
                    "Medyan farkı": np.median(gruplar[adlar[i]]) - np.median(gruplar[adlar[j]]),
                    "p (Bonferroni)": min(1.0, p * m),
                })
    return pd.DataFrame(satirlar)


def _ki_kare(df, x, y, alfa):
    d = df[[x, y]].dropna().astype(str)
    tablo = pd.crosstab(d[x], d[y])
    if tablo.shape[0] < 2 or tablo.shape[1] < 2:
        raise ValueError("Her iki değişkende de en az iki kategori olmalı.")
    if tablo.shape[0] > 20 or tablo.shape[1] > 20:
        raise ValueError("Kategori sayısı çok fazla (20'den fazla). Daha az kategorili "
                         "değişkenler seçin.")
    n = int(tablo.values.sum())
    chi2, p, sd, beklenen = stats.chi2_contingency(tablo)
    v = np.sqrt(chi2 / (n * (min(tablo.shape) - 1)))
    test, ist = "Ki-kare bağımsızlık testi", f"χ²({sd}) = {sayi(chi2)}"
    notlar = ["İki kategorik değişken arasındaki ilişki için ki-kare testi kullanıldı."]
    dusuk = (beklenen < 5).mean()
    if dusuk > 0.2:
        if tablo.shape == (2, 2):
            _, p = stats.fisher_exact(tablo.values)
            test, ist = "Fisher'in kesin testi", "kesin test"
            notlar.append("Beklenen frekansı 5'ten küçük hücre oranı yüksek olduğu için "
                          "2×2 tabloda Fisher'in kesin testi kullanıldı.")
        else:
            notlar.append(f"Uyarı: Hücrelerin %{sayi(dusuk * 100, 0)}'inde beklenen frekans "
                          "5'ten küçük. Sonucu dikkatle yorumlayın veya kategorileri birleştirin.")
    anlamli = p < alfa
    yuzde = (pd.crosstab(d[x], d[y], normalize="index") * 100).round(1)
    if anlamli:
        yorum = [
            f"'{x}' ile '{y}' arasında istatistiksel olarak anlamlı bir ilişki var "
            f"({ist}, {p_yaz(p)}).",
            f"Yani '{y}' dağılımı '{x}' kategorilerine göre farklılaşıyor; satır "
            "yüzdeleri tablosu farkın nerede olduğunu gösterir.",
            f"Etki büyüklüğü: Cramér's V = {sayi(v)} ({_buyukluk_r(v)}).",
        ]
    else:
        yorum = [
            f"'{x}' ile '{y}' arasında istatistiksel olarak anlamlı bir ilişki "
            f"bulunmadı ({ist}, {p_yaz(p)}). İki değişken birbirinden bağımsız görünüyor."
        ]
    return {
        "tur": "capraz", "test": test, "n": n, "istatistik": ist, "p": p,
        "anlamli": anlamli, "etki": f"Cramér's V = {sayi(v)} ({_buyukluk_r(v)})",
        "yorum": yorum, "notlar": notlar,
        "tablolar": {"Çapraz tablo (frekans)": tablo.reset_index(),
                     "Satır yüzdeleri (%)": yuzde.reset_index()},
        "x": x, "y": y,
    }


def rapor_md(s: dict, alfa: float) -> str:
    """Sonucu indirilebilir Markdown rapora çevirir."""
    satirlar = [
        f"# Analiz raporu: {s['x']} × {s['y']}", "",
        f"- **Test:** {s['test']}",
        f"- **Gözlem sayısı:** {s['n']}",
        f"- **Test istatistiği:** {s['istatistik']}",
        f"- **Anlamlılık:** {p_yaz(s['p'])} (α = {sayi(alfa)})",
        f"- **Etki büyüklüğü:** {s['etki']}", "", "## Yorum", "",
    ]
    satirlar += [f"- {c}" for c in s["yorum"]]
    satirlar += ["", "## Yöntem notları", ""] + [f"- {c}" for c in s["notlar"]]
    for ad, t in s["tablolar"].items():
        satirlar += ["", f"## {ad}", "", t.round(3).to_markdown(index=False)]
    return "\n".join(satirlar) + "\n"
