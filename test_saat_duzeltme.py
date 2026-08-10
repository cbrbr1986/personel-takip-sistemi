import os, sys, types, tempfile, importlib
m=types.ModuleType('pyotp'); m.random_base32=lambda:'TEST'; m.TOTP=lambda x:None; sys.modules.setdefault('pyotp',m)
os.environ['SQLITE_PATH']=tempfile.mktemp(prefix='pdks_saat_',suffix='.db')
import veritabani
veritabani.veritabani_hazirla()

def q(sql,args=()):
    b=veritabani.baglanti_ac(); b.row_factory=__import__('sqlite3').Row
    try: return b.execute(sql,args).fetchall()
    finally: b.close()

def setup_person():
    b=veritabani.baglanti_ac()
    b.execute("INSERT INTO subeler(sube_adi,enlem,boylam) VALUES('Test',0,0)")
    sid=b.execute('SELECT sube_id FROM subeler').fetchone()[0]
    b.execute("INSERT INTO personeller(id,isim,soyisim,sicil_no,sube_id,aktif) VALUES(1,'Sara','Test','S1',?,1)",(sid,))
    b.commit(); b.close(); return sid

sid=setup_person()
# 1) Sistem kaynaklı ÇIKIŞ UNUTULDU: talep giriş loguna bağlı, seçilen saatte yeni çıkış oluşmalı.
b=veritabani.baglanti_ac(); b.execute("INSERT INTO loglar(personel_id,islem_turu,zaman,sube_id,durum_etiketi) VALUES(1,'GİRİŞ','2026-08-09 08:42:00',?,'EKSİK ÇIKIŞ')",(sid,)); lid=b.execute('SELECT log_id FROM loglar').fetchone()[0]; b.execute("INSERT INTO duzeltme_talepleri(personel_id,log_id,talep_turu,talep_zamani,kaynak,durum) VALUES(1,?,'ÇIKIŞ UNUTULDU','2026-08-10 09:00:00','SİSTEM','BEKLİYOR')",(lid,)); tid=b.execute('SELECT talep_id FROM duzeltme_talepleri').fetchone()[0]; b.commit(); b.close()
ok,msg=veritabani.duzeltme_talebi_kararla(tid,'ONAYLANDI','2026-08-09T17:15','test'); assert ok,msg
rows=q("SELECT islem_turu,zaman FROM loglar WHERE personel_id=1 ORDER BY zaman"); assert [(r['islem_turu'],r['zaman']) for r in rows]==[('GİRİŞ','2026-08-09 08:42:00'),('ÇIKIŞ','2026-08-09 17:15:00')]
assert veritabani.personel_mobil_ozeti(1,30)['gunler'][1]['son_cikis']=='17:15'

# 2) Aynı gün yanlış çıkış zaten varsa ikinci çıkış ekleme; mevcut kaydı seçilen saate UPDATE et.
b=veritabani.baglanti_ac(); b.execute("INSERT INTO loglar(personel_id,islem_turu,zaman,sube_id) VALUES(1,'GİRİŞ','2026-08-10 08:30:00',?)",(sid,)); b.execute("INSERT INTO loglar(personel_id,islem_turu,zaman,sube_id) VALUES(1,'ÇIKIŞ','2026-08-10 19:00:00',?)",(sid,)); giris=b.execute("SELECT log_id FROM loglar WHERE zaman='2026-08-10 08:30:00'").fetchone()[0]; b.execute("INSERT INTO duzeltme_talepleri(personel_id,log_id,talep_turu,talep_zamani,kaynak,durum) VALUES(1,?,'ÇIKIŞ UNUTULDU','2026-08-10 20:00:00','SİSTEM','BEKLİYOR')",(giris,)); tid2=b.execute('SELECT MAX(talep_id) FROM duzeltme_talepleri').fetchone()[0]; b.commit(); b.close()
ok,msg=veritabani.duzeltme_talebi_kararla(tid2,'ONAYLANDI','2026-08-10T17:05','test'); assert ok,msg
rows=q("SELECT zaman FROM loglar WHERE personel_id=1 AND islem_turu='ÇIKIŞ' AND zaman LIKE '2026-08-10%'"); assert len(rows)==1 and rows[0]['zaman']=='2026-08-10 17:05:00'
assert veritabani.personel_mobil_ozeti(1,30)['gunler'][0]['son_cikis']=='17:05'

# 3) Talebin kaydedilen istenen_zaman alanı da gerçekten uygulanan saati taşımalı.
r=q('SELECT durum,istenen_zaman FROM duzeltme_talepleri WHERE talep_id=?',(tid2,))[0]; assert r['durum']=='ONAYLANDI' and r['istenen_zaman']=='2026-08-10 17:05:00'
print('PASS: ÇIKIŞ UNUTULDU yeni çıkış oluşturma')
print('PASS: mevcut yanlış çıkışı seçilen saate UPDATE etme')
print('PASS: personel mobil özetinde yeni saati gösterme')
print('PASS: talep kaydında uygulanan saati saklama')
