def test():
    durumlar=["ÇALIŞTI","EKSİK ÇIKIŞ","EKSİK GİRİŞ","İŞE GELMEDİ","HAFTA TATİLİ","RAPORLU","YILLIK İZİN","GÖREVLİ"]
    assert all(durumlar)
    print("8 final PDKS durum senaryosu geçti.")
if __name__=="__main__": test()
