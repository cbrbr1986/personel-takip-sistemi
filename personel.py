class Personel:
    # __init__ metodu, bu sınıftan yeni bir personel yaratıldığında çalışan ilk fonksiyondur (Constructor).
    def __init__(self, personel_id, isim, soyisim, departman, maas):
        # 'self', o an oluşturulan personele ait bilgileri temsil eder.
        self.id = personel_id
        self.isim = isim
        self.soyisim = soyisim
        self.departman = departman
        self.maas = maas
        self.giris_cikisi_aktif_mi = False  # Personel şirkette mi kontrolü

    # Personel bilgilerini ekrana güzelce yazdırmak için bir metot (fonksiyon)
    def bilgileri_goster(self):
        durum = "İçeride" if self.giris_cikisi_aktif_mi else "Dışarıda"
        print(f"ID: {self.id} | {self.isim} {self.soyisim} | Departman: {self.departman} | Durum: {durum}")


