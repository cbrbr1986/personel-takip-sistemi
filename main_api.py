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
from datetime import datetime
from zoneinfo import ZoneInfo

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Sunucu arkasında IP'leri doğru yakalamak için headers_enabled aktif
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
async def get_qr_code(request: Request):
    totp = pyotp.TOTP(SIRKET_ANAHTARI, interval=15)
    guncel_sifre = totp.now()
    qr = qrcode.QRCode(box_size=10, border=4)
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
async def get_logs(request: Request):
    try:
        ham_loglar = veritabani.tum_loglari_getir()
        formatli_loglar = []

        for log in ham_loglar:
            if isinstance(log, dict):
                durum = str(log.get("durum", "NORMAL"))
                formatli_loglar.append({
                    "log_id": log.get("id", "0"),
                    "personel": log.get("personel_ad", "Bilinmeyen Personel"),
                    "islem_turu": log.get("islem_turu", "GİRİŞ"),
                    "zaman": log.get("zaman_damgasi", "-"),
                    "sube": log.get("sube_adi", "Merkez"),
                    "durum_etiketi": durum if len(durum) > 6 else "NORMAL"
                })
            else:
                formatli_loglar.append({
                    "log_id": str(log),
                    "personel": f"Personel {log}",
                    "islem_turu": "GİRİŞ",
                    "zaman": "-",
                    "sube": "Merkez",
                    "durum_etiketi": "NORMAL"
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
    cihaz_id: str = Form(...),
    istek_muhru: str = Form(...),
    zaman_damgasi: str = Form(...),
    okunan_qr_metni: str = Form(...)
):
    # 1. Güvenlik Katmanı: Sayısal Mühür Doğrulaması
    ham_metin = f"{cihaz_id}{GIZLI_API_ANAHTARI}{zaman_damgasi}"
    sunucu_muhru = hashlib.sha256(ham_metin.encode()).hexdigest()
    if sunucu_muhru != istek_muhru:
        return JSONResponse(content={"status": "error", "message": "API Güvenlik Duvarı: Geçersiz mühür!"})

    # 2. Güvenlik Katmanı: Zaman Aşımı Kontrolü
    guncel_sunucu_zamani = get_turkiye_timestamp()
    try:
        gelen_zaman = int(zaman_damgasi)
    except ValueError:
        return JSONResponse(content={"status": "error", "message": "Zaman damgası tam sayı olmalıdır!"})

    if abs(guncel_sunucu_zamani - gelen_zaman) > 300:
        return JSONResponse(content={
            "status": "error",
            "message": f"API Güvenlik Duvarı: Zaman aşımı! Sunucu TR: {guncel_sunucu_zamani}, Gelen: {gelen_zaman}"
        })

    # 3. Güvenlik Katmanı: QR Kodunun İçindeki TOTP Şifresinin Geçerlilik Kontrolü
    totp = pyotp.TOTP(SIRKET_ANAHTARI, interval=15)
    if not totp.verify(okunan_qr_metni, valid_window=2):
        return JSONResponse(content={"status": "error", "message": "Geçersiz veya süresi dolmuş karekod!"})

    try:
        enlem_float = float(p_enlem) if p_enlem and p_enlem != "-" else 0.0
        boylam_float = float(p_boylam) if p_boylam and p_boylam != "-" else 0.0
        p_id_int = int(personel_id)
    except ValueError:
        return JSONResponse(content={"status": "error", "message": "Veri formatı uyuşmazlığı!"})

    # 4. Katman: Veritabanı Kayıt ve Onay Adımı
    try:
        basari_durumu, mesaj = veritabani.kart_basma_onayla(
            p_id=p_id_int,
            islem_turu=islem_turu,
            okunan_qr_sifresi=okunan_qr_metni,
            p_enlem=enlem_float,
            p_boylam=boylam_float,
            gelen_cihaz_id=cihaz_id
        )
        if basari_durumu:
            return JSONResponse(content={"status": "success", "message": mesaj})
        else:
            return JSONResponse(content={"status": "error", "message": mesaj})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Veritabanı Hatası: {str(e)}"})
@app.get("/pdks-ekran", response_class=HTMLResponse)
def pdks_ana_ekran(request: Request):
    html_pdks = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8"><title>PDKS Canlı Karekod Ekranı</title>
        <style>
            body { font-family: sans-serif; text-align: center; background: #2c3e50; color: white; padding-top: 50px; }
            .container { background: white; padding: 30px; border-radius: 15px; display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
            img { width: 300px; height: 300px; }
            .counter { font-size: 20px; margin-top: 15px; color: #e74c3c; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>PDKS ORTAK GİRİŞ KAPISI</h1>
        <div class="container">
            <h2 style="color:#2c3e50; margin-top:0;">Lütfen Telefonunuzdan Okutun</h2>
            <img id="qr-img" src="" alt="Karekod Yükleniyor...">
            <div id="counter" class="counter">Yenileniyor...</div>
        </div>
        <script>
            async function qrGetir() {
                try {
                    let response = await fetch('/api/get-qr');
                    let data = await response.json();
                    if(data.status === "success") { document.getElementById('qr-img').src = data.qr_base64; }
                } catch(e) {}
            }
            qrGetir(); setInterval(qrGetir, 15000);
            let sure = 15;
            setInterval(() => {
                sure--; if(sure <= 0) sure = 15;
                document.getElementById('counter').innerText = "Kalan Süre: " + sure + " saniye";
            }, 1000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_pdks)

@app.get("/yonetici-paneli", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def yonetici_paneli(request: Request):
    html_yonetici = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>PDKS Yönetici Paneli</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }
            .container { max-width: 1100px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #34495e; color: white; }
            tr:hover { background-color: #f5f5f5; }
            .badge { padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            .badge-normal { background-color: #2ecc71; color: white; }
            .badge-risk { background-color: #e74c3c; color: white; }
            .refresh-btn { background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px; }
            .refresh-btn:hover { background-color: #2980b9; }
        </style>
    </head>
    <body>
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h1>PDKS Canlı Takip ve Yönetim Paneli</h1>
                <button class="refresh-btn" onclick="loglariYukle()">Yenile</button>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Log ID</th>
                        <th>Personel</th>
                        <th>İşlem Türü</th>
                        <th>Zaman</th>
                        <th>Şube</th>
                        <th>Durum</th>
                    </tr>
                </thead>
                <tbody id="log-table-body">
                    <tr>
                        <td colspan="6" style="text-align:center;">Veriler yükleniyor...</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <script>
            async function loglariYukle() {
                try {
                    let response = await fetch('/api/get-logs');
                    let result = await response.json();
                    if(result.status === "success") {
                        let tbody = document.getElementById('log-table-body');
                        tbody.innerHTML = "";
                        if(result.data.length === 0) {
                            tbody.innerHTML = "<tr><td colspan='6' style='text-align:center;'>Henüz kayıtlı log bulunamadı.</td></tr>";
                            return;
                        }
                        result.data.forEach(log => {
                            let badgeClass = log.durum_etiketi === "NORMAL" ? "badge-normal" : "badge-risk";
                            let row = "<tr>" +
                                "<td>" + log.log_id + "</td>" +
                                "<td><strong>" + log.personel + "</strong></td>" +
                                "<td>" + log.islem_turu + "</td>" +
                                "<td>" + log.zaman + "</td>" +
                                "<td>" + log.sube + "</td>" +
                                "<td><span class='badge " + badgeClass + "'>" + log.durum_etiketi + "</span></td>" +
                            "</tr>";
                            tbody.innerHTML += row;
                        });
                    }
                } catch(e) {
                    document.getElementById('log-table-body').innerHTML = "<tr><td colspan='6' style='text-align:center; color:red;'>Veriler alınırken hata oluştu!</td></tr>";
                }
            }
            loglariYukle();
            setInterval(loglariYukle, 10000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_yonetici)

@app.get("/personel-kurulum")
def personel_kurulum_ekrani(request: Request):
    dosya_yolu = os.path.join(os.path.dirname(__file__), "personel_kurulum.html")
    if not os.path.exists(dosya_yolu):
        raise HTTPException(status_code=404, detail="personel_kurulum.html dosyası sunucuda bulunamadı!")
    return FileResponse(dosya_yolu)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
