
import datetime

GUNLER=["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"]
def durum(model,grup,gunler,baslangic,tolerans,simdi,giris=None,cikis=None):
    calisma=GUNLER[simdi.weekday()] in {x.strip() for x in gunler.split(",")}
    if model=="VARDİYA" and grup=="YOK": return "VARDİYA YOK"
    if not calisma:return "HAFTA TATİLİ"
    if giris and not cikis:return "EKSİK ÇIKIŞ"
    if cikis and not giris:return "EKSİK GİRİŞ"
    if giris and cikis:return "ÇALIŞTI"
    if model=="ESNEK":return "ESNEK / KAYIT YOK"
    limit=datetime.datetime.combine(simdi.date(),datetime.time.fromisoformat(baslangic))+datetime.timedelta(minutes=tolerans)
    return "İŞE GELMEDİ" if simdi>=limit else "MESAİ BAŞLAMADI"

def test():
    sal=datetime.datetime(2026,8,11,22,0)
    assert durum("SABİT","YOK","Pzt,Sal,Çar,Per,Cum","09:00",20,sal)=="İŞE GELMEDİ"
    assert durum("SABİT","YOK","Pzt,Sal,Çar,Per,Cum","09:00",20,sal,datetime.datetime(2026,8,11,9),datetime.datetime(2026,8,11,18))=="ÇALIŞTI"
    assert durum("SABİT","YOK","Pzt,Sal,Çar,Per,Cum","09:00",20,sal,datetime.datetime(2026,8,11,9),None)=="EKSİK ÇIKIŞ"
    paz=datetime.datetime(2026,8,9,22,0)
    assert durum("SABİT","YOK","Pzt,Sal,Çar,Per,Cum","09:00",20,paz)=="HAFTA TATİLİ"
    assert durum("ESNEK","YOK","Pzt,Sal,Çar,Per,Cum","09:00",20,sal)=="ESNEK / KAYIT YOK"
    assert durum("VARDİYA","YOK","Pzt,Sal,Çar,Per,Cum","09:00",20,sal)=="VARDİYA YOK"
    assert durum("VARDİYA","A","Pzt,Sal,Çar,Per,Cum","09:00",20,sal)=="İŞE GELMEDİ"
    erken=datetime.datetime(2026,8,11,9,10)
    assert durum("SABİT","YOK","Pzt,Sal,Çar,Per,Cum","09:00",20,erken)=="MESAİ BAŞLAMADI"
    print("8 günlük PDKS senaryosu geçti.")
if __name__=="__main__":test()
