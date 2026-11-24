"""Veri Analiz Asistanı — Streamlit arayüzü.

Çalıştırmak için:  streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import analiz as A

st.set_page_config(page_title="Veri Analiz Asistanı", page_icon="📊", layout="wide")
st.title("📊 Veri Analiz Asistanı")
st.caption("Verinizi yükleyin. Uygun istatistiksel testi seçip sonucu sade Türkçeyle yorumlayalım.")


@st.cache_data
def yukle(ad: str, icerik: bytes) -> pd.DataFrame:
    return A.dosya_oku(ad, icerik)


# ------------------------------------------------------------------ kenar çubuğu
with st.sidebar:
    st.header("Veri")
    dosya = st.file_uploader("CSV veya Excel (.xlsx) dosyası", type=["csv", "xlsx"])
    st.header("Ayarlar")
    alfa = st.select_slider("Anlamlılık düzeyi (α)", options=[0.01, 0.05, 0.10], value=0.05)
    st.divider()
    st.caption("Türkçe Excel'den kaydedilen ';' ayırıcılı ve ondalık virgüllü "
               "CSV dosyaları otomatik tanınır.")

if dosya is not None:
    try:
        df = yukle(dosya.name, dosya.getvalue())
    except Exception as e:  # noqa: BLE001
        st.error(f"Dosya okunamadı: {e}")
        st.stop()
    kaynak = dosya.name
else:
    df = A.ornek_veri()
    kaynak = "örnek veri"
    st.info("Şu an **örnek veri** gösteriliyor (üç öğretim yönteminin sınav puanına etkisi). "
            "Kendi verinizi soldaki panelden yükleyebilirsiniz.")

turler = {c: A.degisken_turu(df[c]) for c in df.columns}

sekme_veri, sekme_betimsel, sekme_analiz, sekme_on_son = st.tabs(
    ["🗂️ Veri", "📈 Betimsel istatistikler", "🔍 İki değişkenli analiz",
     "📝 Ön test – son test"]
)

# ------------------------------------------------------------------ veri
with sekme_veri:
    c1, c2, c3 = st.columns(3)
    c1.metric("Gözlem (satır)", f"{len(df):,}".replace(",", "."))
    c2.metric("Değişken (sütun)", df.shape[1])
    c3.metric("Eksik hücre", int(df.isna().sum().sum()))
    st.subheader(f"Veri önizleme: {kaynak}")
    st.dataframe(df, width="stretch", height=320)
    st.subheader("Değişken türleri")
    st.dataframe(
        pd.DataFrame({
            "Değişken": df.columns,
            "Algılanan tür": [turler[c] for c in df.columns],
            "Farklı değer": [df[c].nunique() for c in df.columns],
            "Eksik": [int(df[c].isna().sum()) for c in df.columns],
        }),
        width="stretch", hide_index=True,
    )
    st.caption("En fazla 6 farklı değeri olan sayısal sütunlar (ör. 0/1, 1–5 Likert) "
               "kategorik kabul edilir.")

# ------------------------------------------------------------------ betimsel
with sekme_betimsel:
    sayisallar = [c for c, t in turler.items() if t == "sayısal"]
    kategorikler = [c for c, t in turler.items() if t == "kategorik"]

    if sayisallar:
        st.subheader("Sayısal değişkenler")
        st.dataframe(A.betimsel(df).round(2), width="stretch", hide_index=True)
        secili = st.selectbox("Dağılımını görmek istediğiniz değişken", sayisallar)
        fig = px.histogram(df, x=secili, nbins=25, marginal="box")
        fig.update_layout(bargap=0.05, yaxis_title="Frekans")
        st.plotly_chart(fig, width="stretch")

    if kategorikler:
        st.subheader("Kategorik değişkenler")
        secili_k = st.selectbox("Frekans tablosu", kategorikler)
        fr = A.frekans(df, secili_k)
        k1, k2 = st.columns([1, 2])
        k1.dataframe(fr, width="stretch", hide_index=True)
        k2.plotly_chart(px.bar(fr, x="Kategori", y="Frekans", text="Yüzde"),
                        width="stretch")

# ------------------------------------------------------------------ ön test – son test
with sekme_on_son:
    st.write("Aynı kişilerin ön ve son ölçümlerini içeren iki sayısal sütun seçin. "
             "Her satır bir ölçüm çiftini temsil etmelidir.")
    sayisal_sutunlar = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
                        and not pd.api.types.is_bool_dtype(df[c])]
    if len(sayisal_sutunlar) < 2:
        st.warning("Bu analiz için en az iki sayısal sütun gerekli.")
    else:
        varsayilan_son = "son_test_puani" if "son_test_puani" in sayisal_sutunlar else None
        varsayilan_on = ("on_test_puani" if "on_test_puani" in sayisal_sutunlar
                         else next(c for c in sayisal_sutunlar if c != varsayilan_son))
        if varsayilan_son is None:
            varsayilan_son = next(c for c in sayisal_sutunlar if c != varsayilan_on)
        s1, s2 = st.columns(2)
        on = s1.selectbox("Ön test sütunu", sayisal_sutunlar,
                          index=sayisal_sutunlar.index(varsayilan_on))
        son = s2.selectbox("Son test sütunu", sayisal_sutunlar,
                           index=sayisal_sutunlar.index(varsayilan_son))
        try:
            esli_sonuc = A.on_test_son_test(df, on, son, alfa)
        except ValueError as e:
            st.warning(str(e))
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Kullanılan test", esli_sonuc["test"])
            m2.metric("Test istatistiği", esli_sonuc["istatistik"])
            m3.metric("Anlamlılık", A.p_yaz(esli_sonuc["p"]))
            m4.metric("Ölçüm çifti", esli_sonuc["n"])
            kutu = st.success if esli_sonuc["anlamli"] else st.warning
            kutu("**Sonuç:** " + " ".join(esli_sonuc["yorum"]))
            st.write(f"**Etki büyüklüğü:** {esli_sonuc['etki']}")
            for ad, tablo in esli_sonuc["tablolar"].items():
                st.subheader(ad)
                st.dataframe(tablo.round(3), width="stretch", hide_index=True)
            with st.expander("Neden bu test seçildi?"):
                for not_ in esli_sonuc["notlar"]:
                    st.write("• " + not_)
            st.download_button(
                "📄 Ön test – son test raporunu indir (Markdown)",
                data=A.rapor_md(esli_sonuc, alfa),
                file_name=f"rapor_{on}_{son}.md",
                mime="text/markdown",
            )

# ------------------------------------------------------------------ analiz
with sekme_analiz:
    st.write("İki değişken seçin; uygulama türlerine bakarak uygun testi kendisi seçer.")
    sutunlar = list(df.columns)
    v1 = sutunlar.index("yontem") if "yontem" in sutunlar else 0
    v2 = sutunlar.index("sinav_puani") if "sinav_puani" in sutunlar else min(1, len(sutunlar) - 1)
    s1, s2 = st.columns(2)
    x = s1.selectbox("1. değişken", sutunlar, index=v1, format_func=lambda c: f"{c} ({turler[c]})")
    y = s2.selectbox("2. değişken", sutunlar, index=v2, format_func=lambda c: f"{c} ({turler[c]})")

    try:
        sonuc = A.analiz(df, x, y, alfa)
    except ValueError as e:
        st.warning(str(e))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kullanılan test", sonuc["test"])
    m2.metric("Test istatistiği", sonuc["istatistik"])
    m3.metric("Anlamlılık", A.p_yaz(sonuc["p"]))
    m4.metric("Gözlem", sonuc["n"])

    kutu = st.success if sonuc["anlamli"] else st.warning
    kutu("**Sonuç:** " + " ".join(sonuc["yorum"]))
    st.write(f"**Etki büyüklüğü:** {sonuc['etki']}")

    # grafik
    gx, gy = sonuc["x"], sonuc["y"]
    if sonuc["tur"] == "korelasyon":
        d = df[[gx, gy]].apply(pd.to_numeric, errors="coerce").dropna()
        fig = px.scatter(d, x=gx, y=gy, opacity=0.7)
        egim, kesisim = np.polyfit(d[gx], d[gy], 1)
        xs = np.linspace(d[gx].min(), d[gx].max(), 50)
        fig.add_trace(go.Scatter(x=xs, y=egim * xs + kesisim, mode="lines",
                                 name="Doğrusal eğilim"))
    elif sonuc["tur"] == "grup":
        d = df[[gx, gy]].dropna().astype({gx: str})
        fig = px.box(d, x=gx, y=gy, points="all", color=gx)
        fig.update_layout(showlegend=False)
    else:
        d = df[[gx, gy]].dropna().astype(str)
        fig = px.histogram(d, x=gx, color=gy, barmode="group")
        fig.update_layout(yaxis_title="Frekans")
    st.plotly_chart(fig, width="stretch")

    for ad, tablo in sonuc["tablolar"].items():
        st.subheader(ad)
        st.dataframe(tablo.round(3), width="stretch", hide_index=True)

    with st.expander("Neden bu test seçildi?"):
        for n in sonuc["notlar"]:
            st.write("• " + n)

    st.download_button(
        "📄 Raporu indir (Markdown)",
        data=A.rapor_md(sonuc, alfa),
        file_name=f"rapor_{gx}_{gy}.md",
        mime="text/markdown",
    )
