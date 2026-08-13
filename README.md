# PDKS Personel Android

Uygulama PDKS personel ekranını uygulama içi güvenli alanda açar. İlk kullanımda personel 6 haneli şifresini oluşturur; sonraki açılışlarda sicil numarası ve şifresiyle giriş yapar. QR tarayıcı, giriş/çıkış ekranındaki **Kare Kodu Okut** düğmesiyle açılır.

## GitHub ile APK üretme

Bu klasörü deponun köküne yükleyin. `.github/workflows/android-apk.yml` dosyasını depo kökündeki `.github/workflows/` klasörüne taşıyın. GitHub **Actions > Android APK > Run workflow** adımlarından derlemeyi başlatın. Tamamlanınca `PDKS-Personel-APK` çıktısını indirip ZIP içindeki `app-debug.apk` dosyasını telefona kurun.
