# 📊 Veri Analiz Asistanı

CSV veya Excel dosyanızı yükleyin, iki değişken seçin. Uygulama değişken türlerine bakarak uygun istatistiksel testi seçer, sonucu sade Türkçeyle yorumlar ve grafiğini çizer.

| Değişkenler | Normal dağılım varsa | Yoksa |
|---|---|---|
| Sayısal × sayısal | Pearson korelasyonu | Spearman korelasyonu |
| Kategorik (2 grup) × sayısal | Welch t-testi + Cohen's d | Mann-Whitney U |
| Kategorik (3+ grup) × sayısal | ANOVA + η² + Tukey | Kruskal-Wallis + Bonferroni |
| Kategorik × kategorik | Ki-kare + Cramér's V | (2×2 ve düşük frekansta) Fisher |

**Ön test – son test** sekmesi, aynı satırdaki iki sayısal ölçümü eşleştirir.
Ölçüm farkları normal dağılıma uyuyorsa eşleştirilmiş t-testi ve Cohen's dᶻ,
uymuyorsa Wilcoxon işaretli sıralar testi ve sıra-çift serili korelasyon kullanılır.
Eksik veya sonlu olmayan ölçüm içeren çiftler çıkarılır; en az 5 geçerli çift gerekir.
Wilcoxon testi farkların sıfır çevresinde simetrik olduğunu varsayar.

Normallik 5.000 gözleme kadar Shapiro-Wilk, daha büyük örneklemlerde
normaltest ile kontrol edilir. Sabit farklarda normallik değerlendirilemez.

## Dosyalar

- `app.py`: Streamlit arayüzü
- `analiz.py`: Tüm istatistik fonksiyonları (arayüzden bağımsız, Colab'da da kullanılabilir)
- `requirements.txt`: Gerekli paketler

## Bilgisayarda çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Colab'da analiz modülünü kullanma

```python
!pip install -q scipy pandas tabulate
import analiz as A          # analiz.py dosyasını Colab'a yükledikten sonra
df = A.ornek_veri()
s = A.analiz(df, "yontem", "sinav_puani")
print("\n".join(s["yorum"]))
```

## Ücretsiz yayınlama (Streamlit Community Cloud)

1. GitHub'da yeni bir depo açın (ör. `veri-analiz-asistani`) ve bu dört dosyayı yükleyin.
2. https://share.streamlit.io adresine GitHub hesabınızla girin.
3. **Create app** düğmesine basın, depoyu seçin, ana dosya olarak `app.py` yazın, **Deploy** deyin.
4. Birkaç dakika içinde herkesin açabileceği bir bağlantınız olur.

## Geliştirme fikirleri (Copilot ile)

- Çoklu doğrusal regresyon sekmesi
- Raporu Word/PDF olarak indirme
- Güvenirlik analizi (Cronbach alfa) ve Likert ölçek desteği
