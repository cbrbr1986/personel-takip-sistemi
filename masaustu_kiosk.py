import requests
import hashlib
import time

# Adres satırı localhost (127.0.0.1) port 8000 olarak milimetrik tamir edildi
URL = "http://localhost:8000/api/verify-login"
GIZLI_API_ANAHTARI = "PDKS_SAYISAL_IMZA_SABITI_2026"

print("--- [SENARYO 3] KRİTİK MASAÜSTÜ KİOSK TERMİNALİ TETİKLENDİ ---")

# Bu bilgisayarın kimliği sunucudaki izinli listede olmalıdır
masaustu_cihaz_id = "guvenlik_kulubesi_pc"

zaman_damgasi = str(int(time.time()))

# Kiosk bilgisayarı güvenli imza üretiyor
ham_metin = f"{masaustu_cihaz_id}{GIZLI_API_ANAHTARI}{zaman_damgasi}"
kiosk_muhru = hashlib.sha256(ham_metin.encode()).hexdigest()

kiosk_paket = {
    "personel_id": 1,
    "islem_turu": "GİRİŞ",
    "okunan_qr_sifresi": "999999", # Kiosk cihazları bypass şifresine sahip olabilir
    "p_enlem": 41.1345,            
    "p_boylam": 28.6234,
    "cihaz_id": masaustu_cihaz_id,
    "cihaz_tipi": "MASAÜSTÜ",       
    "istek_muhru": kiosk_muhru,
    "zaman_damgasi": zaman_damgasi
}

try:
    # Parametreleri requests kütüphanesi otomatik olarak temiz bir şekilde bağlayacak
    cevap = requests.get(URL, params=kiosk_paket)
    print(f"Durum Kodu: {cevap.status_code}")
    print(f"Masaüstü Terminal Ekranı Yanıtı: {cevap.json()}\n")
except Exception as e:
    print(f"Bağlantı Hatası: {e}\n")
