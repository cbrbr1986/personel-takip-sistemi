
def karar(kaynak, surum, is_mock, developer, accuracy, age_ms):
    if kaynak != "android-native" or surum < 3:
        return "RED_ISTEMCI"
    if is_mock:
        return "RED_FAKE_GPS"
    # developer options alone must NOT reject
    if age_ms < 0 or age_ms > 20000:
        return "RED_ESKI_KONUM"
    if accuracy <= 0 or accuracy > 50:
        return "RED_DUSUK_DOGRULUK"
    return "KABUL"

def test_senaryolar():
    assert karar("android-native",3,False,False,8,1500) == "KABUL"       # gerçek GPS
    assert karar("android-native",3,False,True,8,1500) == "KABUL"        # geliştirici açık + gerçek GPS
    assert karar("android-native",3,True,True,5,500) == "RED_FAKE_GPS"   # Fake GPS
    assert karar("android-native",3,True,False,5,500) == "RED_FAKE_GPS"  # mock bayrağı tek başına yeter
    assert karar("web",3,False,False,5,500) == "RED_ISTEMCI"             # tarayıcı bypass yok
    assert karar("android-native",2,False,False,5,500) == "RED_ISTEMCI"  # eski APK yok
    assert karar("android-native",3,False,False,90,500) == "RED_DUSUK_DOGRULUK"
    assert karar("android-native",3,False,False,8,25001) == "RED_ESKI_KONUM"

if __name__ == "__main__":
    test_senaryolar()
    print("8 GPS güvenlik senaryosu geçti.")
