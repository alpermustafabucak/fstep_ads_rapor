# Fstep Social — Google Ads PDF Rapor Paneli

Streamlit + Supabase PostgreSQL ve **özel** Supabase Storage ile firma bazında PDF arşivi.

## Kurulum

1. Supabase'de proje oluşturun: https://supabase.com/dashboard
2. SQL Editor'de `schema.sql` dosyasını çalıştırın.
3. `python generate_password.py` çalıştırıp bcrypt özetini kopyalayın.
4. Streamlit Cloud: https://share.streamlit.io — GitHub deposu `alpermustafabucak/fstep_ads_rapor`, branch `main`, main file `app.py`.
5. Streamlit Cloud > App Settings > Secrets alanına aşağıdakileri yazın (gerçek değerlerle):

```toml
SUPABASE_URL = "https://PROJE.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "SUPABASE_GIZLI_SERVICE_ROLE_KEY"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "BCRYPT_HASH"
```

**Dikkat:** Secrets kesinlikle GitHub'a yüklenmemelidir. GitHub deposunu Private yapmanız önerilir. Supabase service_role anahtarı tam yetkilidir ve yalnızca sunucu sırlarında tutulmalıdır.

## Özellikler
- Yönetici oturumu (bcrypt şifre doğrulama)
- Firma kayıtları ve ayrı rapor arşivi
- PDF yükleme, özel buluta kaydetme ve indirme
- Metin tabanlı PDF'lerden temel Google Ads metriklerini otomatik okuma; manuel doğrulama
- Tarihsel grafikler, önceki rapor karşılaştırması ve kural bazlı uyarılar

## Sınırlar
- Gerçek üretken yapay zekâ analizi henüz eklenmedi; değerlendirmeler kurallara dayanır.
- Taranmış/görsel PDF'lerde OCR yoktur.
- Rapor başına 15 MB / 60 sayfa limiti vardır.
- İlk sürüm tek yönetici hesabı içindir; çok kullanıcılı erişim ve ayrıntılı denetim kaydı henüz bulunmaz.
- Aynı güne ait farklı PDF sürümleri saklanabilir.
