import sqlite3
import datetime
import pyotp
import math
from zoneinfo import ZoneInfo

def turkiye_saati():
    return datetime.datetime.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)

def veritabani_hazirla():
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()

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

    imlec.execute("INSERT OR IGNORE INTO subeler (sube_id, sube_adi, enlem, boylam, guvenli_yari_cap) VALUES (1, 'Arnavutköy Merkez Ofis', 41.1345, 28.6234, 50)")
    imlec.execute("INSERT OR IGNORE INTO subeler (sube_id, sube_adi, enlem, boylam, guvenli_yari_cap) VALUES (2, 'Esenyurt Depo', 41.0342, 28.6812, 50)")
    imlec.execute("INSERT OR IGNORE INTO subeler (sube_id, sube_adi, enlem, boylam, guvenli_yari_cap) VALUES (3, 'Hadımköy Fabrika', 41.1520, 28.6145, 50)")
    imlec.execute("INSERT OR IGNORE INTO subeler (sube_id, sube_adi, enlem, boylam, guvenli_yari_cap) VALUES (4, 'PDKS Canlı Test Ofisi', 41.1125, 28.6622, 50)")

    imlec.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_personeller_sicil_no
        ON personeller(sicil_no)
        WHERE sicil_no IS NOT NULL AND sicil_no <> ''
    """)

    baglanti.commit()
    baglanti.close()

def veritabanina_personel_ekle(p_id, isim, soyisim, departman, maas):
    rastgele_gizli_anahtar = pyotp.random_base32()
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()
    imlec.execute("""
        INSERT INTO personeller (id, isim, soyisim, departman, maas, cihaz_id, gizli_anahtar, calisma_modeli, mesai_baslangic, vardiya_grubu)
        VALUES (?, ?, ?, ?, ?, 'EŞLEŞMEDİ', ?, 'SABİT', '09:00', 'YOK')
    """, (p_id, isim, soyisim, departman, maas, rastgele_gizli_anahtar))
    baglanti.commit()
    baglanti.close()

def veritabanindan_personelleri_getir():
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()
    imlec.execute("SELECT * FROM personeller")
    veriler = imlec.fetchall()
    baglanti.close()
    return veriler

def log_yaz(personel_id, islem_turu):
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()
    su_an = turkiye_saati().strftime("%Y-%m-%d %H:%M:%S")
    imlec.execute("""
        INSERT INTO loglar (personel_id, islem_turu, zaman, enlem, boylam, sube_id, durum_etiketi)
        VALUES (?, ?, ?, 0.0, 0.0, 1, 'NORMAL')
    """, (personel_id, islem_turu, su_an))
    baglanti.commit()
    baglanti.close()

def personel_isten_cikar(p_id):
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()
    imlec.execute("DELETE FROM personeller WHERE id = ?", (p_id,))
    baglanti.commit()
    baglanti.close()

def personel_maas_guncelle(p_id, yeni_maas):
    baglanti = sqlite3.connect("sirket.db")
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
    baglanti = sqlite3.connect("sirket.db")
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

    if atanmis_sube_id is None:
        imlec.execute("SELECT sube_id, sube_adi, enlem, boylam, guvenli_yari_cap FROM subeler")
    else:
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
    saat_dakika = su_an_dt.strftime("%H:%M")

    durum_etiketi = "NORMAL"

    if islem_turu == "GİRİŞ":
        if model == "SABİT":
            if saat_dakika > sabit_saat:
                durum_etiketi = "GEÇ KALDI"
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
    baglanti = sqlite3.connect("sirket.db")
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
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()
    imlec.execute("SELECT islem_turu, zaman FROM loglar WHERE personel_id = ? ORDER BY zaman DESC", (p_id,))
    veriler = imlec.fetchall()
    baglanti.close()
    return veriler

def veritabani_guncelle():
    baglanti = sqlite3.connect("sirket.db")
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

    baglanti.commit()
    baglanti.close()

veritabani_guncelle()
veritabani_hazirla()
def tum_loglari_getir_api():
    baglanti = sqlite3.connect("sirket.db")
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

def personel_ekle(isim, soyisim, departman, maas, calisma_modeli,
                  sicil_no=None, telefon=None, gorev=None, sube_id=None, aktif=1):
    try:
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()
        imlec.execute("""
            INSERT INTO personeller (
                isim, soyisim, departman, maas, calisma_modeli,
                sicil_no, telefon, gorev, sube_id, aktif,
                cihaz_id, gizli_anahtar
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'EŞLEŞMEDİ', ?)
        """, (isim, soyisim, departman, float(maas), calisma_modeli,
              sicil_no or None, telefon or None, gorev or None,
              int(sube_id) if sube_id else None, int(aktif), pyotp.random_base32()))
        baglanti.commit()
        baglanti.close()
        return True, "Personel başarıyla veritabanına eklendi."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def personel_sil(personel_id):
    try:
        baglanti = sqlite3.connect("sirket.db")
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
        baglanti = sqlite3.connect("sirket.db")
        baglanti.row_factory = sqlite3.Row
        imlec = baglanti.cursor()
        imlec.execute("""
            SELECT p.id, p.isim, p.soyisim, p.departman, p.maas,
                   p.calisma_modeli, p.sicil_no, p.telefon, p.gorev,
                   p.sube_id, p.aktif, p.cihaz_id,
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

def sube_ekle(sube_adi, enlem, boylam, guvenli_yari_cap):
    try:
        baglanti = sqlite3.connect("sirket.db")
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
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()
        imlec.execute("SELECT COUNT(*) FROM personeller WHERE sube_id = ?", (int(sube_id),))
        if imlec.fetchone()[0] > 0:
            baglanti.close()
            return False, "Bu şubeye bağlı personeller bulunduğu için şube silinemez."
        imlec.execute("DELETE FROM subeler WHERE sube_id = ?", (int(sube_id),))
        baglanti.commit()
        baglanti.close()
        return True, "Lokasyon/Şube sistemden kaldırıldı."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def tum_subeleri_getir():
    try:
        baglanti = sqlite3.connect("sirket.db")
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
                      sicil_no=None, telefon=None, gorev=None, sube_id=None, aktif=1):
    try:
        baglanti = sqlite3.connect("sirket.db")
        imlec = baglanti.cursor()
        imlec.execute("""
            UPDATE personeller 
            SET isim=?, soyisim=?, departman=?, maas=?, calisma_modeli=?,
                sicil_no=?, telefon=?, gorev=?, sube_id=?, aktif=?
            WHERE id=?
        """, (isim, soyisim, departman, float(maas), calisma_modeli,
              sicil_no or None, telefon or None, gorev or None,
              int(sube_id) if sube_id else None, int(aktif), int(p_id)))
        baglanti.commit()
        baglanti.close()
        return True, "Personel bilgileri güncellendi."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def sube_guncelle(s_id, sube_adi, enlem, boylam, guvenli_yari_cap):
    try:
        baglanti = sqlite3.connect("sirket.db")
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
    baglanti = sqlite3.connect("sirket.db")
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()
    imlec.execute("""
        SELECT p.id, p.isim, p.soyisim, p.sicil_no, p.cihaz_id,
               p.cihaz_token_hash, p.aktif, p.sube_id,
               COALESCE(s.sube_adi, 'Şube Atanmamış') AS sube_adi
        FROM personeller p
        LEFT JOIN subeler s ON s.sube_id = p.sube_id
        WHERE UPPER(TRIM(p.sicil_no)) = UPPER(TRIM(?))
    """, (sicil_no,))
    kayit = imlec.fetchone()
    baglanti.close()
    return dict(kayit) if kayit else None

def cihaz_kurulumunu_tamamla(personel_id, cihaz_id, token_hash):
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()
    imlec.execute("""
        UPDATE personeller SET cihaz_id = ?, cihaz_token_hash = ?
        WHERE id = ? AND aktif = 1
    """, (cihaz_id, token_hash, int(personel_id)))
    basarili = imlec.rowcount == 1
    baglanti.commit()
    baglanti.close()
    return basarili

def personeli_cihazla_dogrula(cihaz_id, token_hash):
    baglanti = sqlite3.connect("sirket.db")
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
    baglanti = sqlite3.connect("sirket.db")
    imlec = baglanti.cursor()
    imlec.execute("""
        UPDATE personeller
        SET cihaz_id = 'EŞLEŞMEDİ', cihaz_token_hash = NULL
        WHERE id = ?
    """, (int(personel_id),))
    basarili = imlec.rowcount == 1
    baglanti.commit()
    baglanti.close()
    return basarili
