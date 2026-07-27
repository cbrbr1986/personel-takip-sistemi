import requests
import hashlib
import time

# Mobil uygulamanın bağlanacağı ana siber korumalı sunucu adresi
URL = "http://192.168.1"
GIZLI_API_ANAHTARI = "PDKS_SAYISAL_IMZA_SABITI_2026"

print("--- [SENARYO 2] MOBİL UYGULAMA (ANDROID/IOS) MOTORU TETİKLENDİ ---")

# 1. Mobil uygulama telefonun işletim sisteminden (IMEI/UUID) donanım kimliğini çeker
telefon_cihaz_id = "android_cihaz_imei_98765"

# 2. Telefonun dahili GPS sensöründen anlık konum çekilir (Arnavutköy Şubesi)
mobil_enlem = 41.1345
mobil_boylam = 28.6234

# 3. Kamera açılır ve duvardaki QR kodun o anki 6 haneli şifresi okunur
# (Buraya tarayıcı ekranındaki güncel şifreyi yazabilirsiniz)
okunan_qr = "654321" 

zaman_damgasi = str(int(time.time()))

# 4. KRİPTOGRAFİK PAKETLEME: Veri manipülasyonunu önlemek için SHA-256 mühür üretilir
ham_metin = f"{telefon_cihaz_id}{GIZLI_API_ANAHTARI}{zaman_damgasi}"
mobil_istek_muhru = hashlib.sha256(ham_metin.encode()).hexdigest()

mobil_paket = {
    "personel_id": 1,
    "islem_turu": "GİRİŞ",
    "okunan_qr_sifresi": okunan_qr,
    "p_enlem": mobil_enlem,
    "p_boylam": mobil_boylam,
    "cihaz_id": telefon_cihaz_id,
    "cihaz_tipi": "MOBİL", # Sunucuya bunun bir cep telefonu uygulaması olduğunu bildirir
    "istek_muhru": mobil_istek_muhru,
    "zaman_damgasi": zaman_damgasi
}

try:
    cevap = requests.get(URL, params=mobil_paket)
    print(f"Durum Kodu: {cevap.status_code}")
    print(f"Mobil Uygulama Ekranı Sunucu Yanıtı: {cevap.json()}\n")
except Exception as e:
    print(f"Bağlantı Hatası: {e}\n")
