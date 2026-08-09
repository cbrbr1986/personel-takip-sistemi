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
        tolerans_dakika INTEGER NOT NULL DEFAULT 20
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
        SELECT islem_turu, zaman FROM loglar
        WHERE personel_id = ? ORDER BY log_id DESC LIMIT 1
    """, (p_id,))
    son_islem = imlec.fetchone()
    if son_islem:
        try:
            son_zaman = datetime.datetime.strptime(son_islem[1], "%Y-%m-%d %H:%M:%S")
            if (turkiye_saati() - son_zaman).total_seconds() < 30:
                baglanti.close()
                return False, "Mükerrer işlem engellendi. Lütfen 30 saniye bekleyin."
        except (TypeError, ValueError):
            pass
        islem_turu = "ÇIKIŞ" if son_islem[0] == "GİRİŞ" else "GİRİŞ"
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
    return True, f"İşlem Başarılı! {isim} {soyisim} ({model}) - {hedef_sube_adi} Durum: {durum_etiketi}"

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
    "kan_grubu", "ehliyet_sinifi", "yonetici_notu", "foto_mime", "foto_base64"
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

def firma_ayarlarini_getir():
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    satir = baglanti.execute("SELECT gec_kalma_kontrolu, tolerans_dakika FROM firma_ayarlari WHERE id=1").fetchone()
    baglanti.close()
    return dict(satir) if satir else {"gec_kalma_kontrolu": 0, "tolerans_dakika": 20}

def firma_ayarlarini_guncelle(gec_kalma_kontrolu, tolerans_dakika):
    tolerans = max(0, min(int(tolerans_dakika), 240))
    baglanti = baglanti_ac()
    baglanti.execute("UPDATE firma_ayarlari SET gec_kalma_kontrolu=?, tolerans_dakika=? WHERE id=1",
                     (1 if int(gec_kalma_kontrolu) else 0, tolerans))
    baglanti.commit(); baglanti.close()
    return True

def personel_mobil_ozeti(personel_id, gun=30):
    baglanti = baglanti_ac()
    baglanti.row_factory = sqlite3.Row
    p = baglanti.execute("""
        SELECT p.id, p.isim, p.soyisim, p.sicil_no, p.telefon, p.eposta,
               p.departman, p.gorev, p.calisma_modeli, p.foto_base64,
               p.foto_mime, COALESCE(s.sube_adi, 'Şube Atanmamış') AS sube_adi
        FROM personeller p LEFT JOIN subeler s ON s.sube_id=p.sube_id
        WHERE p.id=?
    """, (personel_id,)).fetchone()
    if not p:
        baglanti.close()
        return None
    baslangic = (turkiye_saati() - datetime.timedelta(days=max(1, min(gun, 90)) - 1)).strftime("%Y-%m-%d 00:00:00")
    hareketler = baglanti.execute("""
        SELECT islem_turu, zaman, durum_etiketi FROM loglar
        WHERE personel_id=? AND zaman>=? ORDER BY zaman
    """, (personel_id, baslangic)).fetchall()
    hatalar = baglanti.execute("""
        SELECT zaman, islem, hata_kodu, mesaj FROM hata_loglari
        WHERE personel_id=? AND zaman>=? ORDER BY zaman DESC LIMIT 100
    """, (personel_id, baslangic)).fetchall()
    baglanti.close()

    gunler = {}
    for h in hareketler:
        tarih = h["zaman"][:10]
        gunler.setdefault(tarih, []).append(dict(h))
    ozet = []
    for i in range(max(1, min(gun, 90))):
        tarih = (turkiye_saati().date() - datetime.timedelta(days=i)).isoformat()
        kayitlar = gunler.get(tarih, [])
        girisler = [x for x in kayitlar if x["islem_turu"] == "GİRİŞ"]
        cikislar = [x for x in kayitlar if x["islem_turu"] == "ÇIKIŞ"]
        toplam_saniye = 0
        acik_giris = None
        for x in kayitlar:
            an = datetime.datetime.strptime(x["zaman"], "%Y-%m-%d %H:%M:%S")
            if x["islem_turu"] == "GİRİŞ":
                acik_giris = an
            elif x["islem_turu"] == "ÇIKIŞ" and acik_giris and an >= acik_giris:
                toplam_saniye += int((an - acik_giris).total_seconds())
                acik_giris = None
        durum = "Kayıt yok"
        if kayitlar:
            durum = "Giriş/çıkış eksik" if acik_giris or len(girisler) != len(cikislar) else "Tamamlandı"
        ozet.append({
            "tarih": tarih,
            "ilk_giris": girisler[0]["zaman"][11:16] if girisler else "-",
            "son_cikis": cikislar[-1]["zaman"][11:16] if cikislar else "-",
            "toplam_dakika": toplam_saniye // 60,
            "durum": durum,
            "hareketler": kayitlar
        })
    profil = dict(p)
    profil.pop("foto_base64", None)
    profil.pop("foto_mime", None)
    profil["foto_url"] = f"/api/personel/{personel_id}/foto" if p["foto_base64"] else ""
    return {"profil": profil, "gunler": ozet, "hatalar": [dict(x) for x in hatalar]}

def ilk_kurulum_gerekli():
    baglanti = baglanti_ac()
    adet = baglanti.execute("SELECT COUNT(*) FROM yoneticiler").fetchone()[0]
    baglanti.close()
    return adet == 0

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
