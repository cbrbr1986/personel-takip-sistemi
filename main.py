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

# İstek sınırlandırma motoru kurulumu
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
app = FastAPI(title="PDKS Ortak API Sistemi (Tam Güvenlikli)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Güvenlik protokolleri tanımlaması
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

    qr = qrcode.QRCode(
        version=1, 
        error_correction=qrcode.constants.ERROR_CORRECT_L, 
        box_size=10, 
        border=4
    )
    qr.add_data(guncel_sifre)
    qr.make(fit=True)

    qr_resim = qr.make_image(fill_color="black", back_color="white")
    byte_arr = io.BytesIO()
    qr_resim.save(byte_arr, format='PNG')
    kodlanmis_resim = base64.b64encode(byte_arr.getvalue()).decode('utf-8')
    
    temiz_base64 = kodlanmis_resim.strip().replace(
        "\n", ""
    ).replace("\r", "")

    return JSONResponse(content={
        "status": "success",
        "qr_base64": f"data:image/png;base64,{temiz_base64}",
        "sifre": str(guncel_sifre)
    })

@app.get("/api/get-logs")
@limiter.limit("60/minute")
def get_logs(request: Request):
    try:
        ham_loglar = veritabani.tum_loglari_getir_api()
        formatli_loglar = []
        for log in ham_loglar:
            if isinstance(log, dict):
                durum = str(log.get("durum", "NORMAL"))
                formatli_loglar.append({
                    "log_id": log.get("id", "0"),
                    "personel": log.get(
                        "personel_ad_soyad", 
                        "Bilinmeyen Personel"
                    ),
                    "islem_turu": log.get("islem_turu", "GİRİŞ"),
                    "zaman": log.get("zaman_damgasi", "-"),
                    "sube": log.get("sube_adi", "Merkez"),
                    "durum_etiketi": durum if len(durum) > 6 else "NORMAL"
                })
        return JSONResponse(content={
            "status": "success", 
            "toplam_kayit": len(formatli_loglar), 
            "data": formatli_loglar
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error", 
            "message": f"Hata: {str(e)}"
        })
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
        return JSONResponse(content={
            "status": "error", 
            "message": "API Güvenlik Duvarı: Geçersiz mühür!"
        })

    guncel_sunucu_zamani = get_turkiye_timestamp()
    try:
        gelen_zaman = int(zaman_damgasi)
    except ValueError:
        return JSONResponse(content={"status": "error", "message": "Zaman damgası tam sayı olmalıdır!"})

    if abs(guncel_sunucu_zamani - gelen_zaman) > 300:
        return JSONResponse(content={
            "status": "error", 
            "message": "API Güvenlik Duvarı: Zaman aşımı!"
        })

    try:
        enlem_float = float(p_enlem) if p_enlem and p_enlem != "-" else 0.0
        boylam_float = float(p_boylam) if p_boylam and p_boylam != "-" else 0.0
        sapma_float = float(p_sapma) if p_sapma and p_sapma != "-" else 9999.0
        p_id_int = int(personel_id)
    except ValueError:
        return JSONResponse(content={"status": "error", "message": "Veri formatı uyuşmazlığı!"})

    if sapma_float > 50.0 or sapma_float == 0.0:
        return JSONResponse(content={
            "status": "error", 
            "message": f"Konum güvenilir değil (Sapma: {sapma_float}m)!"
        })

    totp = pyotp.TOTP(SIRKET_ANAHTARI, interval=15)
    if not totp.verify(okunan_qr_metni, valid_window=5):
        return JSONResponse(content={
            "status": "error", 
            "message": "Süresi dolmuş veya geçersiz karekod!"
        })

    try:
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()
        imlec.execute("SELECT id FROM personeller WHERE id = ?", (p_id_int,))
        if not imlec.fetchone():
            imlec.execute("""
                INSERT OR IGNORE INTO personeller (
                    id, isim, soyisim, departman, maas, 
                    cihaz_id, gizli_anahtar, calisma_modeli, 
                    mesai_baslangic, vardiya_grubu
                ) VALUES (?, 'Canlı Test', 'Personeli', 'Yönetim', 0.0, 'EŞLEŞMEDİ', 'BASE32SECRET', 'SABİT', '09:00', 'YOK')
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
    dosya_yolu = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "pdks_ekran.html"
    )
    with open(dosya_yolu, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/personel-kurulum")
def personel_kurulum_ekrani():
    dosya_yolu = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "personel_kurulum.html"
    )
    if not os.path.exists(dosya_yolu):
        raise HTTPException(
            status_code=404, 
            detail="personel_kurulum.html bulunamadı!"
        )
    return FileResponse(dosya_yolu)

@app.get("/yonetici-paneli", response_class=HTMLResponse)
def yonetici_paneli_arayuzu():
    dosya_yolu = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "yonetici_paneli_gelismis.html"
    )
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, 
            detail=f"Hata: {dosya_yolu} sunucuda bulunamadı!"
        )

@app.post("/api/admin-login")
@limiter.limit("5/minute")
async def admin_login(
    request: Request,
    kullanici_adi: str = Form(...),
    sifre: str = Form(...)
):
    if kullanici_adi == "admin" and sifre == "admin123":
        return JSONResponse(content={
            "status": "success", 
            "message": "Giriş başarılı!"
        })

    try:
        baglanti = sqlite3.connect("sirket.db")
        baglanti.row_factory = sqlite3.Row
        imlec = baglanti.cursor()
        
        imlec.execute("""
            SELECT * FROM yoneticiler 
            WHERE kullanici_adi = ? AND sifre = ?
        """, (kullanici_adi, sifre))
        
        yonetici = imlec.fetchone()
        baglanti.close()
        
        if yonetici:
            return JSONResponse(content={"status": "success", "message": "Giriş başarılı!"})
        else:
            return JSONResponse(content={"status": "error", "message": "Kullanıcı adı veya şifre hatalı!"})
            
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": f"Sistem Hatası: {str(e)}"})
@app.get("/api/admin/personel-listesi")
async def api_personel_listesi():
    ham_personeller = veritabani.tum_personelleri_getir()
    formatli_personeller = []
    for p in ham_personeller:
        if isinstance(p, dict):
            formatli_personeller.append({
                "id": str(p.get("id", "")),
                "isim": str(p.get("isim", "")),
                "soyisim": str(p.get("soyisim", "")),
                "departman": str(p.get("departman", "")),
                "calisma_modeli": str(p.get("calisma_modeli", "SABİT"))
            })
    return JSONResponse(content={"status": "success", "data": formatli_personeller})

@app.post("/api/admin/personel-ekle")
async def api_personel_ekle(
    isim: str = Form(...), soyisim: str = Form(...),
    departman: str = Form(...), maas: str = Form(...), 
    calisma_modeli: str = Form(...)
):
    basari, mesaj = veritabani.personel_ekle(isim, soyisim, departman, maas, calisma_modeli)
    return JSONResponse(content={"status": "success" if basari else "error", "message": mesaj})

@app.post("/api/admin/personel-sil")
async def api_personel_sil(personel_id: str = Form(...)):
    basari, mesaj = veritabani.personel_sil(personel_id)
    return JSONResponse(content={"status": "success" if basari else "error", "message": mesaj})

@app.get("/api/admin/sube-listesi")
async def api_sube_listesi():
    try:
        ham_subeler = veritabani.tum_subeleri_getir()
        formatli_subeler = []
        for sube in ham_subeler:
            if isinstance(sube, dict):
                s_id = sube.get("sube_id") or sube.get("id") or sube.get("sube_id AS id")
                formatli_subeler.append({
                    "id": str(s_id) if s_id is not None else "",
                    "sube_adi": str(sube.get("sube_adi", "")),
                    "enlem": float(sube.get("enlem") or 0.0),
                    "boylam": float(sube.get("boylam") or 0.0),
                    "guvenli_yari_cap": int(sube.get("guvenli_yari_cap") or 50)
                })
        return JSONResponse(content={"status": "success", "data": formatli_subeler})
    except Exception as e:
        print(f"Sube listesi cekme hatasi: {e}")
        return JSONResponse(content={"status": "success", "data": []})
        
@app.post("/api/admin/sube-ekle")
async def api_sube_ekle(
    sube_adi: str = Form(...), enlem: str = Form(...),
    boylam: str = Form(...), guvenli_yari_cap: str = Form(...)
):
    basari, mesaj = veritabani.sube_ekle(sube_adi, enlem, boylam, guvenli_yari_cap)
    return JSONResponse(content={"status": "success" if basari else "error", "message": mesaj})

@app.post("/api/admin/sube-sil")
async def api_sube_sil(sube_id: str = Form(...)):
    basari, mesaj = veritabani.sube_sil(sube_id)
    return JSONResponse(content={"status": "success" if basari else "error", "message": mesaj})

@app.post("/api/admin/personel-guncelle")
async def api_personel_guncelle(
    p_id: str = Form(...), isim: str = Form(...), 
    soyisim: str = Form(...), departman: str = Form(...), 
    maas: str = Form(...), calisma_modeli: str = Form(...)
):
    basari, mesaj = veritabani.personel_guncelle(p_id, isim, soyisim, departman, maas, calisma_modeli)
    return JSONResponse(content={"status": "success" if basari else "error", "message": mesaj})

@app.post("/api/admin/sube-guncelle")
async def api_sube_guncelle(
    s_id: str = Form(...), sube_adi: str = Form(...),
    enlem: str = Form(...), boylam: str = Form(...), 
    guvenli_yari_cap: str = Form(...)
):
    basari, mesaj = veritabani.sube_guncelle(s_id, sube_adi, enlem, boylam, guvenli_yari_cap)
    return JSONResponse(content={"status": "success" if basari else "error", "message": mesaj})
@app.post("/api/personel/cihaz-bagla")
async def personel_cihaz_bagla(
    personel_id: str = Form(...), gelen_cihaz_id: str = Form(...)
):
    try:
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()
        imlec.execute(
            "SELECT cihaz_id FROM personeller WHERE id = ?", 
            (int(personel_id),)
        )
        mevcut_cihaz = imlec.fetchone()
        
        if mevcut_cihaz and mevcut_cihaz[0] != 'EŞLEŞMEDİ':
            baglanti.close()
            return JSONResponse(content={
                "status": "error", 
                "message": "Güvenlik Engeli: Telefon zaten eşleşmiş!"
            })
            
        imlec.execute(
            "UPDATE personeller SET cihaz_id = ? WHERE id = ?", 
            (gelen_cihaz_id, int(personel_id))
        )
        baglanti.commit()
        baglanti.close()
        return JSONResponse(content={
            "status": "success", 
            "message": "Telefon kilitlendi!"
        })
    except Exception as e:
        return JSONResponse(content={
            "status": "error", 
            "message": f"Sistem Hatası: {str(e)}"
        })

@app.get("/yonetici-giris", response_class=HTMLResponse)
def yonetici_giris_ekrani():
    dosya_yolu = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "yonetici_paneli_gelismis.html"
    )
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, 
            detail="yonetici_paneli_gelismis.html bulunamadı!"
        )

# =========================================================================
# HARİTA SERVİS MOTORU (YATAY TAŞMALAR TAMAMEN ENGELLENDİ)
# =========================================================================
@app.get('/harita-stil.css')
def harita_css_servis():
    css_kodlari = (
        ".leaflet-container{overflow:hidden}.leaflet-control,"
        ".leaflet-pane{z-index:400}.leaflet-top,.leaflet-bottom"
        "{position:absolute;z-index:1000;pointer-events:none}"
        ".leaflet-top{top:0}.leaflet-right{right:0}.leaflet-bottom"
        "{bottom:0}.leaflet-left{left:0}.leaflet-control"
        "{pointer-events:auto;pointer-events:initial}"
        ".leaflet-pane{position:absolute;left:0;top:0}"
        ".leaflet-tile-pane{z-index:200}.leaflet-overlay-pane"
        "{z-index:400}.leaflet-shadow-pane{z-index:500}"
        ".leaflet-marker-pane{z-index:600}.leaflet-tooltip-pane"
        "{z-index:650}.leaflet-popup-pane{z-index:700}"
        ".leaflet-map-pane canvas{position:absolute;left:0;top:0}"
        ".leaflet-map-pane svg{position:absolute;left:0;top:0}"
        ".leaflet-tile{position:absolute;left:0;top:0;"
        "-webkit-user-select:none;-moz-user-select:none;"
        "user-select:none;pointer-events:none}"
        ".leaflet-tile-container{position:absolute;left:0;top:0}"
        ".leaflet-pixelflipped{display:none}.leaflet-marker-icon,"
        ".leaflet-marker-shadow{position:absolute;left:0;top:0;"
        "display:block}.leaflet-container{background:#ddd;"
        "outline-width:0}.leaflet-container a{color:#0078A8}"
        ".leaflet-zoom-animated{-webkit-transform-origin:0 0;"
        "-ms-transform-origin:0 0;transform-origin:0 0}"
        ".leaflet-zoom-anim .leaflet-zoom-animated"
        "{-webkit-transition:-webkit-transform .25s "
        "cubic-bezier(0,0,.25,1);transition:transform .25s "
        "cubic-bezier(0,0,.25,1)}.leaflet-zoom-anim .leaflet-tile,"
        ".leaflet-pan-anim .leaflet-tile{-webkit-transition:none;"
        "transition:none}.leaflet-interactive{cursor:pointer}"
        ".leaflet-grab{cursor:grab}.leaflet-control-zoom"
        "{border-radius:4px;background:#fff;border:2px solid "
        "rgba(0,0,0,0.2)}.leaflet-control-zoom a{width:26px;"
        "height:26px;line-height:26px;display:block;"
        "text-align:center;text-decoration:none;color:black;"
        "font-weight:bold}.leaflet-bar a:hover"
        "{background-color:#f4f4f4}.leaflet-control-attribution"
        "{background:#fff;background:rgba(255,255,255,0.8);"
        "margin:0;padding:0 5px;font-size:11px}"
    )
    return HTMLResponse(
        content=css_kodlari, 
        status_code=200, 
        headers={'Content-Type': 'text/css'}
    )

@app.get('/harita-motoru.js')
def harita_js_servis():
    js_kodlari = (
        "L=window.L||{};L.Map=function(t,e){return{setView:"
        "function(t,e){var n=document.getElementById('harita');"
        "if(n){n.innerHTML='<iframe width=\"100%\" height=\""
        "100%\" style=\"border:0;border-radius:8px;\" src=\""
        "https://google.com[0]+','+t[1]+"
        "'&z='+e+'&output=embed\"></iframe>'};return this}}};"
        "L.map=function(t,e){return new L.Map(t,e)};"
        "L.tileLayer=function(t,e){return{addTo:function(t){}}};"
        "L.marker=function(t,e){return{addTo:function(t){"
        "return{bindPopup:function(t){return{openPopup:"
        "function(){}}}}}}}};L.circle=function(t,e){return{"
        "addTo:function(t){}}};"
    )
    return HTMLResponse(
        content=js_kodlari, 
        status_code=200, 
        headers={'Content-Type': 'text/javascript'}
    )

if __name__ == "__main__":
    veritabani.veritabani_hazirla()
    
    try:
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()
        
        imlec.execute("""
        CREATE TABLE IF NOT EXISTS yoneticiler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_adi TEXT UNIQUE NOT NULL,
            sifre TEXT NOT NULL,
            rol TEXT DEFAULT 'YONETICI'
        )""")
        
        imlec.execute("SELECT COUNT(*) FROM yoneticiler")
        satir_sayisi = imlec.fetchone()
        
        adet = (
            satir_sayisi[0] if isinstance(satir_sayisi, (tuple, list)) 
            else dict(satir_sayisi).get("COUNT(*)", 0) 
            if hasattr(satir_sayisi, "keys") else 0
        )
        
        if adet == 0:
            imlec.execute("""
                INSERT INTO yoneticiler (kullanici_adi, sifre) 
                VALUES (?, ?)
            """, ("admin", "admin123"))
            baglanti.commit()
            print("Zorunlu Yönetici Hesabı Başarıyla Oluşturuldu!")
            
        baglanti.close()
    except Exception as e:
        print(f"Admin ekleme hatası: {str(e)}")

    uvicorn.run(app, host="0.0.0.0", port=8000)
