# 📊 Veri Analiz Asistanı

CSV veya Excel dosyanızı yükleyin, iki değişken seçin. Uygulama değişken türlerine bakarak uygun istatistiksel testi seçer, sonucu sade Türkçeyle yorumlar ve grafiğini çizer.

| Değişkenler | Normal dağılım varsa | Yoksa |
|---|---|---|
| Sayısal × sayısal | Pearson korelasyonu | Spearman korelasyonu |
| Kategorik (2 grup) × sayısal | Welch t-testi + Cohen's d | Mann-Whitney U |
| Kategorik (3+ grup) × sayısal | ANOVA + η² + Tukey | Kruskal-Wallis + Bonferroni |
| Kategorik × kategorik | Ki-kare + Cramér's V | (2×2 ve düşük frekansta) Fisher |

**Ön test – son test** sekmesi, aynı satırdaki iki sayısal ölçümü eşleştirir.
Örnek verideki `on_test_puani` ve `son_test_puani` sütunları varsayılan olarak seçilir;
son test − ön test farkları ortalama yaklaşık 6, standart sapma yaklaşık 8 olacak
şekilde normal dağılımdan üretilir; bu nedenle bazı öğrencilerin puanı düşer.
Ölçüm farkları normal dağılıma uyuyorsa eşleştirilmiş t-testi ve Cohen's dᶻ,
uymuyorsa Wilcoxon işaretli sıralar testi ve sıra-çift serili korelasyon kullanılır.
Eksik veya sonlu olmayan ölçüm içeren çiftler çıkarılır; en az 5 geçerli çift gerekir.
Wilcoxon testi farkların sıfır çevresinde simetrik olduğunu varsayar.

**Çoklu regresyon** sekmesi, sayısal bir bağımlı değişkeni birden çok sayısal
veya kategorik yordayıcıyla OLS kullanarak inceler. En fazla 6 farklı değeri
olan sayısal yordayıcılar kategorik kabul edilir; ilk kategori referanstır.
Eksik veya sonlu olmayan değer içeren satırlar çıkarılır. Katsayılar, R², F testi,
Shapiro-Wilk, Breusch-Pagan ve VIF sonuçları gösterilir; değişen varyansta HC3
dayanıklı standart hatalar da hesaplanır. Sonuçlar nedensellik göstermez.

İki değişkenli analiz, ön test – son test ve çoklu regresyon sonuçlarını
**➕ Rapora ekle** düğmesiyle kenar çubuğundaki sepette biriktirip tek bir
APA 7 tarzı Word raporu olarak indirebilirsiniz. Rapor başlığı ve yazar adı
ayarlanabilir; her analiz için tablo ve matplotlib grafiği eklenir.

Normallik 5.000 gözleme kadar Shapiro-Wilk, daha büyük örneklemlerde
ön test – son test analizinde normaltest ile kontrol edilir. Regresyonda
Shapiro-Wilk p değeri 5.000'den fazla gözlemde yaklaşık olabilir. Sabit farklarda
normallik değerlendirilemez.

## Dosyalar

- `app.py`: Streamlit arayüzü
- `analiz.py`: Tüm istatistik fonksiyonları (arayüzden bağımsız, Colab'da da kullanılabilir)
- `rapor.py`: APA tarzı Word raporu üretimi
- `requirements.txt`: Gerekli paketler

## Bilgisayarda çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Colab'da analiz modülünü kullanma

```python
!pip install -q scipy pandas tabulate statsmodels
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

- Raporu PDF olarak indirme
- Güvenirlik analizi (Cronbach alfa) ve Likert ölçek desteği
