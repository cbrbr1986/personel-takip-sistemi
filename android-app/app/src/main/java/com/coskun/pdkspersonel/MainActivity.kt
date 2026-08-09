package com.coskun.pdkspersonel

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.SystemClock
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

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView

    inner class AndroidKoprusu {
        @JavascriptInterface
        fun startQrScanner() = runOnUiThread { qrAc() }

        @JavascriptInterface
        fun closeApp() = runOnUiThread { finishAndRemoveTask() }

        @JavascriptInterface
        fun requestSecureLocation() = runOnUiThread { guvenliKonumAl() }
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
                val veri = JSONObject().apply {
                    put("latitude", konum.latitude)
                    put("longitude", konum.longitude)
                    put("accuracy", konum.accuracy)
                    put("ageMs", yasMs.coerceAtLeast(0))
                    put("isMock", LocationCompat.isMock(konum))
                    put("source", "android-native")
                }
                webView.evaluateJavascript("nativeKonumSonucu(${veri})", null)
            }
            .addOnFailureListener { webView.evaluateJavascript("nativeKonumHatasi('GPS konumu alınamadı.')", null) }
    }

    private fun kameraIzniVar() = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
    private fun konumIzniVar() = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    private fun izinleriIste() = izinIstegi.launch(arrayOf(Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION))

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }
}
