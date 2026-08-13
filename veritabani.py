import sqlite3
import datetime
import pyotp
import math
import base64
import os
import re
import hashlib
import hmac
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
POSTGRES_AKTIF = DATABASE_URL.startswith(("postgres://", "postgresql://"))

class _UyumluImlec:
    def __init__(self, imlec, postgres):
        self._imlec = imlec
        self._postgres = postgres

    def execute(self, sorgu, parametreler=()):
        if self._postgres:
            sorgu = sorgu.replace("?", "%s")
            sorgu = re.sub(r"\bINTEGER PRIMARY KEY AUTOINCREMENT\b", "BIGSERIAL PRIMARY KEY", sorgu, flags=re.I)
            sorgu = re.sub(r"\b([a-z_][a-z0-9_]*) INTEGER PRIMARY KEY\b", r"\1 BIGSERIAL PRIMARY KEY", sorgu, flags=re.I)
            if re.search(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO", sorgu, flags=re.I):
                sorgu = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sorgu, count=1, flags=re.I).rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
        self._imlec.execute(sorgu, parametreler)
        return self

    def fetchone(self): return self._imlec.fetchone()
    def fetchall(self): return self._imlec.fetchall()
    @property
    def rowcount(self): return self._imlec.rowcount

class _UyumluBaglanti:
    def __init__(self):
        self.postgres = POSTGRES_AKTIF
        self.row_factory = None
        if self.postgres:
            import psycopg
            self._baglanti = psycopg.connect(DATABASE_URL)
        else:
            self._baglanti = sqlite3.connect(os.getenv("SQLITE_PATH", "sirket.db"))

    def cursor(self):
        if self.postgres:
            from psycopg.rows import dict_row, tuple_row
            return _UyumluImlec(self._baglanti.cursor(row_factory=dict_row if self.row_factory else tuple_row), True)
        self._baglanti.row_factory = self.row_factory
        return _UyumluImlec(self._baglanti.cursor(), False)

    def execute(self, sorgu, parametreler=()):
        imlec = self.cursor()
        return imlec.execute(sorgu, parametreler)

    def commit(self): self._baglanti.commit()
    def rollback(self): self._baglanti.rollback()
    def close(self): self._baglanti.close()

def baglanti_ac():
    return _UyumluBaglanti()

def sifre_hashle(sifre):
    salt = secrets.token_hex(16)
    ozet = hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), bytes.fromhex(salt), 210000).hex()
    return f"pbkdf2_sha256${salt}${ozet}"

def sifre_dogrula(sifre, kayitli):
    try:
        tur, salt, beklenen = kayitli.split("$", 2)
        if tur != "pbkdf2_sha256": return False
        gelen = hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), bytes.fromhex(salt), 210000).hex()
        return hmac.compare_digest(gelen, beklenen)
    except Exception:
        return False
from zoneinfo import ZoneInfo

def turkiye_saati():
    return datetime.datetime.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)

def acik_giris_zaman_asimina_ugradi(calisma_modeli, giris_zamani, simdi=None):
    """Çıkışı unutulan açık girişin yeni işleme taşınmasını engeller.

    Vardiya saatleri henüz ayrı başlangıç/bitiş alanlarıyla tanımlanmadığı için
    gece vardiyasına 24 saat, sabit ve esnek çalışmaya 16 saat güvenli süre verilir.
    """
    simdi = simdi or turkiye_saati()
    azami_saat = 24 if str(calisma_modeli or "").upper() == "VARDİYA" else 16
    return simdi - giris_zamani >= datetime.timedelta(hours=azami_saat)

def veritabani_hazirla():
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS subeler (
        sube_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sube_adi TEXT UNIQUE,
        enlem REAL,
        boylam REAL,
        guvenli_yari_cap INTEGER DEFAULT 50
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS personeller (
        id INTEGER PRIMARY KEY,
        isim TEXT,
        soyisim TEXT,
        departman TEXT,
        maas REAL,
        cihaz_id TEXT DEFAULT 'EŞLEŞMEDİ',
        gizli_anahtar TEXT,
        calisma_modeli TEXT DEFAULT 'SABİT',
        mesai_baslangic TEXT DEFAULT '09:00',
        mesai_bitis TEXT DEFAULT '18:00',
        personel_tolerans_dakika INTEGER DEFAULT 20,
        calisma_gunleri TEXT DEFAULT 'Pzt,Sal,Çar,Per,Cum',
        vardiya_grubu TEXT DEFAULT 'YOK',
        sicil_no TEXT UNIQUE,
        telefon TEXT,
        gorev TEXT,
        sube_id INTEGER,
        aktif INTEGER NOT NULL DEFAULT 1,
        cihaz_token_hash TEXT,
        personel_pin_hash TEXT,
        pin_hata_sayisi INTEGER NOT NULL DEFAULT 0,
        pin_kilit_bitis TEXT,
        tc_kimlik_no TEXT UNIQUE,
        eposta TEXT,
        cinsiyet TEXT,
        dogum_tarihi TEXT,
        dogum_yeri TEXT,
        medeni_durum TEXT,
        uyruk TEXT DEFAULT 'T.C.',
        il TEXT,
        ilce TEXT,
        mahalle TEXT,
        acik_adres TEXT,
        posta_kodu TEXT,
        acil_kisi TEXT,
        acil_telefon TEXT,
        acil_yakinlik TEXT,
        ise_giris_tarihi TEXT,
        personel_turu TEXT,
        ogrenim_durumu TEXT,
        okul TEXT,
        bolum TEXT,
        mezuniyet_yili TEXT,
        mezuniyet_durumu TEXT,
        askerlik_durumu TEXT,
        terhis_tarihi TEXT,
        tecil_bitis_tarihi TEXT,
        askerlik_aciklama TEXT,
        sgk_sicil_no TEXT,
        meslek_kodu TEXT,
        kan_grubu TEXT,
        ehliyet_sinifi TEXT,
        yonetici_notu TEXT,
        foto_mime TEXT,
        foto_base64 TEXT,
        FOREIGN KEY(sube_id) REFERENCES subeler(sube_id)
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS subeler (
        sube_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sube_adi TEXT UNIQUE,
        enlem REAL,
        boylam REAL,
        guvenli_yari_cap INTEGER DEFAULT 50
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS loglar (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        personel_id INTEGER,
        islem_turu TEXT,
        zaman TEXT,
        enlem REAL DEFAULT 0.0,
        boylam REAL DEFAULT 0.0,
        sube_id INTEGER DEFAULT 1,
        durum_etiketi TEXT DEFAULT 'NORMAL',
        FOREIGN KEY(personel_id) REFERENCES personeller(id),
        FOREIGN KEY(sube_id) REFERENCES subeler(sube_id)
    )
    """)

    imlec.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_personeller_sicil_no
        ON personeller(sicil_no)
        WHERE sicil_no IS NOT NULL AND sicil_no <> ''
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS personel_subeleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personel_id INTEGER NOT NULL,
        sube_id INTEGER NOT NULL,
        ana_sube INTEGER NOT NULL DEFAULT 0,
        baslangic_tarihi TEXT,
        bitis_tarihi TEXT,
        aktif INTEGER NOT NULL DEFAULT 1,
        UNIQUE(personel_id, sube_id),
        FOREIGN KEY(personel_id) REFERENCES personeller(id),
        FOREIGN KEY(sube_id) REFERENCES subeler(sube_id)
    )
    """)
    # Eski tek şube kayıtları veri kaybetmeden yeni çoklu şube yapısına taşınır.
    imlec.execute("""
        INSERT OR IGNORE INTO personel_subeleri
            (personel_id, sube_id, ana_sube, aktif)
        SELECT id, sube_id, 1, 1 FROM personeller WHERE sube_id IS NOT NULL
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS firma_bilgileri (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        firma_adi TEXT NOT NULL,
        vergi_no TEXT,
        telefon TEXT,
        eposta TEXT,
        kurulum_zamani TEXT NOT NULL
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS kvkk_bilgilendirme_kayitlari (
        kayit_id INTEGER PRIMARY KEY AUTOINCREMENT, personel_id INTEGER NOT NULL,
        metin_surumu TEXT NOT NULL, bilgi_zamani TEXT NOT NULL, sunucu_kayit_zamani TEXT NOT NULL,
        UNIQUE(personel_id, metin_surumu)
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS yoneticiler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_adi TEXT UNIQUE NOT NULL,
        sifre_hash TEXT NOT NULL,
        ad_soyad TEXT,
        aktif INTEGER NOT NULL DEFAULT 1
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS kartlar (
        kart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        personel_id INTEGER NOT NULL,
        kart_no TEXT UNIQUE NOT NULL,
        kart_turu TEXT NOT NULL DEFAULT 'RFID',
        kart_token_hash TEXT,
        kart_durumu TEXT NOT NULL DEFAULT 'AKTİF',
        verilis_tarihi TEXT,
        gecerlilik_tarihi TEXT,
        son_kullanim TEXT,
        FOREIGN KEY(personel_id) REFERENCES personeller(id)
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS kart_okuyucular (
        okuyucu_id INTEGER PRIMARY KEY AUTOINCREMENT,
        okuyucu_adi TEXT NOT NULL,
        okuyucu_kodu TEXT UNIQUE NOT NULL,
        sube_id INTEGER,
        kapi_adi TEXT,
        aktif INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(sube_id) REFERENCES subeler(sube_id)
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS kart_hareketleri (
        hareket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        kart_id INTEGER,
        personel_id INTEGER,
        okuyucu_id INTEGER,
        zaman TEXT NOT NULL,
        islem_turu TEXT,
        sonuc TEXT NOT NULL,
        red_nedeni TEXT,
        FOREIGN KEY(kart_id) REFERENCES kartlar(kart_id),
        FOREIGN KEY(personel_id) REFERENCES personeller(id),
        FOREIGN KEY(okuyucu_id) REFERENCES kart_okuyucular(okuyucu_id)
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS firma_ayarlari (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        gec_kalma_kontrolu INTEGER NOT NULL DEFAULT 0,
        tolerans_dakika INTEGER NOT NULL DEFAULT 20,
        test_modu INTEGER NOT NULL DEFAULT 0
    )
    """)
    imlec.execute("INSERT OR IGNORE INTO firma_ayarlari (id) VALUES (1)")

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS hata_loglari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personel_id INTEGER,
        zaman TEXT NOT NULL,
        islem TEXT,
        hata_kodu TEXT,
        mesaj TEXT,
        FOREIGN KEY(personel_id) REFERENCES personeller(id)
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS personel_amirleri (
        personel_id INTEGER PRIMARY KEY,
        amir_personel_id INTEGER NOT NULL,
        aktif INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(personel_id) REFERENCES personeller(id),
        FOREIGN KEY(amir_personel_id) REFERENCES personeller(id)
    )
    """)

    imlec.execute("""
    CREATE TABLE IF NOT EXISTS duzeltme_talepleri (
        talep_id INTEGER PRIMARY KEY AUTOINCREMENT,
        personel_id INTEGER NOT NULL,
        amir_personel_id INTEGER,
        log_id INTEGER,
        talep_turu TEXT NOT NULL,
        talep_zamani TEXT NOT NULL,
        istenen_zaman TEXT,
        aciklama TEXT,
        kaynak TEXT NOT NULL DEFAULT 'PERSONEL',
        durum TEXT NOT NULL DEFAULT 'BEKLİYOR',
        karar_zamani TEXT,
        karar_veren TEXT,
        karar_aciklamasi TEXT,
        FOREIGN KEY(personel_id) REFERENCES personeller(id),
        FOREIGN KEY(amir_personel_id) REFERENCES personeller(id),
        FOREIGN KEY(log_id) REFERENCES loglar(log_id)
    )
    """)
    imlec.execute("CREATE INDEX IF NOT EXISTS idx_duzeltme_durum ON duzeltme_talepleri(durum, talep_zamani)")
    imlec.execute("""
        INSERT INTO duzeltme_talepleri(personel_id,amir_personel_id,log_id,talep_turu,talep_zamani,aciklama,kaynak,durum)
        SELECT l.personel_id,pa.amir_personel_id,l.log_id,'ÇIKIŞ UNUTULDU',l.zaman,
               'Önceki eksik çıkış kaydı. Çıkış saati onay bekliyor.','SİSTEM','BEKLİYOR'
        FROM loglar l LEFT JOIN personel_amirleri pa ON pa.personel_id=l.personel_id AND pa.aktif=1
        WHERE l.durum_etiketi='EKSİK ÇIKIŞ'
          AND NOT EXISTS(SELECT 1 FROM duzeltme_talepleri d WHERE d.log_id=l.log_id)
    """)

    baglanti.commit()
    baglanti.close()

def veritabanina_personel_ekle(p_id, isim, soyisim, departman, maas):
    rastgele_gizli_anahtar = pyotp.random_base32()
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("""
        INSERT INTO personeller (id, isim, soyisim, departman, maas, cihaz_id, gizli_anahtar, calisma_modeli, mesai_baslangic, vardiya_grubu)
        VALUES (?, ?, ?, ?, ?, 'EŞLEŞMEDİ', ?, 'SABİT', '09:00', 'YOK')
    """, (p_id, isim, soyisim, departman, maas, rastgele_gizli_anahtar))
    baglanti.commit()
    baglanti.close()

def veritabanindan_personelleri_getir():
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("SELECT * FROM personeller")
    veriler = imlec.fetchall()
    baglanti.close()
    return veriler

def log_yaz(personel_id, islem_turu):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    su_an = turkiye_saati().strftime("%Y-%m-%d %H:%M:%S")
    imlec.execute("""
        INSERT INTO loglar (personel_id, islem_turu, zaman, enlem, boylam, sube_id, durum_etiketi)
        VALUES (?, ?, ?, 0.0, 0.0, 1, 'NORMAL')
    """, (personel_id, islem_turu, su_an))
    baglanti.commit()
    baglanti.close()

def personel_isten_cikar(p_id):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("DELETE FROM personeller WHERE id = ?", (p_id,))
    baglanti.commit()
    baglanti.close()

def personel_maas_guncelle(p_id, yeni_maas):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("UPDATE personeller SET maas = ? WHERE id = ?", (yeni_maas, p_id))
    baglanti.commit()
    baglanti.close()

def mesafe_hesapla(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def kart_basma_onayla(p_id, islem_turu, okunan_qr_sifresi, p_enlem, p_boylam, gelen_cihaz_id):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()

    imlec.execute("""
        SELECT cihaz_id, isim, soyisim, calisma_modeli,
               mesai_baslangic, vardiya_grubu, sube_id, aktif
        FROM personeller WHERE id = ?
    """, (p_id,))
    personel_bilgisi = imlec.fetchone()

    if not personel_bilgisi:
        baglanti.close()
        return False, "Sistemde kayıtlı personel bulunamadı!"

    kayitli_cihaz_id, isim, soyisim, model, sabit_saat, vardiya, atanmis_sube_id, aktif = personel_bilgisi

    if not aktif:
        baglanti.close()
        return False, "Personel kaydı pasif olduğu için işlem yapılamaz."

    if kayitli_cihaz_id == "EŞLEŞMEDİ":
        imlec.execute("UPDATE personeller SET cihaz_id = ? WHERE id = ?", (gelen_cihaz_id, p_id))
        kayitli_cihaz_id = gelen_cihaz_id
    elif kayitli_cihaz_id != gelen_cihaz_id:
        baglanti.close()
        return False, "Giriş Reddedildi! Başkasının telefonu üzerinden kart basamazsınız."

    bugun = turkiye_saati().strftime("%Y-%m-%d")
    imlec.execute("""
        SELECT s.sube_id, s.sube_adi, s.enlem, s.boylam, s.guvenli_yari_cap
        FROM personel_subeleri ps
        JOIN subeler s ON s.sube_id = ps.sube_id
        WHERE ps.personel_id = ? AND ps.aktif = 1
          AND (ps.baslangic_tarihi IS NULL OR ps.baslangic_tarihi = '' OR ps.baslangic_tarihi <= ?)
          AND (ps.bitis_tarihi IS NULL OR ps.bitis_tarihi = '' OR ps.bitis_tarihi >= ?)
        ORDER BY ps.ana_sube DESC, s.sube_adi
    """, (p_id, bugun, bugun))
    tum_subeler = imlec.fetchall()
    # Geçiş güvenliği: henüz ara tabloya taşınmamış eski kayıt ana şubeyi kullanır.
    if not tum_subeler and atanmis_sube_id is not None:
        imlec.execute("""
            SELECT sube_id, sube_adi, enlem, boylam, guvenli_yari_cap
            FROM subeler WHERE sube_id = ?
        """, (atanmis_sube_id,))
        tum_subeler = imlec.fetchall()

    hedef_sube_id = None
    hedef_sube_adi = ""
    for sube in tum_subeler:
        s_id, s_adi, s_enlem, s_boylam, s_yari_cap = sube
        uzaklik = mesafe_hesapla(p_enlem, p_boylam, s_enlem, s_boylam)
        limit_mesafe = float(s_yari_cap if s_yari_cap else 50.0)
        if uzaklik <= limit_mesafe:
            hedef_sube_id = s_id
            hedef_sube_adi = s_adi
            break

    if hedef_sube_id is None:
        baglanti.close()
        return False, "Giriş Reddedildi! Atandığınız şubenin güvenli alanında değilsiniz."

    imlec.execute("""
        SELECT log_id, islem_turu, zaman FROM loglar
        WHERE personel_id = ? ORDER BY log_id DESC LIMIT 1
    """, (p_id,))
    son_islem = imlec.fetchone()
    onceki_cikis_unutuldu = False
    if son_islem:
        try:
            son_zaman = datetime.datetime.strptime(son_islem[2], "%Y-%m-%d %H:%M:%S")
            gecen_sure = turkiye_saati() - son_zaman
            if gecen_sure.total_seconds() < 15 * 60:
                baglanti.close()
                return False, "Mükerrer işlem engellendi. Giriş/çıkış işlemleri arasında en az 15 dakika olmalıdır."

            if son_islem[1] == "GİRİŞ" and acik_giris_zaman_asimina_ugradi(model, son_zaman):
                onceki_cikis_unutuldu = True
                imlec.execute("UPDATE loglar SET durum_etiketi = ? WHERE log_id = ?", ("EKSİK ÇIKIŞ", son_islem[0]))
                imlec.execute("""
                    INSERT INTO hata_loglari (personel_id, zaman, islem, hata_kodu, mesaj)
                    VALUES (?, ?, ?, ?, ?)
                """, (p_id, turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"), "ÇIKIŞ", "CIKIS_UNUTULDU",
                      "Önceki girişin çıkışı unutuldu. Yönetici düzeltmesi bekleniyor."))
                amir = imlec.execute("SELECT amir_personel_id FROM personel_amirleri WHERE personel_id=? AND aktif=1", (p_id,)).fetchone()
                mevcut = imlec.execute("SELECT talep_id FROM duzeltme_talepleri WHERE log_id=? AND durum='BEKLİYOR'", (son_islem[0],)).fetchone()
                if not mevcut:
                    imlec.execute("""
                        INSERT INTO duzeltme_talepleri
                        (personel_id, amir_personel_id, log_id, talep_turu, talep_zamani, aciklama, kaynak, durum)
                        VALUES (?, ?, ?, 'ÇIKIŞ UNUTULDU', ?, ?, 'SİSTEM', 'BEKLİYOR')
                    """, (p_id, amir[0] if amir else None, son_islem[0], turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"),
                          "Azami açık giriş süresi aşıldı. Çıkış saati amir onayı bekliyor."))
        except (TypeError, ValueError):
            pass
        islem_turu = "GİRİŞ" if onceki_cikis_unutuldu else ("ÇIKIŞ" if son_islem[1] == "GİRİŞ" else "GİRİŞ")
    else:
        islem_turu = "GİRİŞ"

    su_an_dt = turkiye_saati()
    su_an_str = su_an_dt.strftime("%Y-%m-%d %H:%M:%S")
    durum_etiketi = "NORMAL"

    if islem_turu == "GİRİŞ":
        if model == "SABİT":
            durum_etiketi = "SABİT GİRİŞ"
        elif model == "VARDİYA":
            durum_etiketi = f"VARDİYA ({vardiya})"
        elif model == "ESNEK":
            durum_etiketi = "ESNEK GİRİŞ"
    else:
        durum_etiketi = "ÇIKIŞ"

    imlec.execute("""
        INSERT INTO loglar (personel_id, islem_turu, zaman, enlem, boylam, sube_id, durum_etiketi)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (p_id, islem_turu, su_an_str, float(p_enlem), float(p_boylam), hedef_sube_id, durum_etiketi))

    baglanti.commit()
    baglanti.close()
    uyari = " Önceki çıkış unutuldu; eksik kayıt yönetici düzeltmesine gönderildi." if onceki_cikis_unutuldu else ""
    return True, f"İşlem Başarılı! {isim} {soyisim} ({model}) - {hedef_sube_adi} Durum: {durum_etiketi}.{uyari}"

def tum_loglari_getir():
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()
    imlec.execute("""
        SELECT loglar.log_id AS id,
               (personeller.isim || ' ' || personeller.soyisim) AS personel_ad_soyad,
               loglar.islem_turu,
               loglar.zaman AS zaman_damgasi,
               COALESCE(subeler.sube_adi, 'Bilinmeyen Şube') AS sube_adi,
               loglar.durum_etiketi AS durum
        FROM loglar
        JOIN personeller ON loglar.personel_id = personeller.id
        LEFT JOIN subeler ON loglar.sube_id = subeler.sube_id
        ORDER BY loglar.zaman DESC
    """)
    veriler = [dict(row) for row in imlec.fetchall()]
    baglanti.close()
    return veriler

def loglari_getir(p_id):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("SELECT islem_turu, zaman FROM loglar WHERE personel_id = ? ORDER BY zaman DESC", (p_id,))
    veriler = imlec.fetchall()
    baglanti.close()
    return veriler

def veritabani_guncelle():
    if POSTGRES_AKTIF:
        return
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN cihaz_id TEXT DEFAULT 'EŞLEŞMEDİ'")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN gizli_anahtar TEXT")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE loglar ADD COLUMN enlem REAL DEFAULT 0.0")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE loglar ADD COLUMN boylam REAL DEFAULT 0.0")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE loglar ADD COLUMN sube_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN calisma_modeli TEXT DEFAULT 'SABİT'")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN mesai_baslangic TEXT DEFAULT '09:00'")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN vardiya_grubu TEXT DEFAULT 'YOK'")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE loglar ADD COLUMN durum_etiketi TEXT DEFAULT 'NORMAL'")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE subeler ADD COLUMN guvenli_yari_cap INTEGER DEFAULT 50")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN sicil_no TEXT")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN telefon TEXT")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN gorev TEXT")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN sube_id INTEGER")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN aktif INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError: pass
    try:
        imlec.execute("ALTER TABLE personeller ADD COLUMN cihaz_token_hash TEXT")
    except sqlite3.OperationalError: pass

    yeni_alanlar = {
        "tc_kimlik_no": "TEXT", "eposta": "TEXT", "cinsiyet": "TEXT",
        "dogum_tarihi": "TEXT", "dogum_yeri": "TEXT", "medeni_durum": "TEXT",
        "uyruk": "TEXT DEFAULT 'T.C.'", "il": "TEXT", "ilce": "TEXT",
        "mahalle": "TEXT", "acik_adres": "TEXT", "posta_kodu": "TEXT",
        "acil_kisi": "TEXT", "acil_telefon": "TEXT", "acil_yakinlik": "TEXT",
        "ise_giris_tarihi": "TEXT", "personel_turu": "TEXT",
        "ogrenim_durumu": "TEXT", "okul": "TEXT", "bolum": "TEXT",
        "mezuniyet_yili": "TEXT", "mezuniyet_durumu": "TEXT",
        "askerlik_durumu": "TEXT", "terhis_tarihi": "TEXT",
        "tecil_bitis_tarihi": "TEXT", "askerlik_aciklama": "TEXT",
        "sgk_sicil_no": "TEXT", "meslek_kodu": "TEXT", "kan_grubu": "TEXT",
        "ehliyet_sinifi": "TEXT", "yonetici_notu": "TEXT",
        "foto_mime": "TEXT", "foto_base64": "TEXT"
    }
    for alan, tur in yeni_alanlar.items():
        try:
            imlec.execute(f"ALTER TABLE personeller ADD COLUMN {alan} {tur}")
        except sqlite3.OperationalError:
            pass
    try:
        imlec.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_personeller_tc ON personeller(tc_kimlik_no) WHERE tc_kimlik_no IS NOT NULL AND tc_kimlik_no <> ''")
    except sqlite3.OperationalError:
        pass

    baglanti.commit()
    baglanti.close()

veritabani_guncelle()
veritabani_hazirla()

def personel_calisma_alanlari_hazirla():
    baglanti = baglanti_ac()
    for sorgu in (
        "ALTER TABLE personeller ADD COLUMN mesai_bitis TEXT DEFAULT '18:00'",
        "ALTER TABLE personeller ADD COLUMN personel_tolerans_dakika INTEGER DEFAULT 20",
        "ALTER TABLE personeller ADD COLUMN calisma_gunleri TEXT DEFAULT 'Pzt,Sal,Çar,Per,Cum'"
    ):
        try:
            baglanti.execute(sorgu)
            baglanti.commit()
        except Exception:
            baglanti.rollback()
    baglanti.close()

personel_calisma_alanlari_hazirla()

def firma_test_modu_alani_hazirla():
    baglanti = baglanti_ac()
    try:
        baglanti.execute("ALTER TABLE firma_ayarlari ADD COLUMN test_modu INTEGER NOT NULL DEFAULT 0")
        baglanti.commit()
    except Exception:
        baglanti.rollback()
    finally:
        baglanti.close()

firma_test_modu_alani_hazirla()

def personel_guvenlik_alanlari_hazirla():
    baglanti = baglanti_ac()
    for sorgu in (
        "ALTER TABLE personeller ADD COLUMN personel_pin_hash TEXT",
        "ALTER TABLE personeller ADD COLUMN pin_hata_sayisi INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE personeller ADD COLUMN pin_kilit_bitis TEXT"
    ):
        try:
            baglanti.execute(sorgu)
            baglanti.commit()
        except Exception:
            baglanti.rollback()
    baglanti.close()

personel_guvenlik_alanlari_hazirla()

def erisim_talepleri_hazirla():
    baglanti = baglanti_ac()
    try:
        baglanti.execute("""
        CREATE TABLE IF NOT EXISTS erisim_talepleri (
            talep_id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_id INTEGER NOT NULL,
            talep_turu TEXT NOT NULL,
            durum TEXT NOT NULL DEFAULT 'BEKLİYOR',
            talep_zamani TEXT NOT NULL,
            karar_zamani TEXT,
            karar_veren TEXT,
            aciklama TEXT,
            FOREIGN KEY(personel_id) REFERENCES personeller(id)
        )
        """)
        baglanti.commit()
    except Exception:
        baglanti.rollback()
    finally:
        baglanti.close()

erisim_talepleri_hazirla()

def erisim_talebi_olustur_sicil(sicil_no, talep_turu, aciklama=""):
    tur = str(talep_turu or "").upper()
    if tur not in ("SIFRE_SIFIRLAMA", "CIHAZ_SIFIRLAMA"):
        return False, "Geçersiz talep türü."
    personel = personel_sicil_ile_getir(str(sicil_no or "").strip())
    if not personel or not personel.get("aktif"):
        return False, "Aktif personel kaydı bulunamadı."
    baglanti = baglanti_ac()
    try:
        mevcut = baglanti.execute("""
            SELECT talep_id FROM erisim_talepleri
            WHERE personel_id=? AND talep_turu=? AND durum='BEKLİYOR'
            LIMIT 1
        """, (personel["id"], tur)).fetchone()
        if mevcut:
            return False, "Bu işlem için zaten bekleyen bir talebiniz var."
        baglanti.execute("""
            INSERT INTO erisim_talepleri
            (personel_id,talep_turu,durum,talep_zamani,aciklama)
            VALUES(?,?,'BEKLİYOR',?,?)
        """, (personel["id"], tur, turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"), str(aciklama or "")[:500]))
        baglanti.commit()
        return True, "Talebiniz yöneticiye gönderildi."
    except Exception as exc:
        baglanti.rollback()
        return False, f"Talep kaydedilemedi: {exc}"
    finally:
        baglanti.close()

def erisim_taleplerini_getir(tumu=False):
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    try:
        kosul = "" if tumu else "WHERE e.durum='BEKLİYOR'"
        rows = baglanti.execute(f"""
            SELECT e.talep_id,e.personel_id,e.talep_turu,e.durum,e.talep_zamani,
                   e.karar_zamani,e.karar_veren,e.aciklama,
                   p.isim,p.soyisim,p.sicil_no,COALESCE(s.sube_adi,'Şube Atanmamış') AS sube_adi
            FROM erisim_talepleri e
            JOIN personeller p ON p.id=e.personel_id
            LEFT JOIN subeler s ON s.sube_id=p.sube_id
            {kosul}
            ORDER BY e.talep_id DESC
        """).fetchall()
        return [dict(x) for x in rows]
    finally:
        baglanti.close()

def personel_sifre_sifirla(personel_id):
    baglanti = baglanti_ac()
    try:
        cur = baglanti.execute("""
            UPDATE personeller
            SET personel_pin_hash=NULL,pin_hata_sayisi=0,pin_kilit_bitis=NULL
            WHERE id=?
        """, (int(personel_id),))
        baglanti.commit()
        return cur.rowcount > 0
    except Exception:
        baglanti.rollback()
        return False
    finally:
        baglanti.close()

def personel_cihaz_sadece_sifirla(personel_id):
    baglanti = baglanti_ac()
    try:
        cur = baglanti.execute("""
            UPDATE personeller
            SET cihaz_id='EŞLEŞMEDİ',cihaz_token_hash=NULL
            WHERE id=?
        """, (int(personel_id),))
        baglanti.commit()
        return cur.rowcount > 0
    except Exception:
        baglanti.rollback()
        return False
    finally:
        baglanti.close()

def erisim_talebi_kararla(talep_id, karar, karar_veren="Yönetici"):
    karar = str(karar or "").upper()
    if karar not in ("ONAYLANDI","REDDEDİLDİ"):
        return False, "Geçersiz karar."
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    try:
        t = baglanti.execute("""
            SELECT * FROM erisim_talepleri WHERE talep_id=? AND durum='BEKLİYOR'
        """, (int(talep_id),)).fetchone()
        if not t:
            return False, "Bekleyen talep bulunamadı."
        if karar == "ONAYLANDI":
            if t["talep_turu"] == "SIFRE_SIFIRLAMA":
                ok = personel_sifre_sifirla(t["personel_id"])
            else:
                ok = personel_cihaz_sadece_sifirla(t["personel_id"])
            if not ok:
                return False, "Sıfırlama işlemi uygulanamadı."
        baglanti.execute("""
            UPDATE erisim_talepleri
            SET durum=?,karar_zamani=?,karar_veren=?
            WHERE talep_id=?
        """, (karar,turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"),karar_veren,int(talep_id)))
        baglanti.commit()
        return True, "Talep onaylandı ve işlem uygulandı." if karar=="ONAYLANDI" else "Talep reddedildi."
    except Exception as exc:
        baglanti.rollback()
        return False, f"İşlem başarısız: {exc}"
    finally:
        baglanti.close()


def durum_olaylari_hazirla():
    baglanti=baglanti_ac()
    try:
        baglanti.execute("""
        CREATE TABLE IF NOT EXISTS durum_olaylari (
            olay_id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_id INTEGER NOT NULL,
            olay_turu TEXT NOT NULL,
            baslangic_tarihi TEXT NOT NULL,
            bitis_tarihi TEXT NOT NULL,
            aciklama TEXT,
            durum TEXT NOT NULL,
            amir_personel_id INTEGER,
            amir_karari TEXT,
            amir_karar_zamani TEXT,
            yonetici_karari TEXT,
            yonetici_karar_zamani TEXT,
            yonetici_aciklamasi TEXT,
            kaynak TEXT NOT NULL DEFAULT 'PERSONEL',
            olusturma_zamani TEXT NOT NULL,
            FOREIGN KEY(personel_id) REFERENCES personeller(id)
        )
        """)
        baglanti.execute("""
        CREATE TABLE IF NOT EXISTS personel_belgeleri (
            belge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            olay_id INTEGER NOT NULL,
            personel_id INTEGER NOT NULL,
            dosya_adi TEXT NOT NULL,
            mime_turu TEXT NOT NULL,
            dosya_base64 TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            yukleme_zamani TEXT NOT NULL,
            FOREIGN KEY(olay_id) REFERENCES durum_olaylari(olay_id),
            FOREIGN KEY(personel_id) REFERENCES personeller(id)
        )
        """)
        baglanti.execute("""
        CREATE TABLE IF NOT EXISTS yonetici_duzeltmeleri (
            duzeltme_id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_id INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            alan TEXT NOT NULL,
            eski_deger TEXT,
            yeni_deger TEXT NOT NULL,
            aciklama TEXT NOT NULL,
            yonetici TEXT NOT NULL,
            zaman TEXT NOT NULL,
            FOREIGN KEY(personel_id) REFERENCES personeller(id)
        )
        """)
        baglanti.commit()
    except Exception:
        baglanti.rollback()
    finally:
        baglanti.close()

durum_olaylari_hazirla()

def performans_indeksleri_hazirla():
    baglanti=baglanti_ac()
    try:
        for sorgu in (
            "CREATE INDEX IF NOT EXISTS idx_loglar_personel_zaman ON loglar(personel_id,zaman)",
            "CREATE INDEX IF NOT EXISTS idx_loglar_personel_tur_zaman ON loglar(personel_id,islem_turu,zaman)",
            "CREATE INDEX IF NOT EXISTS idx_durum_olay_personel_tarih ON durum_olaylari(personel_id,baslangic_tarihi,bitis_tarihi,durum)",
            "CREATE INDEX IF NOT EXISTS idx_yonetici_duzeltme_personel_tarih ON yonetici_duzeltmeleri(personel_id,tarih,duzeltme_id)",
            "CREATE INDEX IF NOT EXISTS idx_erisim_durum ON erisim_talepleri(durum,talep_id)"
        ):
            baglanti.execute(sorgu)
        baglanti.commit()
    except Exception:
        baglanti.rollback()
    finally:
        baglanti.close()

performans_indeksleri_hazirla()

OLAY_TURLERI = {
    "HASTALIK_RAPORU": "RAPORLU",
    "YILLIK_IZIN": "YILLIK İZİN",
    "MAZERET_IZNI": "MAZERET İZNİ",
    "UCRETSIZ_IZIN": "ÜCRETSİZ İZİN",
    "GOREVLI": "GÖREVLİ",
    "DIGER": "DİĞER"
}

def durum_olayi_olustur(personel_id, olay_turu, baslangic, bitis, aciklama="", kaynak="PERSONEL"):
    tur=str(olay_turu or "").upper()
    if tur not in OLAY_TURLERI:
        return False,"Geçersiz durum türü.",None
    try:
        b=datetime.datetime.strptime(str(baslangic),"%Y-%m-%d").date()
        s=datetime.datetime.strptime(str(bitis),"%Y-%m-%d").date()
    except Exception:
        return False,"Başlangıç/bitiş tarihi geçersiz.",None
    if s < b:
        return False,"Bitiş tarihi başlangıçtan önce olamaz.",None
    baglanti=baglanti_ac()
    try:
        amir=baglanti.execute("SELECT amir_personel_id FROM personel_amirleri WHERE personel_id=? AND aktif=1 LIMIT 1",(int(personel_id),)).fetchone()
        # Hastalık raporu bildirimdir: puantaja hemen RAPORLU olarak yansır.
        # İzin/görev türleri çift onay akışındadır.
        durum="BİLDİRİLDİ" if tur=="HASTALIK_RAPORU" else "AMİR BEKLİYOR"
        zaman=turkiye_saati().strftime("%Y-%m-%d %H:%M:%S")
        baglanti.execute("""
            INSERT INTO durum_olaylari
            (personel_id,olay_turu,baslangic_tarihi,bitis_tarihi,aciklama,durum,
             amir_personel_id,kaynak,olusturma_zamani)
            VALUES(?,?,?,?,?,?,?,?,?)
        """,(int(personel_id),tur,b.isoformat(),s.isoformat(),str(aciklama or "")[:1000],durum,
             amir[0] if amir else None,kaynak,zaman))
        kayit=baglanti.execute("""
            SELECT olay_id FROM durum_olaylari
            WHERE personel_id=? AND olay_turu=? AND olusturma_zamani=?
            ORDER BY olay_id DESC LIMIT 1
        """,(int(personel_id),tur,zaman)).fetchone()
        baglanti.commit()
        olay_id=kayit[0] if kayit else None
        return True,("Rapor sisteme işlendi." if tur=="HASTALIK_RAPORU" else "Talep ilgili amire gönderildi."),olay_id
    except Exception as exc:
        baglanti.rollback(); return False,f"Kayıt oluşturulamadı: {exc}",None
    finally:
        baglanti.close()

def durum_olayi_belge_ekle(olay_id, personel_id, dosya_adi, mime_turu, dosya_base64, sha256):
    baglanti=baglanti_ac()
    try:
        baglanti.execute("""
            INSERT INTO personel_belgeleri
            (olay_id,personel_id,dosya_adi,mime_turu,dosya_base64,sha256,yukleme_zamani)
            VALUES(?,?,?,?,?,?,?)
        """,(int(olay_id),int(personel_id),str(dosya_adi)[:200],mime_turu,dosya_base64,sha256,
             turkiye_saati().strftime("%Y-%m-%d %H:%M:%S")))
        baglanti.commit(); return True
    except Exception:
        baglanti.rollback(); return False
    finally:
        baglanti.close()

def olay_belgeleri_getir(olay_id):
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    try:
        rows=baglanti.execute("""
            SELECT belge_id,dosya_adi,mime_turu,sha256,yukleme_zamani
            FROM personel_belgeleri WHERE olay_id=? ORDER BY belge_id
        """,(int(olay_id),)).fetchall()
        return [dict(x) for x in rows]
    finally:
        baglanti.close()

def personel_belgesi_getir(belge_id):
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    try:
        r=baglanti.execute("""
            SELECT belge_id,olay_id,personel_id,dosya_adi,mime_turu,dosya_base64,sha256,yukleme_zamani
            FROM personel_belgeleri WHERE belge_id=?
        """,(int(belge_id),)).fetchone()
        return dict(r) if r else None
    finally:
        baglanti.close()

def durum_olaylari_getir(personel_id=None, sadece_bekleyen=False):
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    try:
        kosul=[];params=[]
        if personel_id is not None:
            kosul.append("o.personel_id=?");params.append(int(personel_id))
        if sadece_bekleyen:
            kosul.append("o.durum IN ('AMİR BEKLİYOR','YÖNETİCİ BEKLİYOR','YÖNETİCİ İNCELEMESİ')")
        where=("WHERE "+" AND ".join(kosul)) if kosul else ""
        rows=baglanti.execute(f"""
            SELECT o.*,p.isim,p.soyisim,p.sicil_no,
                   COALESCE(s.sube_adi,'Şube Atanmamış') AS sube_adi,
                   (SELECT COUNT(*) FROM personel_belgeleri b WHERE b.olay_id=o.olay_id) AS belge_sayisi
            FROM durum_olaylari o
            JOIN personeller p ON p.id=o.personel_id
            LEFT JOIN subeler s ON s.sube_id=p.sube_id
            {where}
            ORDER BY o.olay_id DESC
        """,params).fetchall()
        return [dict(x) for x in rows]
    finally:
        baglanti.close()

def amir_durum_karari(amir_personel_id, olay_id, karar):
    karar=str(karar or "").upper()
    if karar not in ("ONAYLANDI","REDDEDİLDİ"):
        return False,"Geçersiz karar."
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    try:
        o=baglanti.execute("""
            SELECT * FROM durum_olaylari
            WHERE olay_id=? AND amir_personel_id=? AND durum='AMİR BEKLİYOR'
        """,(int(olay_id),int(amir_personel_id))).fetchone()
        if not o:return False,"Amir kararına açık kayıt bulunamadı."
        # Amir reddetse de kayıt kaybolmaz; yönetici incelemesine gider.
        yeni="YÖNETİCİ BEKLİYOR" if karar=="ONAYLANDI" else "YÖNETİCİ İNCELEMESİ"
        baglanti.execute("""
            UPDATE durum_olaylari SET amir_karari=?,amir_karar_zamani=?,durum=? WHERE olay_id=?
        """,(karar,turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"),yeni,int(olay_id)))
        baglanti.commit();return True,("Amir onayı kaydedildi; yönetici onayı bekleniyor." if karar=="ONAYLANDI" else "Amir onaylamadı; kayıt yönetici incelemesine gönderildi.")
    except Exception as exc:
        baglanti.rollback();return False,str(exc)
    finally:
        baglanti.close()

def yonetici_durum_karari(olay_id, karar, aciklama=""):
    karar=str(karar or "").upper()
    if karar not in ("ONAYLANDI","REDDEDİLDİ"):
        return False,"Geçersiz karar."
    baglanti=baglanti_ac()
    try:
        cur=baglanti.execute("""
            UPDATE durum_olaylari
            SET yonetici_karari=?,yonetici_karar_zamani=?,yonetici_aciklamasi=?,durum=?
            WHERE olay_id=? AND durum IN ('YÖNETİCİ BEKLİYOR','YÖNETİCİ İNCELEMESİ','BİLDİRİLDİ')
        """,(karar,turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"),str(aciklama or "")[:1000],karar,int(olay_id)))
        baglanti.commit()
        return (cur.rowcount>0, "Yönetici kararı kaydedildi." if cur.rowcount else "Karara açık kayıt bulunamadı.")
    except Exception as exc:
        baglanti.rollback();return False,str(exc)
    finally:
        baglanti.close()

def aktif_durum_olayi(personel_id,tarih):
    """Puantajı etkileyen en yüksek öncelikli olay."""
    gun=tarih.isoformat() if hasattr(tarih,"isoformat") else str(tarih)
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    try:
        rows=baglanti.execute("""
            SELECT * FROM durum_olaylari
            WHERE personel_id=? AND baslangic_tarihi<=? AND bitis_tarihi>=?
              AND (
                 (olay_turu='HASTALIK_RAPORU' AND durum IN ('BİLDİRİLDİ','ONAYLANDI'))
                 OR
                 (olay_turu<>'HASTALIK_RAPORU' AND durum='ONAYLANDI')
              )
            ORDER BY CASE WHEN olay_turu='HASTALIK_RAPORU' THEN 1 ELSE 2 END DESC, olay_id DESC
        """,(int(personel_id),gun,gun)).fetchall()
        return dict(rows[0]) if rows else None
    finally:
        baglanti.close()

def yonetici_manuel_durum_kaydet(personel_id,tarih,yeni_durum,aciklama,yonetici="Yönetici"):
    if not str(aciklama or "").strip():
        return False,"Manuel düzeltmede açıklama zorunludur."
    baglanti=baglanti_ac()
    try:
        baglanti.execute("""
            INSERT INTO yonetici_duzeltmeleri
            (personel_id,tarih,alan,eski_deger,yeni_deger,aciklama,yonetici,zaman)
            VALUES(?,?,'GUNLUK_DURUM',NULL,?,?,?,?)
        """,(int(personel_id),str(tarih),str(yeni_durum),str(aciklama)[:1000],yonetici,
             turkiye_saati().strftime("%Y-%m-%d %H:%M:%S")))
        baglanti.commit();return True,"Manuel durum düzeltmesi kaydedildi."
    except Exception as exc:
        baglanti.rollback();return False,str(exc)
    finally:
        baglanti.close()

def yonetici_manuel_durum_getir(personel_id,tarih):
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    try:
        r=baglanti.execute("""
            SELECT yeni_deger,aciklama,yonetici,zaman FROM yonetici_duzeltmeleri
            WHERE personel_id=? AND tarih=? AND alan='GUNLUK_DURUM'
            ORDER BY duzeltme_id DESC LIMIT 1
        """,(int(personel_id),str(tarih))).fetchone()
        return dict(r) if r else None
    finally:
        baglanti.close()

def tum_loglari_getir_api():
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()
    try:
        imlec.execute("""
            SELECT l.log_id AS id, l.personel_id, l.islem_turu,
                   l.zaman AS zaman_damgasi,
                   COALESCE(s.sube_adi, 'Bilinmeyen Şube') AS sube_adi,
                   COALESCE(l.durum_etiketi, 'NORMAL') AS durum,
                   COALESCE(p.isim || ' ' || p.soyisim,
                            'Personel (ID: ' || l.personel_id || ')') AS personel_ad_soyad
            FROM loglar l
            LEFT JOIN personeller p ON p.id = l.personel_id
            LEFT JOIN subeler s ON s.sube_id = l.sube_id
            ORDER BY l.log_id DESC
        """)
        return [dict(satir) for satir in imlec.fetchall()]
    except Exception as e:
        print(f"Log cekme hatasi: {e}")
        return []
    finally:
        baglanti.close()

PERSONEL_EK_ALANLARI = [
    "tc_kimlik_no", "eposta", "cinsiyet", "dogum_tarihi", "dogum_yeri",
    "medeni_durum", "uyruk", "il", "ilce", "mahalle", "acik_adres",
    "posta_kodu", "acil_kisi", "acil_telefon", "acil_yakinlik",
    "ise_giris_tarihi", "personel_turu", "ogrenim_durumu", "okul", "bolum",
    "mezuniyet_yili", "mezuniyet_durumu", "askerlik_durumu", "terhis_tarihi",
    "tecil_bitis_tarihi", "askerlik_aciklama", "sgk_sicil_no", "meslek_kodu",
    "kan_grubu", "ehliyet_sinifi", "yonetici_notu", "mesai_baslangic", "mesai_bitis",
    "personel_tolerans_dakika", "calisma_gunleri", "foto_mime", "foto_base64"
]

def personel_ekle(isim, soyisim, departman, maas, calisma_modeli,
                  sicil_no=None, telefon=None, gorev=None, sube_id=None, aktif=1,
                  **ek_alanlar):
    try:
        baglanti = baglanti_ac()
        imlec = baglanti.cursor()
        alanlar = ["isim", "soyisim", "departman", "maas", "calisma_modeli",
                   "sicil_no", "telefon", "gorev", "sube_id", "aktif",
                   "cihaz_id", "gizli_anahtar"] + PERSONEL_EK_ALANLARI
        degerler = [isim, soyisim, departman, float(maas), calisma_modeli,
                    sicil_no or None, telefon or None, gorev or None,
                    int(sube_id) if sube_id else None, int(aktif), "EŞLEŞMEDİ",
                    pyotp.random_base32()] + [ek_alanlar.get(a) or None for a in PERSONEL_EK_ALANLARI]
        imlec.execute(
            f"INSERT INTO personeller ({','.join(alanlar)}) VALUES ({','.join(['?'] * len(alanlar))})",
            degerler
        )
        baglanti.commit()
        baglanti.close()
        return True, "Personel başarıyla veritabanına eklendi."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def personel_sil(personel_id):
    try:
        baglanti = baglanti_ac()
        imlec = baglanti.cursor()
        imlec.execute("UPDATE personeller SET aktif = 0 WHERE id = ?", (int(personel_id),))
        if imlec.rowcount == 0:
            baglanti.close()
            return False, "Personel bulunamadı."
        baglanti.commit()
        baglanti.close()
        return True, "Personel pasif duruma alındı; geçmiş kayıtları korundu."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def tum_personelleri_getir():
    try:
        baglanti = baglanti_ac()
        baglanti.row_factory = sqlite3.Row
        imlec = baglanti.cursor()
        imlec.execute("""
            SELECT p.*,
                   COALESCE(s.sube_adi, 'Şube Atanmamış') AS sube_adi
            FROM personeller p
            LEFT JOIN subeler s ON s.sube_id = p.sube_id
            ORDER BY p.isim, p.soyisim
        """)
        veriler = [dict(satir) for satir in imlec.fetchall()]
        baglanti.close()
        return veriler
    except Exception:
        return []

def personel_subelerini_getir(personel_id, sadece_aktif=False):
    """Personelin ana, ek ve tarihli geçici şube yetkilerini döndürür."""
    try:
        baglanti = baglanti_ac()
        baglanti.row_factory = sqlite3.Row
        imlec = baglanti.cursor()
        kosul = ""
        parametreler = [int(personel_id)]
        if sadece_aktif:
            bugun = turkiye_saati().strftime("%Y-%m-%d")
            kosul = """AND ps.aktif=1
                AND (ps.baslangic_tarihi IS NULL OR ps.baslangic_tarihi='' OR ps.baslangic_tarihi<=?)
                AND (ps.bitis_tarihi IS NULL OR ps.bitis_tarihi='' OR ps.bitis_tarihi>=?)"""
            parametreler.extend([bugun, bugun])
        imlec.execute(f"""
            SELECT ps.sube_id, s.sube_adi, ps.ana_sube,
                   ps.baslangic_tarihi, ps.bitis_tarihi, ps.aktif
            FROM personel_subeleri ps
            JOIN subeler s ON s.sube_id=ps.sube_id
            WHERE ps.personel_id=? {kosul}
            ORDER BY ps.ana_sube DESC, s.sube_adi
        """, parametreler)
        sonuc = [dict(satir) for satir in imlec.fetchall()]
        baglanti.close()
        return sonuc
    except Exception:
        return []

def personel_subelerini_ayarla(personel_id, ana_sube_id, ek_atamalar):
    """Formdaki güncel listeyi tek işlemde kaydeder; ana şube eski sütunda da korunur."""
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    try:
        personel_id = int(personel_id)
        ana = int(ana_sube_id) if ana_sube_id else None
        temiz = []
        gorulen = set()
        if ana is not None:
            temiz.append((ana, 1, None, None, 1))
            gorulen.add(ana)
        for atama in ek_atamalar or []:
            sube = int(atama.get("sube_id"))
            if sube in gorulen:
                continue
            baslangic = str(atama.get("baslangic_tarihi") or "").strip() or None
            bitis = str(atama.get("bitis_tarihi") or "").strip() or None
            if baslangic and bitis and baslangic > bitis:
                raise ValueError("Geçici şube başlangıç tarihi bitiş tarihinden sonra olamaz.")
            temiz.append((sube, 0, baslangic, bitis, 1))
            gorulen.add(sube)
        if gorulen:
            yerler = ",".join(["?"] * len(gorulen))
            imlec.execute(f"SELECT COUNT(*) FROM subeler WHERE sube_id IN ({yerler})", list(gorulen))
            if imlec.fetchone()[0] != len(gorulen):
                raise ValueError("Seçilen şubelerden biri artık mevcut değil.")
        imlec.execute("UPDATE personeller SET sube_id=? WHERE id=?", (ana, personel_id))
        if imlec.rowcount == 0:
            raise ValueError("Personel bulunamadı.")
        imlec.execute("DELETE FROM personel_subeleri WHERE personel_id=?", (personel_id,))
        for sube, ana_mi, baslangic, bitis, aktif in temiz:
            imlec.execute("""
                INSERT INTO personel_subeleri
                    (personel_id, sube_id, ana_sube, baslangic_tarihi, bitis_tarihi, aktif)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (personel_id, sube, ana_mi, baslangic, bitis, aktif))
        baglanti.commit()
        return True, "Şube yetkileri güncellendi."
    except Exception as exc:
        baglanti.rollback()
        return False, str(exc)
    finally:
        baglanti.close()

def sube_ekle(sube_adi, enlem, boylam, guvenli_yari_cap):
    try:
        baglanti = baglanti_ac()
        imlec = baglanti.cursor()
        imlec.execute("""
            INSERT INTO subeler (
                sube_adi, enlem, boylam, guvenli_yari_cap
            ) VALUES (?, ?, ?, ?)
        """, (sube_adi, float(enlem), float(boylam), int(guvenli_yari_cap)))
        baglanti.commit()
        baglanti.close()
        return True, "Coğrafi çit lokasyonu başarıyla tanımlandı."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def sube_sil(sube_id):
    try:
        baglanti = baglanti_ac()
        imlec = baglanti.cursor()
        imlec.execute("SELECT COUNT(*) FROM personel_subeleri WHERE sube_id = ?", (int(sube_id),))
        if imlec.fetchone()[0] > 0:
            baglanti.close()
            return False, "Bu şubeye yetkili personeller bulunduğu için şube silinemez."
        imlec.execute("DELETE FROM subeler WHERE sube_id = ?", (int(sube_id),))
        baglanti.commit()
        baglanti.close()
        return True, "Lokasyon/Şube sistemden kaldırıldı."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def tum_subeleri_getir():
    try:
        baglanti = baglanti_ac()
        baglanti.row_factory = sqlite3.Row
        imlec = baglanti.cursor()
        
        # KESİN ÇÖZÜM: Gerçek sütun adı olan sube_id'yi çekip arayüze 'id' olarak takdim ediyoruz
        imlec.execute("SELECT sube_id AS id, sube_adi, enlem, boylam, guvenli_yari_cap FROM subeler")
        
        veriler = [dict(satir) for satir in imlec.fetchall()]
        baglanti.close()
        return veriler
    except Exception as e:
        print(f"Veritabanindan sube cekilirken hata olustu: {e}")
        return []


def personel_guncelle(p_id, isim, soyisim, departman, maas, calisma_modeli,
                      sicil_no=None, telefon=None, gorev=None, sube_id=None, aktif=1,
                      **ek_alanlar):
    try:
        baglanti = baglanti_ac()
        imlec = baglanti.cursor()
        atanacaklar = ["isim", "soyisim", "departman", "maas", "calisma_modeli",
                       "sicil_no", "telefon", "gorev", "sube_id", "aktif"]
        degerler = [isim, soyisim, departman, float(maas), calisma_modeli,
                    sicil_no or None, telefon or None, gorev or None,
                    int(sube_id) if sube_id else None, int(aktif)]
        for alan in PERSONEL_EK_ALANLARI:
            if alan in ek_alanlar and ek_alanlar[alan] is not None:
                atanacaklar.append(alan)
                degerler.append(ek_alanlar[alan] or None)
        degerler.append(int(p_id))
        imlec.execute(
            f"UPDATE personeller SET {','.join(a + '=?' for a in atanacaklar)} WHERE id=?",
            degerler
        )
        baglanti.commit()
        baglanti.close()
        return True, "Personel bilgileri güncellendi."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def sube_guncelle(s_id, sube_adi, enlem, boylam, guvenli_yari_cap):
    try:
        baglanti = baglanti_ac()
        imlec = baglanti.cursor()
        imlec.execute("""
            UPDATE subeler 
            SET sube_adi=?, enlem=?, boylam=?, guvenli_yari_cap=?
            WHERE sube_id=?
        """, (sube_adi, float(enlem), float(boylam), int(guvenli_yari_cap), int(s_id)))
        baglanti.commit()
        baglanti.close()
        return True, "Lokasyon/Şube ayarları güncellendi."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def personel_sicil_ile_getir(sicil_no):
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()
    imlec.execute("""
        SELECT p.id, p.isim, p.soyisim, p.sicil_no, p.cihaz_id,
               p.cihaz_token_hash, p.personel_pin_hash, p.pin_hata_sayisi,
               p.pin_kilit_bitis, p.aktif, p.sube_id,
               COALESCE(s.sube_adi, 'Şube Atanmamış') AS sube_adi
        FROM personeller p
        LEFT JOIN subeler s ON s.sube_id = p.sube_id
        WHERE UPPER(TRIM(p.sicil_no)) = UPPER(TRIM(?))
    """, (sicil_no,))
    kayit = imlec.fetchone()
    baglanti.close()
    return dict(kayit) if kayit else None

def cihaz_kurulumunu_tamamla(personel_id, cihaz_id, token_hash):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("""
        UPDATE personeller SET cihaz_id = ?, cihaz_token_hash = ?
        WHERE id = ? AND aktif = 1
    """, (cihaz_id, token_hash, int(personel_id)))
    basarili = imlec.rowcount == 1
    baglanti.commit()
    baglanti.close()
    return basarili

def personel_pin_kaydet(personel_id, pin):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("UPDATE personeller SET personel_pin_hash=? WHERE id=? AND personel_pin_hash IS NULL", (sifre_hashle(pin), int(personel_id)))
    basarili = imlec.rowcount == 1
    baglanti.commit()
    baglanti.close()
    return basarili

def personel_pin_dogrula(personel, pin):
    return bool(personel.get("personel_pin_hash") and sifre_dogrula(pin, personel["personel_pin_hash"]))

def personel_pin_kilitli_mi(personel):
    deger = personel.get("pin_kilit_bitis")
    if not deger:
        return False, 0
    try:
        bitis = datetime.datetime.strptime(str(deger), "%Y-%m-%d %H:%M:%S")
        kalan = int((bitis - turkiye_saati()).total_seconds())
        return kalan > 0, max(0, (kalan + 59) // 60)
    except (TypeError, ValueError):
        return False, 0

def personel_pin_deneme_kaydet(personel_id, basarili):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    if basarili:
        imlec.execute("UPDATE personeller SET pin_hata_sayisi=0, pin_kilit_bitis=NULL WHERE id=?", (int(personel_id),))
    else:
        imlec.execute("SELECT COALESCE(pin_hata_sayisi,0) FROM personeller WHERE id=?", (int(personel_id),))
        satir = imlec.fetchone()
        sayi = int(satir[0] if satir else 0) + 1
        kilit = (turkiye_saati() + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S") if sayi >= 5 else None
        imlec.execute("UPDATE personeller SET pin_hata_sayisi=?, pin_kilit_bitis=? WHERE id=?", (0 if kilit else sayi, kilit, int(personel_id)))
    baglanti.commit()
    baglanti.close()

def personeli_cihazla_dogrula(cihaz_id, token_hash):
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()
    imlec.execute("""
        SELECT id, isim, soyisim, aktif, sube_id
        FROM personeller
        WHERE cihaz_id = ? AND cihaz_token_hash = ?
    """, (cihaz_id, token_hash))
    kayit = imlec.fetchone()
    baglanti.close()
    return dict(kayit) if kayit else None

def cihaz_kaydini_sifirla(personel_id):
    baglanti = baglanti_ac()
    imlec = baglanti.cursor()
    imlec.execute("""
        UPDATE personeller
        SET cihaz_id = 'EŞLEŞMEDİ', cihaz_token_hash = NULL, personel_pin_hash = NULL
        WHERE id = ?
    """, (int(personel_id),))
    basarili = imlec.rowcount == 1
    baglanti.commit()
    baglanti.close()
    return basarili

def hata_logu_yaz(personel_id, islem, hata_kodu, mesaj):
    baglanti = baglanti_ac()
    baglanti.execute("""
        INSERT INTO hata_loglari (personel_id, zaman, islem, hata_kodu, mesaj)
        VALUES (?, ?, ?, ?, ?)
    """, (personel_id, turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"), islem, hata_kodu, mesaj))
    baglanti.commit()
    baglanti.close()

def personel_amir_ata(personel_id, amir_personel_id):
    """Personelin ilgili amirini atomik ve SQLite/PostgreSQL uyumlu biçimde kaydeder."""
    baglanti = baglanti_ac()
    try:
        personel_id = int(personel_id)
        amir_metni = str(amir_personel_id or "").strip()

        personel = baglanti.execute("SELECT id FROM personeller WHERE id=?", (personel_id,)).fetchone()
        if not personel:
            raise ValueError("Personel bulunamadı.")

        if not amir_metni:
            baglanti.execute("DELETE FROM personel_amirleri WHERE personel_id=?", (personel_id,))
        else:
            amir_id = int(amir_metni)
            if personel_id == amir_id:
                raise ValueError("Personel kendi amiri olamaz.")
            amir = baglanti.execute("SELECT id FROM personeller WHERE id=? AND aktif=1", (amir_id,)).fetchone()
            if not amir:
                raise ValueError("Seçilen amir bulunamadı veya aktif değil.")
            baglanti.execute("""
                INSERT INTO personel_amirleri(personel_id, amir_personel_id, aktif)
                VALUES(?,?,1)
                ON CONFLICT(personel_id) DO UPDATE SET
                    amir_personel_id=excluded.amir_personel_id,
                    aktif=1
            """, (personel_id, amir_id))
        baglanti.commit()
        return True, "Amir ataması kaydedildi."
    except Exception as exc:
        baglanti.rollback()
        return False, str(exc)
    finally:
        baglanti.close()

def personel_amir_id_getir(personel_id):
    baglanti=baglanti_ac(); s=baglanti.execute("SELECT amir_personel_id FROM personel_amirleri WHERE personel_id=? AND aktif=1",(int(personel_id),)).fetchone(); baglanti.close(); return s[0] if s else None

def duzeltme_talebi_olustur(personel_id, talep_turu, istenen_zaman="", aciklama="", kaynak="PERSONEL", log_id=None):
    izinli={"GİRİŞ UNUTULDU","ÇIKIŞ UNUTULDU","İNTERNET YOKTU","HASTALIK İZNİ","YILLIK İZİN","MAZERET İZNİ","ÜCRETSİZ İZİN","RAPORLU","GÖREVLİ","İŞE GELMEDİ","DİĞER"}
    tur=str(talep_turu or "").strip().upper()
    if tur not in izinli:return False,"Geçersiz talep türü."
    if len(str(aciklama or ""))>1000:return False,"Açıklama çok uzun."
    amir=personel_amir_id_getir(personel_id); baglanti=baglanti_ac()
    try:
        # Manuel saat düzeltmesinde hedef kaydı talep oluşturulurken sabitle.
        # Böylece onay anında farklı/yanlış bir logun tahmin edilmesi engellenir.
        hedef_log_id = log_id
        istenen = str(istenen_zaman or "").strip().replace("T", " ")
        if hedef_log_id is None and tur in ("GİRİŞ UNUTULDU", "ÇIKIŞ UNUTULDU") and istenen:
            try:
                try:
                    dt = datetime.datetime.strptime(istenen, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    dt = datetime.datetime.strptime(istenen, "%Y-%m-%d %H:%M")
                gun_baslangic = dt.strftime("%Y-%m-%d 00:00:00")
                gun_bitis = dt.strftime("%Y-%m-%d 23:59:59")
                islem = "GİRİŞ" if tur == "GİRİŞ UNUTULDU" else "ÇIKIŞ"
                siralama = "ASC" if islem == "GİRİŞ" else "DESC"
                aday = baglanti.execute(
                    f"SELECT log_id FROM loglar WHERE personel_id=? AND islem_turu=? AND zaman>=? AND zaman<=? ORDER BY zaman {siralama}, log_id {siralama} LIMIT 1",
                    (int(personel_id), islem, gun_baslangic, gun_bitis)
                ).fetchone()
                if aday:
                    hedef_log_id = aday[0] if not isinstance(aday, dict) else aday.get("log_id")
            except ValueError:
                pass

        baglanti.execute("""INSERT INTO duzeltme_talepleri(personel_id,amir_personel_id,log_id,talep_turu,talep_zamani,istenen_zaman,aciklama,kaynak,durum) VALUES(?,?,?,?,?,?,?,?, 'BEKLİYOR')""",
                         (int(personel_id),amir,hedef_log_id,tur,turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"),str(istenen_zaman or "").strip() or None,str(aciklama or "").strip(),kaynak))
        baglanti.commit();return True,"Talebiniz amir onayına gönderildi." if amir else "Talebiniz yönetici onayına gönderildi."
    except Exception as exc:baglanti.rollback();return False,str(exc)
    finally:baglanti.close()

def duzeltme_talepleri_getir(personel_id=None, amir_personel_id=None, tumu=False):
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    kosul=[];deger=[]
    if personel_id is not None:kosul.append("d.personel_id=?");deger.append(int(personel_id))
    if amir_personel_id is not None:kosul.append("d.amir_personel_id=?");deger.append(int(amir_personel_id))
    if not tumu:kosul.append("d.durum='BEKLİYOR'")
    where=" WHERE "+" AND ".join(kosul) if kosul else ""
    satirlar=baglanti.execute("""SELECT d.*,p.isim||' '||p.soyisim AS personel, a.isim||' '||a.soyisim AS amir FROM duzeltme_talepleri d JOIN personeller p ON p.id=d.personel_id LEFT JOIN personeller a ON a.id=d.amir_personel_id"""+where+" ORDER BY d.talep_zamani DESC",tuple(deger)).fetchall();baglanti.close();return [dict(x) for x in satirlar]

def duzeltme_talebi_kararla(talep_id, karar, duzeltilmis_zaman="", aciklama="", karar_veren="Yönetici"):
    karar = str(karar or "").upper()
    if karar not in ("ONAYLANDI", "REDDEDİLDİ"):
        return False, "Geçersiz karar."
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    try:
        t = baglanti.execute(
            "SELECT * FROM duzeltme_talepleri WHERE talep_id=? AND durum='BEKLİYOR'",
            (int(talep_id),)
        ).fetchone()
        if not t:
            return False, "Bekleyen talep bulunamadı."

        zaman = str(duzeltilmis_zaman or t["istenen_zaman"] or "").strip().replace("T", " ")
        uygulanan_zaman = None
        if karar == "ONAYLANDI" and t["talep_turu"] in ("GİRİŞ UNUTULDU", "ÇIKIŞ UNUTULDU", "İNTERNET YOKTU"):
            if not zaman:
                return False, "Onay için düzeltilmiş tarih ve saat zorunludur."
            try:
                dt = datetime.datetime.strptime(zaman, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.datetime.strptime(zaman, "%Y-%m-%d %H:%M")
            yeni_zaman = dt.strftime("%Y-%m-%d %H:%M:%S")
            uygulanan_zaman = yeni_zaman
            islem = "ÇIKIŞ" if t["talep_turu"] == "ÇIKIŞ UNUTULDU" else "GİRİŞ"

            # Önce talebe bağlı logu doğrula. Sistem kaynaklı ÇIKIŞ UNUTULDU
            # talebi çoğu zaman eksik çıkıştan önceki GİRİŞ loguna bağlıdır.
            bagli_log = None
            hedef_log = None
            if t["log_id"]:
                bagli_log = baglanti.execute(
                    "SELECT log_id,islem_turu,zaman FROM loglar WHERE log_id=? AND personel_id=?",
                    (t["log_id"], t["personel_id"])
                ).fetchone()
                if bagli_log and bagli_log["islem_turu"] == islem:
                    hedef_log = bagli_log["log_id"]

            # Seçilen gün içinde hedef türde bir kayıt varsa onu güncelle. Bu,
            # daha önce yanlış saatte oluşmuş ÇIKIŞ kaydının yanına ikinci bir
            # kayıt eklenmesini ve personel ekranında eski saatin kalmasını önler.
            gun_baslangic = dt.strftime("%Y-%m-%d 00:00:00")
            gun_bitis = dt.strftime("%Y-%m-%d 23:59:59")
            if hedef_log is None:
                siralama = "ASC" if islem == "GİRİŞ" else "DESC"
                aday = baglanti.execute(
                    f"SELECT log_id FROM loglar WHERE personel_id=? AND islem_turu=? AND zaman>=? AND zaman<=? ORDER BY zaman {siralama}, log_id {siralama} LIMIT 1",
                    (t["personel_id"], islem, gun_baslangic, gun_bitis)
                ).fetchone()
                if aday:
                    hedef_log = aday["log_id"]

            if hedef_log is not None:
                sonuc = baglanti.execute(
                    "UPDATE loglar SET zaman=?, durum_etiketi='DÜZELTİLDİ' WHERE log_id=? AND personel_id=?",
                    (yeni_zaman, hedef_log, t["personel_id"])
                )
                if sonuc.rowcount != 1:
                    raise RuntimeError("Saat düzeltmesi ilgili hareket kaydına uygulanamadı.")
            else:
                sonuc = baglanti.execute("""
                    INSERT INTO loglar(personel_id,islem_turu,zaman,enlem,boylam,sube_id,durum_etiketi)
                    SELECT ?,?,?,0,0,sube_id,'DÜZELTİLDİ' FROM personeller WHERE id=?
                """, (t["personel_id"], islem, yeni_zaman, t["personel_id"]))
                if sonuc.rowcount != 1:
                    raise RuntimeError("Düzeltilmiş hareket kaydı oluşturulamadı.")

            # Eksik çıkış talebi bir GİRİŞ loguna bağlıysa, çıkış başarıyla
            # uygulandıktan sonra o girişteki 'EKSİK ÇIKIŞ' işaretini de temizle.
            if bagli_log and t["talep_turu"] == "ÇIKIŞ UNUTULDU" and bagli_log["islem_turu"] == "GİRİŞ":
                baglanti.execute(
                    "UPDATE loglar SET durum_etiketi='DÜZELTİLDİ' WHERE log_id=? AND durum_etiketi='EKSİK ÇIKIŞ'",
                    (bagli_log["log_id"],)
                )

        baglanti.execute(
            "UPDATE duzeltme_talepleri SET durum=?,istenen_zaman=COALESCE(?,istenen_zaman),karar_zamani=?,karar_veren=?,karar_aciklamasi=? WHERE talep_id=?",
            (karar, uygulanan_zaman, turkiye_saati().strftime("%Y-%m-%d %H:%M:%S"), karar_veren, str(aciklama or ""), int(talep_id))
        )
        baglanti.commit()
        return True, (f"Talep sonuçlandırıldı. Uygulanan saat: {uygulanan_zaman[11:16]}" if uygulanan_zaman else "Talep sonuçlandırıldı.")
    except Exception as exc:
        baglanti.rollback()
        return False, str(exc)
    finally:
        baglanti.close()


SISTEM_GECIKME_GUVENLIK_DAKIKA = 30

HAFTA_GUN_KISALTMALARI = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"]

def _calisma_gunu_mu(calisma_gunleri, tarih):
    # Eski kayitlarda gunler farkli yazimlarla tutulmus olabilir
    # (Pzt / Pazartesi / PAZARTESI, virgül veya noktalı virgül).
    # Panelin devamsizlik sayacinin bu nedenle personeli atlamasini engelle.
    ham = str(calisma_gunleri or "Pzt,Sal,Çar,Per,Cum").replace(";", ",")
    tr = str.maketrans({"İ":"I","I":"I","ı":"i","Ş":"S","ş":"s","Ğ":"G","ğ":"g","Ü":"U","ü":"u","Ö":"O","ö":"o","Ç":"C","ç":"c"})
    alias = {
        "pzt":0,"pazartesi":0,"monday":0,
        "sal":1,"sali":1,"tuesday":1,
        "car":2,"carsamba":2,"wednesday":2,
        "per":3,"persembe":3,"thursday":3,
        "cum":4,"cuma":4,"friday":4,
        "cmt":5,"cumartesi":5,"saturday":5,
        "paz":6,"pazar":6,"sunday":6,
    }
    secilen=set()
    for parca in ham.split(","):
        anahtar=parca.strip().translate(tr).lower().replace(" ","")
        if anahtar in alias:
            secilen.add(alias[anahtar])
    # Alan bozuk/bos ise eski sistem davranisini koru: hafta ici.
    if not secilen:
        secilen={0,1,2,3,4}
    return tarih.weekday() in secilen

def _dakika_farki(giris, cikis):
    if not giris or not cikis or cikis < giris:
        return 0
    return int((cikis-giris).total_seconds()//60)

def gunluk_personel_durumlari(tarih=None, simdi=None, personel_id=None):
    """Tek gerçek kaynak: panel, sicil, hatırlatma ve Excel bu sonucu kullanır."""
    simdi = simdi or turkiye_saati()
    if tarih is None:
        tarih = simdi.date()
    elif isinstance(tarih, str):
        tarih = datetime.datetime.strptime(tarih, "%Y-%m-%d").date()

    gun=tarih.isoformat()
    bas=gun+" 00:00:00"; bit=gun+" 23:59:59"
    baglanti=baglanti_ac();baglanti.row_factory=sqlite3.Row
    sonuc=[]
    try:
        # PostgreSQL, NULL gelen bağsız bir parametrenin tipini "? IS NULL" kalıbında
        # her zaman çıkaramaz. Filtreyi SQL'e yalnız personel_id gerçekten varsa ekle.
        personel_sql="""
            SELECT p.id,p.isim,p.soyisim,p.sicil_no,p.calisma_modeli,p.mesai_baslangic,
                   p.mesai_bitis,p.personel_tolerans_dakika,p.calisma_gunleri,p.vardiya_grubu,
                   p.ise_giris_tarihi,p.aktif,
                   COALESCE(s.sube_adi,'Şube Atanmamış') AS sube_adi
            FROM personeller p LEFT JOIN subeler s ON s.sube_id=p.sube_id
            WHERE p.aktif=1
        """
        personel_params=[]
        if personel_id is not None:
            personel_sql += " AND p.id=?"
            personel_params.append(int(personel_id))
        personel_sql += " ORDER BY p.isim,p.soyisim"
        personeller=baglanti.execute(personel_sql, tuple(personel_params)).fetchall()

        for p in personeller:
            model=str(p["calisma_modeli"] or "SABİT").upper()
            grup=str(p["vardiya_grubu"] or "YOK").upper()
            calisma_gunu=_calisma_gunu_mu(p["calisma_gunleri"],tarih)
            vardiya_var=not(model=="VARDİYA" and grup in ("","YOK","NONE","NULL"))
            planli=calisma_gunu and vardiya_var

            # İşe giriş tarihinden önce devamsızlık üretme.
            if p["ise_giris_tarihi"]:
                try:
                    if tarih < datetime.datetime.strptime(str(p["ise_giris_tarihi"])[:10],"%Y-%m-%d").date():
                        sonuc.append({
                            "personel_id":p["id"],"personel":f"{p['isim']} {p['soyisim']}".strip(),
                            "sicil_no":p["sicil_no"] or "","sube":p["sube_adi"],"calisma_modeli":model,
                            "vardiya_grubu":p["vardiya_grubu"] or "YOK","tarih":gun,"planli_calisma":False,
                            "planlanan_giris":"","planlanan_cikis":"","durum":"İŞE BAŞLAMADI",
                            "ilk_giris":"","son_cikis":"","toplam_dakika":0,"gec_dakika":0,"erken_cikis_dakika":0,
                            "detay":"Personelin işe giriş tarihinden önceki gün.","kaynak":"PLAN"
                        })
                        continue
                except Exception: pass

            loglar=baglanti.execute("""
                SELECT log_id,islem_turu,zaman,durum_etiketi
                FROM loglar WHERE personel_id=? AND zaman>=? AND zaman<=?
                ORDER BY zaman,log_id
            """,(p["id"],bas,bit)).fetchall()

            hareket=[]
            for l in loglar:
                try:
                    an=datetime.datetime.strptime(str(l["zaman"])[:19],"%Y-%m-%d %H:%M:%S")
                    hareket.append((str(l["islem_turu"]).upper(),an))
                except Exception: pass

            # Giriş/çıkış çiftlerini sırayla eşleştir. Ara süre çalışma sayılmaz.
            acik=None; toplam=0; girisler=[]; cikislar=[]; eksik_giris=False
            for tur,an in hareket:
                if tur=="GİRİŞ":
                    girisler.append(an)
                    if acik is None: acik=an
                    # Arka arkaya ikinci giriş varsa önceki açık giriş eksik çıkış olarak kalır.
                elif tur=="ÇIKIŞ":
                    cikislar.append(an)
                    if acik is not None and an>=acik:
                        toplam+=int((an-acik).total_seconds()//60);acik=None
                    else:
                        eksik_giris=True

            ilk=min(girisler) if girisler else None
            son=max(cikislar) if cikislar else None
            plan_g=str(p["mesai_baslangic"] or "09:00")[:5]
            plan_c=str(p["mesai_bitis"] or "18:00")[:5]
            gec=0;erken=0
            try:
                plan_g_dt=datetime.datetime.strptime(gun+" "+plan_g,"%Y-%m-%d %H:%M")
                plan_c_dt=datetime.datetime.strptime(gun+" "+plan_c,"%Y-%m-%d %H:%M")
                if plan_c_dt <= plan_g_dt and model=="VARDİYA":
                    plan_c_dt += datetime.timedelta(days=1)
                if ilk:
                    gec=max(0,int((ilk-plan_g_dt).total_seconds()//60)-int(p["personel_tolerans_dakika"] or 20))
                if son and plan_c_dt.date()==tarih:
                    erken=max(0,int((plan_c_dt-son).total_seconds()//60))
            except Exception:
                plan_g_dt=None;plan_c_dt=None

            # Öncelik 1: Yönetici manuel düzeltmesi.
            manuel=yonetici_manuel_durum_getir(p["id"],gun)
            olay=aktif_durum_olayi(p["id"],tarih)

            durum="BEKLİYOR";detay="";kaynak="OTOMATİK"
            if manuel:
                durum=manuel["yeni_deger"];detay=f"Yönetici düzeltmesi: {manuel['aciklama']}";kaynak="YÖNETİCİ"
            elif olay:
                durum=OLAY_TURLERI.get(olay["olay_turu"],olay["olay_turu"])
                detay=olay.get("aciklama") or "Personel durum olayı sisteme işlendi."
                kaynak="RAPOR/BELGE" if olay["olay_turu"]=="HASTALIK_RAPORU" else "İZİN/GÖREV"
            elif model=="VARDİYA" and not vardiya_var:
                durum="VARDİYA YOK";detay="Aktif vardiya grubu tanımlı değil."
            elif not calisma_gunu:
                durum="HAFTA TATİLİ";detay="Bugün çalışma planında değil."
            elif eksik_giris or (cikislar and not girisler):
                durum="EKSİK GİRİŞ";detay="Çıkış kaydı var fakat eşleşen giriş yok."
            elif acik is not None:
                if tarih==simdi.date():
                    durum="ÇALIŞIYOR";detay="Giriş yapıldı; çıkış işlemi henüz yapılmadı."
                else:
                    durum="EKSİK ÇIKIŞ";detay="Giriş var, gün kapandı fakat çıkış yok."
            elif girisler and cikislar:
                durum="ÇALIŞTI"
                if gec>0: durum="GEÇ GELDİ"
                if erken>0 and durum=="ÇALIŞTI": durum="ERKEN ÇIKTI"
                detay=f"Net çalışma {toplam//60} sa {toplam%60} dk."
            elif model=="ESNEK":
                durum="ESNEK / KAYIT YOK";detay="Esnek personelde sabit saat üzerinden otomatik devamsızlık verilmedi."
            else:
                try:
                    tolerans=int(p["personel_tolerans_dakika"] or 20)
                    sinir=datetime.datetime.strptime(gun+" "+plan_g,"%Y-%m-%d %H:%M")+datetime.timedelta(minutes=tolerans)
                    kesin_sinir=sinir+datetime.timedelta(minutes=SISTEM_GECIKME_GUVENLIK_DAKIKA)
                    if tarih < simdi.date():
                        durum="İŞE GELMEDİ"
                        detay=f"Plan {plan_g}, tolerans {tolerans} dk; gün kapandı ve giriş bulunamadı."
                    elif simdi.replace(tzinfo=None) >= kesin_sinir:
                        durum="İŞE GELMEDİ"
                        detay=f"Plan {plan_g}, tolerans {tolerans} dk + {SISTEM_GECIKME_GUVENLIK_DAKIKA} dk sistem gecikme güvenliği geçti; giriş bulunamadı."
                    elif simdi.replace(tzinfo=None) >= sinir:
                        durum="KONTROL BEKLİYOR"
                        detay=f"Giriş henüz görünmüyor. Sunucu/ağ gecikmesine karşı {SISTEM_GECIKME_GUVENLIK_DAKIKA} dk güvenlik penceresi açık."
                    else:
                        durum="MESAİ BAŞLAMADI"
                        detay="Planlanan başlangıç+tolerans henüz geçmedi."
                except Exception:
                    durum="PLAN HATASI";detay="Çalışma planı geçersiz."

            sonuc.append({
                "personel_id":p["id"],"personel":f"{p['isim']} {p['soyisim']}".strip(),
                "sicil_no":p["sicil_no"] or "","sube":p["sube_adi"],"calisma_modeli":model,
                "vardiya_grubu":p["vardiya_grubu"] or "YOK","tarih":gun,"planli_calisma":bool(planli),
                "planlanan_giris":plan_g if planli else "—","planlanan_cikis":plan_c if planli else "—",
                "durum":durum,"ilk_giris":ilk.strftime("%H:%M:%S") if ilk else "—",
                "son_cikis":son.strftime("%H:%M:%S") if son else "—",
                "toplam_dakika":toplam,"gec_dakika":gec,"erken_cikis_dakika":erken,
                "detay":detay or durum,"kaynak":kaynak
            })
        return sonuc
    finally:
        baglanti.close()



def acik_devamsizliklari_getir(geri_gun=30, simdi=None):
    """APK sicil karti ile AYNI puantaj sonucunu kullanarak acik devamsizliklari getirir.

    Eski kod her gun icin tum personeli yeniden hesapliyordu. Bu hem yavasliyor hem de
    mobil sicil kartindaki sonuc ile yonetim panelinin farkli gorunmesine yol acabiliyordu.
    Artik her aktif personelin personel_mobil_ozeti() sonucu tek kaynak kabul edilir.
    """
    gun_sayisi=max(1,min(int(geri_gun or 30),90))
    baglanti=baglanti_ac()
    try:
        personel_ids=[r[0] for r in baglanti.execute(
            "SELECT id FROM personeller WHERE aktif=1 ORDER BY id"
        ).fetchall()]
    finally:
        baglanti.close()

    sonuc=[]
    for pid in personel_ids:
        veri=personel_mobil_ozeti(pid, gun_sayisi)
        if not veri:
            continue
        profil=veri.get("profil") or {}
        personel=f"{profil.get('isim','')} {profil.get('soyisim','')}".strip()
        for g in veri.get("gunler") or []:
            if g.get("durum") != "İŞE GELMEDİ":
                continue
            sonuc.append({
                "personel_id": pid,
                "personel": personel,
                "sicil_no": profil.get("sicil_no") or "",
                "sube": profil.get("sube_adi") or "Şube Atanmamış",
                "calisma_modeli": profil.get("calisma_modeli") or "SABİT",
                "tarih": g.get("tarih") or "",
                "planli_calisma": True,
                "planlanan_giris": g.get("planlanan_giris") or "—",
                "planlanan_cikis": g.get("planlanan_cikis") or "—",
                "durum": "İŞE GELMEDİ",
                "ilk_giris": g.get("ilk_giris") or "—",
                "son_cikis": g.get("son_cikis") or "—",
                "toplam_dakika": int(g.get("toplam_dakika") or 0),
                "gec_dakika": int(g.get("gec_dakika") or 0),
                "erken_cikis_dakika": int(g.get("erken_cikis_dakika") or 0),
                "detay": g.get("detay") or "Planlı çalışma gününde giriş kaydı bulunamadı.",
                "kaynak": g.get("kaynak") or "OTOMATİK"
            })
    sonuc.sort(key=lambda x:(x.get("tarih",""),x.get("personel","")),reverse=True)
    return sonuc

def gelmeyen_personelleri_kontrol_et(geri_gun=30):
    """
    Son N gündeki gerçek devamsızlıkları sisteme taşır.
    Aynı personel+tarih için ikinci kayıt oluşturmaz.
    """
    simdi=turkiye_saati()
    durumlar=acik_devamsizliklari_getir(geri_gun=geri_gun,simdi=simdi)
    baglanti=baglanti_ac()
    try:
        eklenen=0
        for d in durumlar:
            pid=d["personel_id"]
            gun=d["tarih"]
            mevcut=baglanti.execute("""
                SELECT 1 FROM duzeltme_talepleri
                WHERE personel_id=? AND talep_turu='İŞE GELMEDİ'
                  AND (istenen_zaman LIKE ? OR talep_zamani LIKE ?)
                LIMIT 1
            """,(pid,gun+"%",gun+"%")).fetchone()
            if mevcut: continue

            amir=baglanti.execute("""
                SELECT amir_personel_id FROM personel_amirleri
                WHERE personel_id=? AND aktif=1 LIMIT 1
            """,(pid,)).fetchone()

            # Talep zamanı bugünün sunucu zamanı; devamsız olunan gün istenen_zaman'da tutulur.
            baglanti.execute("""
                INSERT INTO duzeltme_talepleri
                (personel_id,amir_personel_id,talep_turu,talep_zamani,istenen_zaman,
                 aciklama,kaynak,durum)
                VALUES(?,?,'İŞE GELMEDİ',?,?,?,'SİSTEM','BEKLİYOR')
            """,(pid,amir[0] if amir else None,
                 simdi.strftime("%Y-%m-%d %H:%M:%S"),
                 gun+" 00:00:00",
                 d.get("detay") or "Planlı çalışma gününde giriş kaydı bulunamadı."))
            eklenen+=1
        baglanti.commit()
        return eklenen
    except Exception as exc:
        baglanti.rollback()
        print("İşe gelmeyen personel kontrol hatası:",repr(exc))
        return 0
    finally:
        baglanti.close()


def firma_ayarlarini_getir():
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    satir = baglanti.execute("SELECT gec_kalma_kontrolu, tolerans_dakika, test_modu FROM firma_ayarlari WHERE id=1").fetchone()
    baglanti.close()
    return dict(satir) if satir else {"gec_kalma_kontrolu": 0, "tolerans_dakika": 20, "test_modu": 0}

def firma_ayarlarini_guncelle(gec_kalma_kontrolu, tolerans_dakika, test_modu=0):
    tolerans = max(0, min(int(tolerans_dakika), 240))
    baglanti = baglanti_ac()
    baglanti.execute("UPDATE firma_ayarlari SET gec_kalma_kontrolu=?, tolerans_dakika=?, test_modu=? WHERE id=1",
                     (1 if int(gec_kalma_kontrolu) else 0, tolerans, 1 if int(test_modu) else 0))
    baglanti.commit(); baglanti.close()
    return True

def test_modu_acik_mi():
    try:
        return bool(firma_ayarlarini_getir().get("test_modu", 0))
    except Exception:
        return False

def tum_personel_verilerini_temizle():
    """Şube, firma ve yönetici kayıtlarını koruyarak bütün personel verilerini siler."""
    baglanti = baglanti_ac()
    try:
        imlec = baglanti.cursor()
        imlec.execute("SELECT COUNT(*) FROM personeller")
        adet = int(imlec.fetchone()[0])
        for tablo in ("duzeltme_talepleri", "personel_amirleri", "kart_hareketleri", "kartlar", "hata_loglari", "loglar", "personel_subeleri", "personeller"):
            imlec.execute(f"DELETE FROM {tablo}")
        baglanti.commit()
        return True, f"{adet} personel ve bağlı kayıtları kalıcı olarak silindi."
    except Exception as exc:
        baglanti.rollback()
        return False, f"Temizleme yapılamadı: {exc}"
    finally:
        baglanti.close()

def personel_mobil_ozeti(personel_id, gun=30):
    """Mobil sicil kartı için 30 günlük özeti tek bağlantı ve toplu sorgularla üretir.

    Eski sürüm her gün için gunluk_personel_durumlari() çağırıyor; bu da 30 gün için
    tekrar tekrar veritabanı bağlantısı, log, manuel düzeltme ve izin/rapor sorgusu
    açıyordu. Render/PostgreSQL üzerinde 30-40 saniyelik beklemenin ana nedeni buydu.
    Bu sürüm aynı personelin profilini, loglarını, manuel düzeltmelerini ve olaylarını
    birer kez alır; günlük hesaplamayı bellekte yapar.
    """
    gun = max(1, min(int(gun or 30), 90))
    simdi = turkiye_saati()
    bugun = simdi.date()
    ilk_gun = bugun - datetime.timedelta(days=gun - 1)
    baslangic = ilk_gun.isoformat() + " 00:00:00"
    bitis = bugun.isoformat() + " 23:59:59"

    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    try:
        p = baglanti.execute("""
            SELECT p.id,p.isim,p.soyisim,p.sicil_no,p.telefon,p.eposta,p.departman,p.gorev,
                   p.calisma_modeli,p.foto_base64,p.foto_mime,p.mesai_baslangic,p.mesai_bitis,
                   p.personel_tolerans_dakika,p.calisma_gunleri,p.vardiya_grubu,p.ise_giris_tarihi,p.aktif,
                   COALESCE(s.sube_adi,'Şube Atanmamış') AS sube_adi
            FROM personeller p LEFT JOIN subeler s ON s.sube_id=p.sube_id WHERE p.id=?
        """, (int(personel_id),)).fetchone()
        if not p:
            return None

        loglar = baglanti.execute("""
            SELECT log_id,islem_turu,zaman,durum_etiketi
            FROM loglar
            WHERE personel_id=? AND zaman>=? AND zaman<=?
            ORDER BY zaman,log_id
        """, (int(personel_id), baslangic, bitis)).fetchall()

        hatalar = baglanti.execute("""
            SELECT zaman,islem,hata_kodu,mesaj FROM hata_loglari
            WHERE personel_id=? AND zaman>=? ORDER BY zaman DESC LIMIT 100
        """, (int(personel_id), baslangic)).fetchall()

        manuel_rows = baglanti.execute("""
            SELECT duzeltme_id,tarih,yeni_deger,aciklama,yonetici,zaman
            FROM yonetici_duzeltmeleri
            WHERE personel_id=? AND alan='GUNLUK_DURUM' AND tarih>=? AND tarih<=?
            ORDER BY tarih,duzeltme_id DESC
        """, (int(personel_id), ilk_gun.isoformat(), bugun.isoformat())).fetchall()

        olay_rows = baglanti.execute("""
            SELECT * FROM durum_olaylari
            WHERE personel_id=? AND bitis_tarihi>=? AND baslangic_tarihi<=?
              AND (
                 (olay_turu='HASTALIK_RAPORU' AND durum IN ('BİLDİRİLDİ','ONAYLANDI'))
                 OR
                 (olay_turu<>'HASTALIK_RAPORU' AND durum='ONAYLANDI')
              )
            ORDER BY olay_id DESC
        """, (int(personel_id), ilk_gun.isoformat(), bugun.isoformat())).fetchall()
    finally:
        baglanti.close()

    # Gün bazında logları bir kez grupla.
    log_map = {}
    for l in loglar:
        z = str(l["zaman"] or "")
        if len(z) < 10:
            continue
        log_map.setdefault(z[:10], []).append(l)

    # Aynı gün için en son yönetici düzeltmesi geçerlidir.
    manuel_map = {}
    for r in manuel_rows:
        tarih = str(r["tarih"])
        if tarih not in manuel_map:
            manuel_map[tarih] = dict(r)

    olaylar = [dict(x) for x in olay_rows]
    model = str(p["calisma_modeli"] or "SABİT").upper()
    grup = str(p["vardiya_grubu"] or "YOK").upper()
    tolerans = int(p["personel_tolerans_dakika"] or 20)
    plan_g = str(p["mesai_baslangic"] or "09:00")[:5]
    plan_c = str(p["mesai_bitis"] or "18:00")[:5]

    ise_giris_tarihi = None
    if p["ise_giris_tarihi"]:
        try:
            ise_giris_tarihi = datetime.datetime.strptime(str(p["ise_giris_tarihi"])[:10], "%Y-%m-%d").date()
        except Exception:
            ise_giris_tarihi = None

    ozet = []
    for i in range(gun):
        tarih = bugun - datetime.timedelta(days=i)
        gun_iso = tarih.isoformat()
        calisma_gunu = _calisma_gunu_mu(p["calisma_gunleri"], tarih)
        vardiya_var = not (model == "VARDİYA" and grup in ("", "YOK", "NONE", "NULL"))
        planli = calisma_gunu and vardiya_var

        if ise_giris_tarihi and tarih < ise_giris_tarihi:
            ozet.append({
                "tarih": gun_iso, "ilk_giris": "—", "son_cikis": "—", "toplam_dakika": 0,
                "durum": "İŞE BAŞLAMADI", "detay": "Personelin işe giriş tarihinden önceki gün.",
                "kaynak": "PLAN", "planlanan_giris": "—", "planlanan_cikis": "—",
                "gec_dakika": 0, "erken_cikis_dakika": 0
            })
            continue

        hareket = []
        for l in log_map.get(gun_iso, []):
            try:
                an = datetime.datetime.strptime(str(l["zaman"])[:19], "%Y-%m-%d %H:%M:%S")
                hareket.append((str(l["islem_turu"]).upper(), an))
            except Exception:
                pass

        acik = None
        toplam = 0
        girisler = []
        cikislar = []
        eksik_giris = False
        for tur, an in hareket:
            if tur == "GİRİŞ":
                girisler.append(an)
                if acik is None:
                    acik = an
            elif tur == "ÇIKIŞ":
                cikislar.append(an)
                if acik is not None and an >= acik:
                    toplam += int((an - acik).total_seconds() // 60)
                    acik = None
                else:
                    eksik_giris = True

        ilk = min(girisler) if girisler else None
        son = max(cikislar) if cikislar else None
        gec = 0
        erken = 0
        try:
            plan_g_dt = datetime.datetime.strptime(gun_iso + " " + plan_g, "%Y-%m-%d %H:%M")
            plan_c_dt = datetime.datetime.strptime(gun_iso + " " + plan_c, "%Y-%m-%d %H:%M")
            if plan_c_dt <= plan_g_dt and model == "VARDİYA":
                plan_c_dt += datetime.timedelta(days=1)
            if ilk:
                gec = max(0, int((ilk - plan_g_dt).total_seconds() // 60) - tolerans)
            if son and plan_c_dt.date() == tarih:
                erken = max(0, int((plan_c_dt - son).total_seconds() // 60))
        except Exception:
            plan_g_dt = None
            plan_c_dt = None

        manuel = manuel_map.get(gun_iso)
        olay = None
        for o in olaylar:
            if str(o.get("baslangic_tarihi") or "")[:10] <= gun_iso <= str(o.get("bitis_tarihi") or "")[:10]:
                if olay is None:
                    olay = o
                elif o.get("olay_turu") == "HASTALIK_RAPORU" and olay.get("olay_turu") != "HASTALIK_RAPORU":
                    olay = o

        durum = "BEKLİYOR"
        detay = ""
        kaynak = "OTOMATİK"
        if manuel:
            durum = manuel["yeni_deger"]
            detay = f"Yönetici düzeltmesi: {manuel['aciklama']}"
            kaynak = "YÖNETİCİ"
        elif olay:
            durum = OLAY_TURLERI.get(olay["olay_turu"], olay["olay_turu"])
            detay = olay.get("aciklama") or "Personel durum olayı sisteme işlendi."
            kaynak = "RAPOR/BELGE" if olay["olay_turu"] == "HASTALIK_RAPORU" else "İZİN/GÖREV"
        elif model == "VARDİYA" and not vardiya_var:
            durum = "VARDİYA YOK"; detay = "Aktif vardiya grubu tanımlı değil."
        elif not calisma_gunu:
            durum = "HAFTA TATİLİ"; detay = "Bugün çalışma planında değil."
        elif eksik_giris or (cikislar and not girisler):
            durum = "EKSİK GİRİŞ"; detay = "Çıkış kaydı var fakat eşleşen giriş yok."
        elif acik is not None:
            if tarih == bugun:
                durum = "ÇALIŞIYOR"; detay = "Giriş yapıldı; çıkış işlemi henüz yapılmadı."
            else:
                durum = "EKSİK ÇIKIŞ"; detay = "Giriş var, gün kapandı fakat çıkış yok."
        elif girisler and cikislar:
            durum = "ÇALIŞTI"
            if gec > 0:
                durum = "GEÇ GELDİ"
            if erken > 0 and durum == "ÇALIŞTI":
                durum = "ERKEN ÇIKTI"
            detay = f"Net çalışma {toplam//60} sa {toplam%60} dk."
        elif model == "ESNEK":
            durum = "ESNEK / KAYIT YOK"; detay = "Esnek personelde sabit saat üzerinden otomatik devamsızlık verilmedi."
        else:
            try:
                sinir = datetime.datetime.strptime(gun_iso + " " + plan_g, "%Y-%m-%d %H:%M") + datetime.timedelta(minutes=tolerans)
                kesin_sinir = sinir + datetime.timedelta(minutes=SISTEM_GECIKME_GUVENLIK_DAKIKA)
                if tarih < bugun:
                    durum = "İŞE GELMEDİ"
                    detay = f"Plan {plan_g}, tolerans {tolerans} dk; gün kapandı ve giriş bulunamadı."
                elif simdi.replace(tzinfo=None) >= kesin_sinir:
                    durum = "İŞE GELMEDİ"
                    detay = f"Plan {plan_g}, tolerans {tolerans} dk + {SISTEM_GECIKME_GUVENLIK_DAKIKA} dk sistem gecikme güvenliği geçti; giriş bulunamadı."
                elif simdi.replace(tzinfo=None) >= sinir:
                    durum = "KONTROL BEKLİYOR"
                    detay = f"Giriş henüz görünmüyor. Sunucu/ağ gecikmesine karşı {SISTEM_GECIKME_GUVENLIK_DAKIKA} dk güvenlik penceresi açık."
                else:
                    durum = "MESAİ BAŞLAMADI"; detay = "Planlanan başlangıç+tolerans henüz geçmedi."
            except Exception:
                durum = "PLAN HATASI"; detay = "Çalışma planı geçersiz."

        ozet.append({
            "tarih": gun_iso,
            "ilk_giris": ilk.strftime("%H:%M:%S") if ilk else "—",
            "son_cikis": son.strftime("%H:%M:%S") if son else "—",
            "toplam_dakika": toplam,
            "durum": durum,
            "detay": detay or durum,
            "kaynak": kaynak,
            "planlanan_giris": plan_g if planli else "—",
            "planlanan_cikis": plan_c if planli else "—",
            "gec_dakika": gec,
            "erken_cikis_dakika": erken
        })

    profil = dict(p)
    profil.pop("foto_base64", None)
    profil.pop("foto_mime", None)
    # Mobil profil yanıtını gereksiz plan alanlarıyla şişirme.
    for alan in ("mesai_baslangic", "mesai_bitis", "personel_tolerans_dakika", "calisma_gunleri", "vardiya_grubu", "ise_giris_tarihi", "aktif"):
        profil.pop(alan, None)
    profil["foto_url"] = f"/api/personel/{personel_id}/foto" if p["foto_base64"] else ""
    return {"profil": profil, "gunler": ozet, "hatalar": [dict(x) for x in hatalar]}


def ilk_kurulum_gerekli():
    baglanti = baglanti_ac()
    adet = baglanti.execute("SELECT COUNT(*) FROM yoneticiler").fetchone()[0]
    baglanti.close()
    return adet == 0


def firma_bilgilerini_getir():
    baglanti = baglanti_ac(); baglanti.row_factory = sqlite3.Row
    satir = baglanti.execute("SELECT firma_adi, vergi_no, telefon, eposta FROM firma_bilgileri WHERE id=1").fetchone()
    baglanti.close(); return dict(satir) if satir else {}

def kvkk_bilgilendirme_kaydet(personel_id, metin_surumu, bilgi_zamani):
    if not metin_surumu or not bilgi_zamani: return False
    baglanti = baglanti_ac()
    try:
        baglanti.execute("INSERT OR REPLACE INTO kvkk_bilgilendirme_kayitlari (personel_id, metin_surumu, bilgi_zamani, sunucu_kayit_zamani) VALUES (?, ?, ?, ?)", (int(personel_id), str(metin_surumu), str(bilgi_zamani), turkiye_saati().strftime("%Y-%m-%d %H:%M:%S")))
        baglanti.commit(); baglanti.close(); return True
    except Exception:
        baglanti.rollback(); baglanti.close(); return False

def ilk_kurulumu_yap(firma_adi, ad_soyad, kullanici_adi, sifre, vergi_no="", telefon="", eposta=""):
    if not firma_adi.strip() or not ad_soyad.strip() or not kullanici_adi.strip() or len(sifre) < 8:
        return False, "Firma, yönetici bilgileri ve en az 8 karakterli parola zorunludur."
    baglanti = baglanti_ac()
    try:
        if baglanti.execute("SELECT COUNT(*) FROM yoneticiler").fetchone()[0] > 0:
            baglanti.close(); return False, "İlk kurulum daha önce tamamlanmış."
        baglanti.execute("""
            INSERT INTO firma_bilgileri (id, firma_adi, vergi_no, telefon, eposta, kurulum_zamani)
            VALUES (1, ?, ?, ?, ?, ?)
        """, (firma_adi.strip(), vergi_no.strip() or None, telefon.strip() or None,
              eposta.strip() or None, turkiye_saati().strftime("%Y-%m-%d %H:%M:%S")))
        baglanti.execute("""
            INSERT INTO yoneticiler (kullanici_adi, sifre_hash, ad_soyad, aktif)
            VALUES (?, ?, ?, 1)
        """, (kullanici_adi.strip(), sifre_hashle(sifre), ad_soyad.strip()))
        baglanti.commit(); baglanti.close()
        return True, "Firma ve yönetici hesabı oluşturuldu."
    except Exception as exc:
        baglanti.rollback(); baglanti.close()
        return False, f"Kurulum tamamlanamadı: {exc}"

def yonetici_dogrula(kullanici_adi, sifre):
    baglanti = baglanti_ac(); baglanti.row_factory = sqlite3.Row
    kayit = baglanti.execute("SELECT sifre_hash, aktif FROM yoneticiler WHERE kullanici_adi=?", (kullanici_adi,)).fetchone()
    baglanti.close()
    return bool(kayit and kayit["aktif"] and sifre_dogrula(sifre, kayit["sifre_hash"]))

def kart_ata(personel_id, kart_no, kart_turu="RFID", gecerlilik_tarihi=None):
    baglanti = baglanti_ac()
    try:
        baglanti.execute("UPDATE kartlar SET kart_durumu='İPTAL' WHERE personel_id=? AND kart_durumu='AKTİF'", (int(personel_id),))
        baglanti.execute("""
            INSERT INTO kartlar (personel_id, kart_no, kart_turu, kart_token_hash, kart_durumu, verilis_tarihi, gecerlilik_tarihi)
            VALUES (?, ?, ?, ?, 'AKTİF', ?, ?)
        """, (int(personel_id), kart_no.strip(), kart_turu, hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
              turkiye_saati().date().isoformat(), gecerlilik_tarihi or None))
        baglanti.commit(); baglanti.close(); return True, "Kart personele atandı."
    except Exception as exc:
        baglanti.rollback(); baglanti.close(); return False, f"Kart atanamadı: {exc}"

def personel_kartlarini_getir(personel_id):
    baglanti = baglanti_ac(); baglanti.row_factory = sqlite3.Row
    veriler = baglanti.execute("""
        SELECT kart_id, kart_no, kart_turu, kart_durumu, verilis_tarihi, gecerlilik_tarihi, son_kullanim
        FROM kartlar WHERE personel_id=? ORDER BY kart_id DESC
    """, (int(personel_id),)).fetchall()
    baglanti.close(); return [dict(x) for x in veriler]


def personel_mobil_profil_fallback(personel_id):
    """Mobil özetin ağır günlük hesapları hata verirse temel sicil kartını döndürür.

    SQLite ve PostgreSQL uyumlu, yalnız tek personel satırını okur. GPS/QR veya
    cihaz güvenliği mantığına dokunmaz.
    """
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    try:
        p = baglanti.execute("""
            SELECT p.id,p.isim,p.soyisim,p.sicil_no,p.telefon,p.eposta,p.departman,p.gorev,
                   p.calisma_modeli,p.foto_base64,p.foto_mime,
                   COALESCE(s.sube_adi,'Şube Atanmamış') AS sube_adi
            FROM personeller p
            LEFT JOIN subeler s ON s.sube_id=p.sube_id
            WHERE p.id=?
        """, (int(personel_id),)).fetchone()
        if not p:
            return None
        profil = dict(p)
        foto_var = bool(profil.get("foto_base64"))
        profil.pop("foto_base64", None)
        profil.pop("foto_mime", None)
        profil["foto_url"] = f"/api/personel/{personel_id}/foto" if foto_var else ""
        return {"profil": profil, "gunler": [], "hatalar": []}
    finally:
        baglanti.close()
