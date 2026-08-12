package com.coskun.pdkspersonel

import android.Manifest
import android.annotation.SuppressLint
import android.app.AppOpsManager
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.provider.Settings
import android.webkit.GeolocationPermissions
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.location.LocationCompat
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import com.google.zxing.client.android.Intents
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import org.json.JSONObject
import java.security.MessageDigest

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView

    inner class AndroidKoprusu {
        @JavascriptInterface
        fun startQrScanner() = runOnUiThread { qrAc() }

        @JavascriptInterface
        fun closeApp() = runOnUiThread { finishAndRemoveTask() }

        @JavascriptInterface
        fun requestSecureLocation() = runOnUiThread { guvenliKonumAl() }

        @JavascriptInterface
        fun getStableDeviceId(): String = kaliciCihazKimligi()

        @JavascriptInterface
        fun isVpnOrProxyActive(): Boolean = vpnVeyaProxyAktifMi()
    }

    private val izinIstegi = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { webView.reload() }

    private val qrTarayici = registerForActivityResult(ScanContract()) { sonuc ->
        val qr = sonuc.contents ?: return@registerForActivityResult
        val jsDegeri = JSONObject.quote(qr)
        webView.evaluateJavascript("if(typeof nativeQrSonucu==='function'){nativeQrSonucu($jsDegeri)}", null)
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this)
        setContentView(webView)

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.databaseEnabled = true
        webView.settings.setGeolocationEnabled(true)
        webView.settings.mediaPlaybackRequiresUserGesture = false
        webView.addJavascriptInterface(AndroidKoprusu(), "Android")
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = object : WebChromeClient() {
            override fun onGeolocationPermissionsShowPrompt(origin: String?, callback: GeolocationPermissions.Callback?) {
                callback?.invoke(origin, konumIzniVar(), false)
                if (!konumIzniVar()) izinleriIste()
            }
            override fun onPermissionRequest(request: PermissionRequest?) {
                runOnUiThread {
                    if (kameraIzniVar()) request?.grant(request.resources) else {
                        request?.deny(); izinleriIste()
                    }
                }
            }
        }
        izinleriIste()
        webView.loadUrl("https://pdks-897e.onrender.com/personel-kurulum")
    }

    private fun qrAc() {
        val ayar = ScanOptions().apply {
            setDesiredBarcodeFormats(Intents.Scan.QR_CODE_MODE)
            setPrompt("PDKS ekranındaki QR kodunu okutun")
            setBeepEnabled(true)
            setOrientationLocked(true)
        }
        qrTarayici.launch(ayar)
    }

    @SuppressLint("MissingPermission")
    private fun guvenliKonumAl() {
        if (!konumIzniVar()) {
            izinleriIste()
            webView.evaluateJavascript("nativeKonumHatasi('Konum izni verilmedi.')", null)
            return
        }
        val iptal = CancellationTokenSource()
        LocationServices.getFusedLocationProviderClient(this)
            .getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, iptal.token)
            .addOnSuccessListener { konum ->
                if (konum == null) {
                    webView.evaluateJavascript("nativeKonumHatasi('GPS konumu alınamadı.')", null)
                    return@addOnSuccessListener
                }
                val yasMs = (SystemClock.elapsedRealtimeNanos() - konum.elapsedRealtimeNanos) / 1_000_000
                val konumMock = LocationCompat.isMock(konum) ||
                    (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && konum.isMock) ||
                    (Build.VERSION.SDK_INT < Build.VERSION_CODES.S && konum.isFromMockProvider)
                val mockUygulamaSecili = mockKonumUygulamasiYetkiliMi()
                val sahteKonum = konumMock || mockUygulamaSecili
                val veri = JSONObject().apply {
                    put("latitude", konum.latitude)
                    put("longitude", konum.longitude)
                    put("accuracy", konum.accuracy)
                    put("ageMs", yasMs.coerceAtLeast(0))
                    put("isMock", sahteKonum)
                    put("mockLocationFlag", konumMock)
                    put("mockAppDetected", mockUygulamaSecili)
                    put("developerOptions", gelistiriciSecenekleriAcikMi())
                    put("source", "android-native")
                }
                webView.evaluateJavascript("nativeKonumSonucu(${veri})", null)
            }
            .addOnFailureListener { webView.evaluateJavascript("nativeKonumHatasi('GPS konumu alınamadı.')", null) }
    }


    /**
     * Android 11+ cihazlarda bazı sahte-konum uygulamaları tek konum örneğinde
     * mock bayrağını güvenilir biçimde taşımayabiliyor. Bu nedenle ayrıca
     * sistemde OPSTR_MOCK_LOCATION yetkisi verilmiş bir uygulama olup olmadığını
     * kontrol ediyoruz. Bu kontrol geliştirici seçeneklerinin açık olmasını tek
     * başına engellemez; yalnızca sahte konum yetkisi gerçekten verilmişse red verir.
     */
    @Suppress("DEPRECATION")
    private fun mockKonumUygulamasiYetkiliMi(): Boolean {
        return try {
            val appOps = getSystemService(APP_OPS_SERVICE) as AppOpsManager
            val uygulamalar = packageManager.getInstalledApplications(PackageManager.GET_META_DATA)
            uygulamalar.any { app ->
                if (app.packageName == packageName) return@any false
                val mod = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    appOps.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_MOCK_LOCATION, app.uid, app.packageName)
                } else {
                    appOps.checkOpNoThrow(AppOpsManager.OPSTR_MOCK_LOCATION, app.uid, app.packageName)
                }
                mod == AppOpsManager.MODE_ALLOWED
            } || (Build.VERSION.SDK_INT <= Build.VERSION_CODES.LOLLIPOP_MR1 &&
                Settings.Secure.getString(contentResolver, Settings.Secure.ALLOW_MOCK_LOCATION) != "0")
        } catch (_: Exception) {
            false
        }
    }

    private fun gelistiriciSecenekleriAcikMi(): Boolean {
        return try {
            Settings.Global.getInt(contentResolver, Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) == 1
        } catch (_: Exception) {
            false
        }
    }

    private fun kaliciCihazKimligi(): String {
        return try {
            val androidId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
            val ham = "$packageName|$androidId|pdks-device-v1"
            val ozet = MessageDigest.getInstance("SHA-256").digest(ham.toByteArray(Charsets.UTF_8))
                .joinToString("") { "%02x".format(it) }
            "android-$ozet"
        } catch (_: Exception) {
            "android-fallback-${Build.FINGERPRINT.hashCode()}-${packageName.hashCode()}"
        }
    }

    private fun vpnVeyaProxyAktifMi(): Boolean {
        val vpnAktif = try {
            val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
            val ag = cm.activeNetwork
            val caps = ag?.let { cm.getNetworkCapabilities(it) }
            caps?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true
        } catch (_: Exception) { false }

        val proxyAktif = try {
            val globalProxy = Settings.Global.getString(contentResolver, Settings.Global.HTTP_PROXY)
            val host = System.getProperty("http.proxyHost")
            val httpsHost = System.getProperty("https.proxyHost")
            !globalProxy.isNullOrBlank() || !host.isNullOrBlank() || !httpsHost.isNullOrBlank()
        } catch (_: Exception) { false }

        return vpnAktif || proxyAktif
    }

    private fun kameraIzniVar() = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
    private fun konumIzniVar() = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    private fun izinleriIste() = izinIstegi.launch(arrayOf(Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION))

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }
}
