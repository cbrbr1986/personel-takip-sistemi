from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import pyotp
import qrcode
import io
import base64
import uvicorn
import hashlib
import veritabani
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
app = FastAPI(title="PDKS Ortak API Sistemi (Tam Güvenlikli)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SIRKET_ANAHTARI = "BASE32SECRET3232QLDKSAJHGFRTYUIP"
GIZLI_API_ANAHTARI = "PDKS_SAYISAL_IMZA_SABITI_2026"

def get_turkiye_timestamp():
    tz = ZoneInfo("Europe/Istanbul")
    return int(datetime.now(tz).timestamp())

@app.get("/api/get-qr")
@limiter.limit("30/minute")
def get_qr_code(request: Request):
    totp = pyotp.TOTP(SIRKET_ANAHTARI, interval=15)
    guncel_sifre = totp.now()

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(guncel_sifre)
    qr.make(fit=True)

    qr_resim = qr.make_image(fill_color="black", back_color="white")
    byte_arr = io.BytesIO()
    qr_resim.save(byte_arr, format='PNG')
    kodlanmis_resim = base64.b64encode(byte_arr.getvalue()).decode('utf-8')

    return JSONResponse(content={
        "status": "success",
        "qr_base64": f"data:image/png;base64,{kodlanmis_resim}",
        "sifre": guncel_sifre
    })

@app.get("/api/get-logs")
@limiter.limit("60/minute")
def get_logs(request: Request):
    try:
        ham_loglar = veritabani.tum_loglari_getir()
        formatli_loglar = []
        for log in ham_loglar:
            if isinstance(log, dict):
                durum = str(log.get("durum", "NORMAL"))
                formatli_loglar.append({
                    "log_id": log.get("id", "0"),
                    "personel": log.get("personel_ad_soyad", "Bilinmeyen Personel"),
                    "islem_turu": log.get("islem_turu", "GİRİŞ"),
                    "zaman": log.get("zaman_damgasi", "-"),
                    "sube": log.get("sube_adi", "Merkez"),
                    "durum_etiketi": durum if len(durum) > 6 else "NORMAL"
                })
        return JSONResponse(content={"status": "success", "toplam_kayit": len(formatli_loglar), "data": formatli_loglar})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Hata: {str(e)}"})

@app.post("/api/verify-camera-photo")
@limiter.limit("15/minute")
async def verify_camera_photo(
    request: Request,
    personel_id: str = Form(...),
    islem_turu: str = Form(...),
    p_enlem: str = Form(...),
    p_boylam: str = Form(...),
    p_sapma: str = Form(...),
    cihaz_id: str = Form(...),
    istek_muhru: str = Form(...),
    zaman_damgasi: str = Form(...),
    okunan_qr_metni: str = Form(...)
):
    ham_metin = f"{cihaz_id}{GIZLI_API_ANAHTARI}{zaman_damgasi}"
    sunucu_muhru = hashlib.sha256(ham_metin.encode()).hexdigest()
    if sunucu_muhru != istek_muhru:
        return JSONResponse(content={"status": "error", "message": "API Güvenlik Duvarı: Geçersiz mühür!"})

    guncel_sunucu_zamani = get_turkiye_timestamp()
    try:
        gelen_zaman = int(zaman_damgasi)
    except ValueError:
        return JSONResponse(content={"status": "error", "message": "Zaman damgası tam sayı olmalıdır!"})

    if abs(guncel_sunucu_zamani - gelen_zaman) > 300:
        return JSONResponse(content={"status": "error", "message": "API Güvenlik Duvarı: Zaman aşımı!"})

    try:
        enlem_float = float(p_enlem) if p_enlem and p_enlem != "-" else 0.0
        boylam_float = float(p_boylam) if p_boylam and p_boylam != "-" else 0.0
        sapma_float = float(p_sapma) if p_sapma and p_sapma != "-" else 9999.0
        p_id_int = int(personel_id)
    except ValueError:
        return JSONResponse(content={"status": "error", "message": "Veri formatı uyuşmazlığı!"})

    if sapma_float > 50.0 or sapma_float == 0.0:
        return JSONResponse(content={"status": "error", "message": f"Konum güvenilir değil (Sapma: {sapma_float}m)!"})

    totp = pyotp.TOTP(SIRKET_ANAHTARI, interval=15)
    if not totp.verify(okunan_qr_metni, valid_window=5):
        return JSONResponse(content={"status": "error", "message": "Süresi dolmuş veya geçersiz karekod!"})

    try:
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()
        imlec.execute("SELECT id FROM personeller WHERE id = ?", (p_id_int,))
        if not imlec.fetchone():
            imlec.execute("""
                INSERT OR IGNORE INTO personeller (id, isim, soyisim, departman, maas, cihaz_id, gizli_anahtar, calisma_modeli, mesai_baslangic, vardiya_grubu)
                VALUES (?, 'Canlı Test', 'Personeli', 'Yönetim', 0.0, 'EŞLEŞMEDİ', 'BASE32SECRET', 'SABİT', '09:00', 'YOK')
            """, (p_id_int,))
            baglanti.commit()
        baglanti.close()
    except Exception:
        pass

    try:
        basari_durumu, mesaj = veritabani.kart_basma_onayla(
            p_id=p_id_int, islem_turu=islem_turu, okunan_qr_sifresi=okunan_qr_metni,
            p_enlem=enlem_float, p_boylam=boylam_float, gelen_cihaz_id=cihaz_id
        )
        return JSONResponse(content={"status": "success" if basari_durumu else "error", "message": mesaj})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Veritabanı Hatası: {str(e)}"})

@app.get("/pdks-ekran", response_class=HTMLResponse)
def pdks_ana_ekran():
    dosya_yolu = os.path.join(os.path.dirname(__file__), "pdks_ekran.html")
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/personel-kurulum")
def personel_kurulum_ekrani():
    dosya_yolu = os.path.join(os.path.dirname(__file__), "personel_kurulum.html")
    if not os.path.exists(dosya_yolu):
        raise HTTPException(status_code=404, detail="personel_kurulum.html bulunamadı!")
    return FileResponse(dosya_yolu)

@app.get("/yonetici-paneli", response_class=HTMLResponse)
def yonetici_paneli_arayuzu():
    dosya_yolu = os.path.join(os.path.dirname(__file__), "yonetici_paneli_gelismis.html")
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
