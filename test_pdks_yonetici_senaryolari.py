
def rapor_degeri(giris=None,cikis=None,planli=True,izin=None,mesai_gecti=True):
    if izin:
        return izin
    if not planli:
        return "ÇALIŞMA PLANI YOK"
    if giris and cikis:
        return "ÇALIŞTI"
    if giris and not cikis:
        return "EKSİK ÇIKIŞ"
    if cikis and not giris:
        return "EKSİK GİRİŞ"
    return "İŞE GELMEDİ" if mesai_gecti else "MESAİ BAŞLAMADI"

def test():
    assert rapor_degeri("09:00","18:00")=="ÇALIŞTI"
    assert rapor_degeri("09:00",None)=="EKSİK ÇIKIŞ"
    assert rapor_degeri(None,"18:00")=="EKSİK GİRİŞ"
    assert rapor_degeri(None,None)=="İŞE GELMEDİ"
    assert rapor_degeri(None,None,izin="RAPORLU")=="RAPORLU"
    assert rapor_degeri(None,None,planli=False)=="ÇALIŞMA PLANI YOK"
    assert rapor_degeri(None,None,mesai_gecti=False)=="MESAİ BAŞLAMADI"
    print("7 yönetici/rapor senaryosu geçti; boş durum üretilmiyor.")

if __name__=="__main__":
    test()
