package com.coskun.pdkspersonel

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Bundle
import android.webkit.GeolocationPermissions
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
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

    private fun kameraIzniVar() = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
    private fun konumIzniVar() = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
    private fun izinleriIste() = izinIstegi.launch(arrayOf(Manifest.permission.CAMERA, Manifest.permission.ACCESS_FINE_LOCATION))

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }
}
