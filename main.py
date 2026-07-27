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
    return """
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

@app.get("/personel-kurulum")
def personel_kurulum_ekrani():
    dosya_yolu = os.path.join(os.path.dirname(__file__), "personel_kurulum.html")
    if not os.path.exists(dosya_yolu):
        raise HTTPException(status_code=404, detail="personel_kurulum.html bulunamadı!")
    return FileResponse(dosya_yolu)
@app.get("/yonetici-paneli", response_class=HTMLResponse)
def yonetici_paneli_arayuzu():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>PDKS Akıllı Vardiya & Esnek Çalışma Paneli</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 25px; color: #1c1e21; }
            .main-header { text-align: center; font-size: 28px; font-weight: bold; margin-bottom: 30px; color: #2c3e50; }
            .grid-container { display: grid; grid-template-columns: 1fr 1.5fr; gap: 20px; margin-bottom: 25px; }
            .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); text-align: center; }
            .qr-box img { width: 220px; height: 220px; object-fit: contain; border: 1px solid #ddd; padding: 10px; border-radius: 8px; }
            .qr-code-text { font-size: 28px; font-weight: bold; color: #e74c3c; letter-spacing: 4px; margin-top: 10px; }
            .model-list { text-align: left; margin: 20px auto; max-width: 400px; font-size: 14px; line-height: 1.8; }
            .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
            .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px; }
            .stat-box { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.04); text-align: center; border-bottom: 4px solid #ddd; }
            .stat-box.gec { border-bottom-color: #e74c3c; color: #e74c3c; }
            .stat-box.vardiya { border-bottom-color: #3498db; color: #3498db; }
            .stat-box.esnek { border-bottom-color: #f1c40f; color: #f1c40f; }
            .stat-num { font-size: 32px; font-weight: bold; margin-top: 5px; }
            .search-bar { width: 100%; padding: 12px; font-size: 15px; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.04); }
            th, td { padding: 14px; text-align: left; border-bottom: 1px solid #eee; }
            th { background-color: #34495e; color: white; font-weight: 600; }
            tr:hover { background-color: #f8f9fa; }
            .badge { padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 11px; text-transform: uppercase; }
            .badge-giriş { background: #2ecc71; color: white; }
            .badge-çıkış { background: #e74c3c; color: white; }
            .badge-gec { background: #f1c40f; color: #333; }
        </style>
    </head>
    <body>
        <div class="main-header">PDKS Akıllı Vardiya & Esnek Çalışma Paneli</div>
        <div class="grid-container">
            <div class="card">
                <h3 style="margin-top:0; color:#34495e;">Canlı Ortak Giriş QR Kodu</h3>
                <div class="qr-box"><img id="panel-qr-img" src="" alt="QR Yükleniyor..."></div>
                <div id="panel-qr-text" class="qr-code-text">------</div>
                <div id="panel-counter" style="margin-top:10px; color:#7f8c8d; font-weight:bold;">Yenileniyor...</div>
            </div>
            <div class="card" style="display: flex; flex-direction: column; justify-content: center;">
                <h3 style="margin-top:0; color:#34495e;">Sistem Çalışma Modelleri</h3>
                <div class="model-list">
                    <div><span class="status-dot" style="background:#e74c3c;"></span><b>Sabit Saat:</b> 09:00 sonrasında otomatik "GEÇ KALDI" yazar.</div>
                    <div><span class="status-dot" style="background:#3498db;"></span><b>Vardiya Sistemi:</b> Fabrika/Depo için Gece-Gündüz takibi yapar.</div>
                    <div><span class="status-dot" style="background:#f1c40f;"></span><b>Esnek Model:</b> Yazılımcı/Saha personeli için serbest zaman loglar.</div>
                </div>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-box gec">Bugün Geç Kalanlar<div id="count-gec" class="stat-num">0</div></div>
            <div class="stat-box vardiya">Aktif Vardiyalılar<div id="count-vardiya" class="stat-num">0</div></div>
            <div class="stat-box esnek">Esnek Çalışanlar<div id="count-esnek" class="stat-num">0</div></div>
        </div>
        <input type="text" id="panel-search" class="search-bar" placeholder="Personel ismi, şube adı veya durum etiketine göre canlı ara..." onkeyup="canliAra()">
        <h3 style="color:#2c3e50; margin-bottom:10px;">Gelişmiş Personel Geçiş Günlüğü</h3>
        <table>
            <thead>
                <tr><th>Personel</th><th>İşlem Türü</th><th>Zaman Damgası</th><th>Bulunduğu Şube</th><th>Durum Bilgisi</th></tr>
            </thead>
            <tbody id="panel-table-body">
                <tr><td colspan="5" style="text-align:center;">Veriler yükleniyor...</td></tr>
            </tbody>
        </table>
        <script>
            let tumLoglar = [];
            async function qrGuncelle() {
                try {
                    let r = await fetch('/api/get-qr');
                    let res = await r.json();
                    if(res.status === "success") {
                        document.getElementById('panel-qr-img').src = res.qr_base64;
                        document.getElementById('panel-qr-text').innerText = res.sifre;
                    }
                } catch(e) {}
            }
            async function verileriYenile() {
                try {
                    let r = await fetch('/api/get-logs');
                    let res = await r.json();
                    if(res.status === "success") {
                        tumLoglar = res.data;
                        tabloyuCiz(tumLoglar);
                        sayaclariGuncelle(tumLoglar);
                    }
                } catch(e) {}
            }
            function tabloyuCiz(veriler) {
                let html = "";
                veriler.forEach(log => {
                    let etiketSinif = "badge-giriş";
                    if(log.islem_turu === "ÇIKIŞ") etiketSinif = "badge-çıkış";
                    if(log.durum_etiketi.includes("GEÇ")) etiketSinif = "badge-gec";
                    html += `<tr>
                        <td><b>\${log.personel}</b></td>
                        <td><span class="badge badge-\${log.islem_turu.toLowerCase()}">\${log.islem_turu}</span></td>
                        <td>\${log.zaman}</td>
                        <td>📍 \${log.sube}</td>
                        <td><span class="badge \${etiketSinif}">\${log.durum_etiketi}</span></td>
                    </tr>`;
                });
                document.getElementById('panel-table-body').innerHTML = html || '<tr><td colspan="5" style="text-align:center;">Kayıt bulunamadı.</td></tr>';
            }
            function sayaclariGuncelle(veriler) {
                let gec = 0, vardiya = 0, esnek = 0;
                veriler.forEach(log => {
                    if(log.durum_etiketi.includes("GEÇ")) gec++;
                    if(log.durum_etiketi.includes("VARDİYA")) vardiya++;
                    if(log.durum_etiketi.includes("ESNEK")) esnek++;
                });
                document.getElementById('count-gec').innerText = gec;
                document.getElementById('count-vardiya').innerText = vardiya;
                document.getElementById('count-esnek').innerText = esnek;
            }
            function canliAra() {
                let kelime = document.getElementById('panel-search').value.toLowerCase();
                let filtreli = tumLoglar.filter(log =>
                    log.personel.toLowerCase().includes(kelime) ||
                    log.sube.toLowerCase().includes(kelime) ||
                    log.durum_etiketi.toLowerCase().includes(kelime)
                );
                tabloyuCiz(filtreli);
            }
            qrGuncelle(); verileriYenile();
            setInterval(qrGuncelle, 15000); setInterval(verileriYenile, 5000);
            let sure = 15;
            setInterval(() => {
                sure--; if(sure <= 0) sure = 15;
                document.getElementById('panel-counter').innerText = "Kalan Süre: " + sure + " saniye";
            }, 1000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
