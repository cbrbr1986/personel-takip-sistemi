from pathlib import Path

root = Path(__file__).resolve().parent
kt = (root/'android-app/app/src/main/java/com/coskun/pdkspersonel/MainActivity.kt').read_text(encoding='utf-8')
html = (root/'personel_kurulum.html').read_text(encoding='utf-8')
main = (root/'main.py').read_text(encoding='utf-8')
manifest = (root/'android-app/app/src/main/AndroidManifest.xml').read_text(encoding='utf-8')

assert 'LocationCompat.isMock(konum)' in kt
assert 'konum.isMock' in kt
assert 'konum.isFromMockProvider' in kt
assert 'AppOpsManager.OPSTR_MOCK_LOCATION' in kt
assert 'put("isMock", sahteKonum)' in kt
assert 'QUERY_ALL_PACKAGES' not in manifest  # geniş uygulama listesi izni kaldırıldı
assert "if(sonKonum&&sonKonum.isMock)" in html
assert "Sahte konum tespit edildi. İşlem reddedildi." in html
assert 'konum_sahte' in main
assert 'FAKE_GPS' in main
assert 'Sahte konum tespit edildi. İşlem reddedildi.' in main
print('PASS: Android mock-location flag kontrolleri mevcut')
print('PASS: Seçili mock-location uygulaması AppOps ile kontrol ediliyor')
print('PASS: QR açılmadan istemci tarafında sahte konum reddediliyor')
print('PASS: Backend FAKE_GPS reddi ikinci katman olarak mevcut')
assert 'getSecurityVersion(): Int = 2' in kt
assert 'androidGuvenlikSurumu()<2' in html
assert "sonKonum.source||''" in html
assert 'android_guvenlik_surumu' in main
assert 'GUVENLI_ISTEMCI_YOK' in main
assert 'konum_kaynagi != "android-native" or guvenlik_surumu < 2' in main
print('PASS: Web/navigator GPS fallback kart basma için kapalı')
print('PASS: Eski APK güvenlik sürümü backend tarafından reddediliyor')
