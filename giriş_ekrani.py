import tkinter as tk
from tkinter import messagebox, simpledialog
import sqlite3
import pyotp
import qrcode
from PIL import ImageTk, Image
import time

# Şirket için sabit bir anahtar belirliyoruz (Banka gibi)
SIRKET_ANAHTARI = "BASE32SECRET3232QLDKSAJHGFRTYUIP"

def qr_kod_yenile():
    # 1. Zaman bazlı şifre üreten motoru çalışztatıyoruz
    totp = pyotp.TOTP(SIRKET_ANAHTARI, interval=15)
    guncel_sifre = totp.now()

    # 2. Bu şifreyi içeren bir QR kod resmi oluşturuyoruz
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(guncel_sifre)
    qr.make(fit=True)

    # 3. Resmi Tkinter'ın anlayacağı formata çeviriyoruz
    qr_resim = qr.make_image(fill_color="black", back_color="white")
    qr_tk = ImageTk.PhotoImage(qr_resim)

    # 4. Ekrandaki etiketi bu yeni resimle güncelliyoruz
    qr_etiketi.config(image=qr_tk)
    qr_etiketi.image = qr_tk # Resmin hafızadan silinmesini önler

    # 5. ZAMANLAYICI: 15.000 milisaniye (15 saniye) sonra bu fonksiyonu tekrar çağır!
    pencere.after(15000, qr_kod_yenile)
# YENİ ÖZELLİK: Eski cihaz kilidini veritabanına dokunmadan arayüz üzerinden temizleyen fonksiyon
def cihaz_kilidini_sifirla_buton():
    # Kullanıcıdan Personel ID'sini girdi olarak alıyoruz
    p_id_str = simpledialog.askstring("Cihaz Kilidi Sıfırla", "Cihaz kilidi kaldırılacak Personel ID girin:", parent=pencere)
    if not p_id_str:
        return

    try:
        p_id = int(p_id_str)
    except ValueError:
        messagebox.showerror("Hata", "Geçersiz Personel ID! Lütfen sadece sayı girin.")
        return

    try:
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()

        # Personel gerçekten var mı kontrol et
        imlec.execute("SELECT isim, soyisim FROM personeller WHERE id = ?", (p_id,))
        personel = imlec.fetchone()

        if personel:
            # Personelin cihaz eşleşmesini temizle
            imlec.execute("UPDATE personeller SET cihaz_id = 'EŞLEŞMEDİ' WHERE id = ?", (p_id,))
            baglanti.commit()
            messagebox.showinfo("Başarılı", f"{personel[0]} {personel[1]} için eski cihaz kilidi silindi!\nPersonel yeni telefonundan okuttuğunda otomatik eşleşecektir.")
        else:
            messagebox.showerror("Hata", "Bu ID'ye sahip bir personel bulunamadı!")

        baglanti.close()
    except Exception as hata:
        messagebox.showerror("Hata", f"Kilit sıfırlanırken hata oluştu: {hata}")

# 1. Ana penceremizi oluşturuyoruz ve boyutunu ayarlıyoruz
pencere = tk.Tk()
pencere.title("Güvenli Personel Giriş Terminali (Dinamik QR)")
pencere.geometry("450x620") # Buton için boyutu dikeyde biraz genişlettik
pencere.configure(bg="#f0f2f5") # Şık, açık gri bir arka plan

# 2. Üst kısma personeli yönlendiren net bir başlık yazısı ekliyoruz
baslik = tk.Label(pencere, text="Lütfen Telefonunuzdan\nQR Kodu Okutunuz", font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#1c1e21")
baslik.pack(pady=20)

# 3. QR Kod resminin içine yerleşeceği boş bir etiket (çerçeve) oluşturuyoruz
qr_etiketi = tk.Label(pencere, bg="white")
qr_etiketi.pack(pady=10)

# 4. Alt kısma güvenlik uyarısı ekliyoruz
uyari_yazisi = tk.Label(
    pencere,
    text="Bu QR kod her 15 saniyede bir yenilenir.\nEkran fotoğrafı ile giriş yapılamaz.",
    font=("Arial", 10, "italic"),
    bg="#f0f2f5",
    fg="#606770"
)
uyari_yazisi.pack(pady=10)

# 5. YENİ ARAYÜZ BUTONU: Yönetici için eski kilitleri silen admin yetki butonu
btn_sifirla = tk.Button(
    pencere,
    text="⚙️ Eski Cihaz Kilidini Temizle",
    font=("Arial", 11, "bold"),
    bg="#e74c3c", # Şık kırmızı admin rengi
    fg="white",
    relief="flat",
    cursor="hand2",
    command=cihaz_kilidini_sifirla_buton
)
btn_sifirla.pack(pady=15, ipady=5, ipadx=10)

# 6. SİSTEMİ BAŞLATAN KRİTİK TETİKLEYİCİLER:
qr_kod_yenile()

# Pencerenin ekranda sürekli açık kalmasını sağlıyoruz:
pencere.mainloop()
