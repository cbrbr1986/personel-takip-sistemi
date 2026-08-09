# PDKS — Boş Firma Kurulumu

1. Render üzerinde bir PostgreSQL veritabanı oluşturun.
2. Web servisi ile veritabanını aynı bölgeye yerleştirin.
3. PostgreSQL iç bağlantı adresini web servisinin `DATABASE_URL` ortam değişkenine ekleyin.
4. Render web servisinde güçlü bir Base32 değerini `SIRKET_ANAHTARI` olarak ekleyin.
5. Başlangıç komutunu `python main.py` olarak bırakın ve yeniden deploy edin.
6. İlk açılışta `/ilk-kurulum` sayfasından firma ve ilk yönetici hesabını oluşturun.
7. Yönetici panelinde önce şube, sonra personel ekleyin.

`DATABASE_URL` bulunmazsa sistem yalnızca yerel geliştirme/test amacıyla SQLite kullanır. `sirket.db` GitHub'a gönderilmez ve müşteriler arasında paylaşılmaz.

Sistem boş başlar; Arnavutköy, Esenyurt, Hadımköy veya başka bir örnek şube/personel otomatik oluşturulmaz.
