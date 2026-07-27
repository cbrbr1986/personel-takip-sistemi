import flet as ft
import pyotp
import qrcode
import io
import base64
import threading
import time

# Şirket için sabit anahtar (Aynen korundu)
SIRKET_ANAHTARI = "BASE32SECRET3232QLDKSAJHGFRTYUIP"

def main(page: ft.Page):
    # 1. Sayfa Genel Ayarları
    page.title = "Güvenli Personel Giriş Terminali (Dinamik QR)"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#f0f2f5"
    page.window_width = 450
    page.window_height = 600

    # 2. QR Kod Üretme Fonksiyonu
    def qr_kod_uret_base64():
        totp = pyotp.TOTP(SIRKET_ANAHTARI, interval=15)
        guncel_sifre = totp.now()
        
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(guncel_sifre)
        qr.make(fit=True)
        
        qr_resim = qr.make_image(fill_color="black", back_color="white")
        
        byte_arr = io.BytesIO()
        qr_resim.save(byte_arr, format='PNG')
        kodlanmis_resim = base64.b64encode(byte_arr.getvalue()).decode('utf-8')
        return kodlanmis_resim

    # 3. Arayüz Elemanlarının Tanımlanması
    baslik = ft.Text(
        value="Lütfen Telefonunuzdan\nQR Kodu Okutunuz", 
        size=22, 
        weight=ft.FontWeight.BOLD, 
        color="#1c1e21", 
        text_align=ft.TextAlign.CENTER
    )
    
    ilk_qr = f"data:image/png;base64,{qr_kod_uret_base64()}"
    qr_gorsel = ft.Image(src=ilk_qr, width=250, height=250, fit="contain")
    
    uyari_yazisi = ft.Text(
        value="Bu QR kod her 15 saniyede bir yenilenir.\nEkran fotoğrafı ile giriş yapılamaz.",
        size=12,
        italic=True,
        color="#606770",
        text_align=ft.TextAlign.CENTER
    )

    # Elemanları ekrana ekliyoruz
    page.add(baslik, qr_gorsel, uyari_yazisi)

    # 4. ZAMANLAYICI DÖNGÜSÜ
    def zamanlayici_dongusu():
        while True:
            time.sleep(15)
            qr_gorsel.src = f"data:image/png;base64,{qr_kod_uret_base64()}"
            page.update() 

    threading.Thread(target=zamanlayici_dongusu, daemon=True).start()

# 5. DOĞRU ÇALIŞTIRMA SATIRI (Hem Masaüstü açar, hem tünel linki üretir)
if __name__ == "__main__":
    ft.app(target=main, port=8550, export_top_level_route=True)

