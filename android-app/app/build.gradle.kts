plugins { id("com.android.application") }

android {
    namespace = "com.coskun.pdkspersonel"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.coskun.pdkspersonel"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")
}
