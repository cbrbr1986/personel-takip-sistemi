# PDKS Personel Android

Uygulama mevcut PDKS personel kurulum sayfasını uygulama içi güvenli alanda açar. Chrome geçmişi veya site verileri silinse bile uygulamanın kendi verileri etkilenmez. QR, uygulamanın altındaki **QR KODU OKUT** düğmesiyle taranır.

## GitHub ile APK üretme

Bu klasörü deponun köküne yükleyin. `.github/workflows/android-apk.yml` dosyasını depo kökündeki `.github/workflows/` klasörüne taşıyın. GitHub **Actions > Android APK > Run workflow** adımlarından derlemeyi başlatın. Tamamlanınca `PDKS-Personel-APK` çıktısını indirip ZIP içindeki `app-debug.apk` dosyasını telefona kurun.
