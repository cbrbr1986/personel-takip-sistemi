import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
from tkinter import ttk
import veritabani # Dogru dosya ismi

veritabani.veritabani_hazirla()

def tabloyu_yenile():
    for sira in tablo.get_children():
        tablo.delete(sira)
    kayitlar = veritabani.veritabanindan_personelleri_getir()
    for s in kayitlar:
        tablo.insert("", tk.END, values=s)

def personel_ekle_buton():
    try:
        p_id = int(entry_id.get())
        isim = entry_isim.get()
        soyisim = entry_soyisim.get()
        departman = entry_departman.get()
        maas = float(entry_maas.get())
        
        veritabani.veritabanina_personel_ekle(p_id, isim, soyisim, departman, maas)
        messagebox.showinfo("Başarılı", f"{isim} eklendi!")
        tabloyu_yenile()
    except Exception as e:
        messagebox.showerror("Hata", f"Kayıt eklenemedi: {e}")

def personel_sil_buton():
    secili_eleman = tablo.selection()
    if not secili_eleman:
        messagebox.showwarning("Uyarı", "Lütfen tablodan bir personel seçin!")
        return
    
    personel_id = tablo.item(secili_eleman)["values"][0]
    veritabani.personel_isten_cikar(personel_id) # Veritabanı ismi duzeltildi
    messagebox.showinfo("Başarılı", "Personel sistemden silindi.")
    tabloyu_yenile()
    
    
def hareket_kaydet_buton(islem_turu):
    secili_eleman = tablo.selection()
    if not secili_eleman:
        messagebox.showwarning("Uyarı", "Lütfen bir personel seçin!")
        return
        
    personel_id = tablo.item(secili_eleman)["values"][0]
    veritabani.log_yaz(personel_id, islem_turu) # Veritabanı ismi duzeltildi
    messagebox.showinfo("İşlem Başarılı", f"Personel {islem_turu} kaydı yapıldı.")

def maas_guncelle_buton():
    secili_eleman = tablo.selection()
    if not secili_eleman:
        messagebox.showwarning("Uyarı", "Lütfen maaşı güncellenecek personeli seçin!")
        return

    personel_id = tablo.item(secili_eleman)["values"][0]

    try:
        # Kullanıcıdan ekrana açılan küçük bir kutuyla yeni maaşı girmesini istiyoruz
        cevap = simpledialog.askstring("Maaş Güncelle", "Yeni Maaş Tutarını Girin:")
        yeni_maas = float(cevap)
        
        # Veritabanına gidip o ID'li personelin maaşını güncelliyoruz
        veritabani.personel_maas_guncelle(personel_id, yeni_maas)
        messagebox.showinfo("Başarılı", "Maaş başarıyla güncellendi!")
        tabloyu_yenile() # Tabloyu güncelleyip yeni maaşı ekranda gösteriyoruz
    except Exception as e:
        messagebox.showerror("Hata", f"Maaş güncellenemedi: {e}")

    
# PENCERE TASARIMI
pencere = tk.Tk()
pencere.title("Profesyonel PDKS")
pencere.geometry("800x450")

# SOL PANEL
sol_cerceve = tk.Frame(pencere, padx=10, pady=10)
sol_cerceve.pack(side=tk.LEFT, fill=tk.Y)

tk.Label(sol_cerceve, text="Personel ID:").pack()
entry_id = tk.Entry(sol_cerceve)
entry_id.pack(pady=2)

tk.Label(sol_cerceve, text="İsim:").pack()
entry_isim = tk.Entry(sol_cerceve)
entry_isim.pack(pady=2)

tk.Label(sol_cerceve, text="Soyisim:").pack()
entry_soyisim = tk.Entry(sol_cerceve)
entry_soyisim.pack(pady=2)

tk.Label(sol_cerceve, text="Departman:").pack()
entry_departman = tk.Entry(sol_cerceve)
entry_departman.pack(pady=2)

tk.Label(sol_cerceve, text="Maaş:").pack()
entry_maas = tk.Entry(sol_cerceve)
entry_maas.pack(pady=2)

btn_ekle = tk.Button(sol_cerceve, text="Personel Ekle", command=personel_ekle_buton, bg="green", fg="white", width=15)
btn_ekle.pack(pady=10)

# SAĞ PANEL
sag_cerceve = tk.Frame(pencere, padx=10, pady=10)
sag_cerceve.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

sutunlar = ("ID", "İsim", "Soyisim", "Departman", "Maaş")
tablo = ttk.Treeview(sag_cerceve, columns=sutunlar, show="headings", height=12)
for sutun in sutunlar:
    tablo.heading(sutun, text=sutun)
    tablo.column(sutun, width=100)
tablo.pack(fill=tk.BOTH, expand=True)

# BUTONLAR
buton_cercevesi = tk.Frame(sag_cerceve)
buton_cercevesi.pack(pady=10)

btn_giris = tk.Button(buton_cercevesi, text="Kart Bas: GİRİŞ", command=lambda: hareket_kaydet_buton("GİRİŞ"), bg="blue", fg="white")
btn_giris.pack(side=tk.LEFT, padx=5)

btn_cikis = tk.Button(buton_cercevesi, text="Kart Bas: ÇIKIŞ", command=lambda: hareket_kaydet_buton("ÇIKIŞ"), bg="orange", fg="black")
btn_cikis.pack(side=tk.LEFT, padx=5)

btn_sil = tk.Button(buton_cercevesi, text="Seçileni Sil", command=personel_sil_buton, bg="red", fg="white")
btn_sil.pack(side=tk.LEFT, padx=5)

btn_zam = tk.Button(buton_cercevesi, text="Seçilene Zam Yap", command=maas_guncelle_buton, bg="yellow", fg="black")
btn_zam.pack(side=tk.LEFT, padx=5)

tabloyu_yenile()
pencere.mainloop()
