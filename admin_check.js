



/* ============================================================
   GLOBAL DEĞİŞKENLER
============================================================ */

let tumLoglar = [];

let haritaNesnesi = null;
let haritaMarker = null;
let haritaDaire = null;
let personelVerileri = [];
let subeVerileri = [];
let kayitliSubeKatmanlari = [];

let gpsMarker = null;

function kayitliSubeleriHaritadaGoster(odakla=false) {
    if (!haritaNesnesi || typeof L === "undefined") return;
    kayitliSubeKatmanlari.forEach(k => haritaNesnesi.removeLayer(k));
    kayitliSubeKatmanlari = [];
    const sinirlar = [];
    subeVerileri.forEach(s => {
        const lat = parseFloat(String(s.enlem).replace(",", "."));
        const lng = parseFloat(String(s.boylam).replace(",", "."));
        const cap = parseFloat(String(s.guvenli_yari_cap || 50).replace(",", "."));
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
        const marker = L.marker([lat,lng]).addTo(haritaNesnesi).bindPopup(`<strong>📍 ${escapeHtml(s.sube_adi || "Şube")}</strong><br>Güvenli yarıçap: ${Number.isFinite(cap) ? cap : 50} metre`);
        const daire = L.circle([lat,lng], {radius:Number.isFinite(cap)?cap:50,color:"#287fbd",weight:2,fillColor:"#4ca3dd",fillOpacity:.12}).addTo(haritaNesnesi);
        kayitliSubeKatmanlari.push(marker, daire);
        sinirlar.push([lat,lng]);
    });
    if (odakla && sinirlar.length) haritaNesnesi.fitBounds(sinirlar, {padding:[35,35],maxZoom:16});
}


/* ============================================================
   HARİTAYI BAŞLAT
============================================================ */

function haritayiIlkle() {

    const mapElement =
        document.getElementById("harita");

    if (!mapElement) {
        return;
    }

    if (typeof L === "undefined") {

        mapElement.innerHTML = `
            <div style="
                padding:30px;
                text-align:center;
                color:#c0392b;
            ">
                ❌ Harita kütüphanesi yüklenemedi.
                <br>
                İnternet bağlantısını kontrol edin.
            </div>
        `;

        return;
    }


    /*
     * Harita zaten oluşturulduysa tekrar oluşturma.
     */

    if (!haritaNesnesi) {

        haritaNesnesi = L.map("harita", {
            zoomControl: true
        }).setView(
            [41.0082, 28.9784],
            12
        );


        /*
         * OpenStreetMap
         */

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,
                attribution:
                    '&copy; OpenStreetMap katkıcıları'
            }
        ).addTo(haritaNesnesi);

        haritaNesnesi.on("click", function(e) {
            if (!document.getElementById("sube-modal")?.classList.contains("acik")) return;
            document.getElementById("s_enlem").value = e.latlng.lat.toFixed(6);
            document.getElementById("s_boylam").value = e.latlng.lng.toFixed(6);
            document.getElementById("map-info").innerHTML = "✅ Konum haritadan seçildi. Şube adını yazıp kaydedebilirsiniz.";
            haritayiGuncelle();
        });


        /*
         * Harita boyutunu düzelt
         */

        setTimeout(function() {

            if (haritaNesnesi) {
                haritaNesnesi.invalidateSize();
            }

        }, 300);

    }


    /*
     * Mevcut koordinat varsa göster.
     */

    haritayiGuncelle();
}


/* ============================================================
   HARİTAYI GÜNCELLE
============================================================ */

function haritayiGuncelle() {

    const latBox =
        document.getElementById("s_enlem");

    const lngBox =
        document.getElementById("s_boylam");

    const capBox =
        document.getElementById("s_cap");

    const mapInfo =
        document.getElementById("map-info");


    if (!latBox || !lngBox) {
        return;
    }


    const lat =
        parseFloat(
            String(latBox.value).replace(",", ".")
        );

    const lng =
        parseFloat(
            String(lngBox.value).replace(",", ".")
        );

    let cap =
        parseFloat(
            String(capBox?.value || "50").replace(",", ".")
        );


    /*
     * Geçersiz koordinat
     */

    if (
        !Number.isFinite(lat) ||
        !Number.isFinite(lng) ||
        lat < -90 ||
        lat > 90 ||
        lng < -180 ||
        lng > 180
    ) {

        if (mapInfo) {

            mapInfo.innerHTML =
                "📍 Geçerli koordinat bekleniyor...";

        }

        return;
    }


    /*
     * Çap/radius güvenliği
     */

    if (!Number.isFinite(cap) || cap <= 0) {
        cap = 50;
    }


    /*
     * Harita yoksa başlat
     */

    if (!haritaNesnesi) {
        haritayiIlkle();
    }

    if (!haritaNesnesi) {
        return;
    }


    const koordinat = [lat, lng];


    /*
     * Önceki marker
     */

    if (haritaMarker) {

        haritaNesnesi.removeLayer(
            haritaMarker
        );

        haritaMarker = null;
    }


    /*
     * Önceki çember
     */

    if (haritaDaire) {

        haritaNesnesi.removeLayer(
            haritaDaire
        );

        haritaDaire = null;
    }


    /*
     * Şube marker
     */

    haritaMarker = L.marker(
        koordinat
    )
    .addTo(haritaNesnesi)
    .bindPopup(
        `
        <strong>📍 Şube Konumu</strong><br>
        Enlem: ${lat.toFixed(6)}<br>
        Boylam: ${lng.toFixed(6)}<br>
        Güvenli yarıçap: ${cap} metre
        `
    );


    /*
     * 50 metre güvenli alan
     */

    haritaDaire = L.circle(
        koordinat,
        {
            radius: cap,

            color: "#e74c3c",

            weight: 3,

            opacity: 0.9,

            fillColor: "#e74c3c",

            fillOpacity: 0.20
        }
    ).addTo(haritaNesnesi);


    /*
     * Haritayı konuma götür
     */

    haritaNesnesi.setView(
        koordinat,
        17,
        {
            animate: true
        }
    );


    /*
     * Bilgi alanı
     */

    if (mapInfo) {

        mapInfo.innerHTML = `
            📍 <strong>Şube:</strong>
            ${lat.toFixed(6)}, ${lng.toFixed(6)}
            &nbsp;&nbsp;|&nbsp;&nbsp;
            🔴 <strong>Güvenli alan:</strong>
            ${cap} metre
        `;
    }


    /*
     * Popup aç
     */

    haritaMarker.openPopup();
}


/* ============================================================
   GPS
============================================================ */

function cihazKonumunuAl() {

    if (!navigator.geolocation) {

        alert(
            "Tarayıcınız konum bilgisini desteklemiyor."
        );

        return;
    }


    /*
     * Kullanıcıya bilgi
     */

    const mapInfo =
        document.getElementById("map-info");

    if (mapInfo) {

        mapInfo.innerHTML =
            "📡 GPS konumu alınıyor...";
    }


    navigator.geolocation.getCurrentPosition(

        function(position) {

            const lat =
                position.coords.latitude;

            const lng =
                position.coords.longitude;


            /*
             * Alanlara yaz
             */

            document.getElementById(
                "s_enlem"
            ).value = lat.toFixed(6);


            document.getElementById(
                "s_boylam"
            ).value = lng.toFixed(6);


            /*
             * Çap boşsa 50 metre
             */

            const capInput =
                document.getElementById("s_cap");

            if (!capInput.value) {
                capInput.value = 50;
            }


            /*
             * Haritayı güncelle
             */

            haritayiGuncelle();


            /*
             * Gerçek GPS noktasını ayrıca göster.
             */

            if (haritaNesnesi) {

                if (gpsMarker) {

                    haritaNesnesi.removeLayer(
                        gpsMarker
                    );
                }


                gpsMarker =
                    L.circleMarker(
                        [lat, lng],
                        {
                            radius: 8,
                            color: "#ffffff",
                            weight: 3,
                            fillColor: "#3498db",
                            fillOpacity: 1
                        }
                    )
                    .addTo(haritaNesnesi)
                    .bindPopup(
                        `
                        <strong>📱 GPS Konumunuz</strong><br>
                        ${lat.toFixed(6)},
                        ${lng.toFixed(6)}
                        `
                    );


                gpsMarker.openPopup();
            }

        },

        function(error) {

            if (error.code === 1) {

                alert(
                    "Konum izni reddedildi.\n\n" +
                    "Tarayıcının adres çubuğundaki " +
                    "kilit simgesine tıklayıp " +
                    "Konum iznini açın."
                );

            } else if (error.code === 2) {

                alert(
                    "Konum bilgisi alınamadı."
                );

            } else if (error.code === 3) {

                alert(
                    "GPS isteği zaman aşımına uğradı."
                );

            } else {

                alert(
                    "Konum alınırken bir hata oluştu."
                );
            }

        },

        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}


/* ============================================================
   WHATSAPP / GOOGLE MAPS KOORDİNAT AYRIŞTIRMA
============================================================ */

function hizliKonumAyristir(metin) {

    if (!metin) {
        return;
    }


    /*
     * URL decode
     */

    try {

        metin =
            decodeURIComponent(metin);

    } catch (e) {
        // Decode edilemezse olduğu gibi kullan.
    }


    let enlem = null;
    let boylam = null;


    /*
     * Google Maps:
     *
     * ?q=41.112595,28.662186
     *
     * @41.112595,28.662186
     *
     * veya direkt:
     *
     * 41.112595,28.662186
     */

    const regex =
        /([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)/;


    const match =
        metin.match(regex);


    if (match) {

        enlem =
            parseFloat(match[1]);

        boylam =
            parseFloat(match[2]);
    }


    /*
     * Geçerlilik kontrolü
     */

    if (
        !Number.isFinite(enlem) ||
        !Number.isFinite(boylam) ||
        enlem < -90 ||
        enlem > 90 ||
        boylam < -180 ||
        boylam > 180
    ) {

        return;
    }


    /*
     * Alanlara yaz
     */

    document.getElementById(
        "s_enlem"
    ).value = enlem.toFixed(6);


    document.getElementById(
        "s_boylam"
    ).value = boylam.toFixed(6);


    /*
     * Haritayı güncelle
     */

    haritayiGuncelle();
}


/* ============================================================
   LOGIN
============================================================ */

async function sistemeGirisYap(event) {

    event.preventDefault();


    const formData =
        new FormData();


    formData.append(
        "kullanici_adi",
        document.getElementById(
            "username"
        ).value
    );


    formData.append(
        "sifre",
        document.getElementById(
            "password"
        ).value
    );


    const uyarKutusu =
        document.getElementById(
            "alertMessage"
        );


    try {

        const response =
            await fetch(
                window.location.origin +
                "/api/admin-login",
                {
                    method: "POST",
                    body: formData
                }
            );


        const result =
            await response.json();


        if (
            result.status === "success"
        ) {

            localStorage.setItem(
                "pdks_admin_oturum",
                "acik"
            );


            document.getElementById(
                "login-block-layer"
            ).style.display = "none";


            document.getElementById(
                "main-panel-view"
            ).style.display = "block";


            haritayiIlkle();

            yonetimPaneliVerileriniYukle();
            firmaAyarlariniYukle();


            if (!window.pdksInterval) {

                window.pdksInterval =
                    setInterval(
                        yonetimPaneliVerileriniYukle,
                        5000
                    );
            }

        } else {

            uyarKutusu.className =
                "alert-box alert-error";

            uyarKutusu.innerText =
                result.message ||
                "Giriş başarısız.";

            uyarKutusu.style.display =
                "block";
        }

    } catch (error) {

        console.error(
            "Login hatası:",
            error
        );


        uyarKutusu.className =
            "alert-box alert-error";

        uyarKutusu.innerText =
            "Sunucuya bağlanırken hata oluştu.";

        uyarKutusu.style.display =
            "block";
    }
}


/* ============================================================
   OTURUM KAPAT
============================================================ */

async function oturumuKapat() {
    localStorage.removeItem("pdks_admin_oturum");
    try { await fetch("/api/admin-logout", {method:"POST"}); } catch(e) {}
    window.location.reload();
}


/* ============================================================
   ANA VERİLER
============================================================ */

function yonetimPaneliVerileriniYukle() {

    qrGuncelle();

    verileriYenile();

    gunlukDurumuYukle();

    personelListesiYenile();

    subeListesiYenile();

    duzeltmeTalepleriniYukle();
    erisimTalepleriniYukle();
}


/* ============================================================
   QR
============================================================ */

async function qrGuncelle() {

    try {

        const response =
            await fetch(
                window.location.origin +
                "/api/get-qr"
            );


        const result =
            await response.json();


        if (
            result.status === "success"
        ) {

            const qr =
                document.getElementById(
                    "panel-qr-img"
                );


            const text =
                document.getElementById(
                    "panel-qr-text"
                );


            if (qr) {

                qr.src =
                    String(
                        result.qr_base64 || ""
                    ).trim();
            }


            if (text) {

                text.innerText =
                    result.sifre || "-";
            }
        }

    } catch (error) {

        console.error(
            "QR yükleme hatası:",
            error
        );
    }
}


/* ============================================================
   LOG
============================================================ */

async function gunlukDurumuYukle(){
    try{
        const r=await fetch('/api/admin/gunluk-durum',{cache:'no-store'}),v=await r.json();
        if(v.status!=='success')return;
        const o=v.ozet||{};
        const set=(id,val)=>{const e=document.getElementById(id);if(e)e.textContent=String(val??0)};
        set('count-gec',o.gec_gelen);set('count-vardiya',o.bugun_vardiyada);
        set('count-esnek',o.esnek);set('ise-gelmeyen-sayisi',o.ise_gelmeyen);
        window.gunlukPersonelDurumlari=Array.isArray(v.data)?v.data:[];
    }catch(e){console.error('Günlük durum yüklenemedi',e)}
}

async function verileriYenile() {

    try {

        const response =
            await fetch(
                window.location.origin +
                "/api/get-logs"
            );


        const result =
            await response.json();


        if (
            result.status === "success"
        ) {

            tumLoglar =
                Array.isArray(result.data)
                    ? result.data
                    : [];


            tabloyuCiz(
                tumLoglar
            );


            sayaclariGuncelle(
                tumLoglar
            );
        }

    } catch (error) {

        console.error(
            "Log yükleme hatası:",
            error
        );
    }
}


/* ============================================================
   LOG TABLOSU
============================================================ */

function tabloyuCiz(veriler) {

    const tbody =
        document.getElementById(
            "panel-table-body"
        );


    if (!tbody) {
        return;
    }


    let html = "";


    veriler.forEach(
        function(log) {

            const durum =
                String(
                    log.durum_etiketi || ""
                );


            const islem =
                String(
                    log.islem_turu || ""
                );


            let etiketSinif =
                "badge-giriş";


            if (
                islem.toUpperCase() ===
                "ÇIKIŞ"
            ) {

                etiketSinif =
                    "badge-çıkış";

            } else if (
                durum.includes("GEÇ") || durum.includes("EKSİK") || durum.includes("BEKLİYOR")
            ) {

                etiketSinif =
                    "badge-gec";
            }


            const islemClass =
                islem.toLowerCase() ===
                "çıkış"
                    ? "badge-çıkış"
                    : "badge-giriş";


            html += `

                <tr>

                    <td>
                        <b>
                            ${escapeHtml(
                                log.personel || "-"
                            )}
                        </b>
                    </td>

                    <td>

                        <span
                            class="badge ${islemClass}"
                        >
                            ${escapeHtml(islem)}
                        </span>

                    </td>

                    <td>
                        ${escapeHtml(
                            log.zaman || "-"
                        )}
                    </td>

                    <td>
                        📍
                        ${escapeHtml(
                            log.sube || "-"
                        )}
                    </td>

                    <td>

                        <span
                            class="badge ${etiketSinif}"
                        >
                            ${escapeHtml(durum)}
                        </span>

                    </td>

                </tr>

            `;
        }
    );


    if (!html) {

        html = `

            <tr>

                <td
                    colspan="5"
                    style="text-align:center;"
                >
                    Kayıt yok.
                </td>

            </tr>

        `;
    }


    tbody.innerHTML =
        html;
}


/* ============================================================
   PERSONEL
============================================================ */

async function personelListesiYenile() {

    try {

        const response =
            await fetch(
                window.location.origin +
                "/api/admin/personel-listesi"
            );


        const result =
            await response.json();


        const tbody =
            document.getElementById(
                "admin-personel-table"
            );


        if (!tbody) {
            return;
        }


        let html = "";


        const data =
            Array.isArray(result.data)
                ? result.data
                : [];

        personelVerileri = data;
        const amirSec=document.getElementById("p_amir_id");
        if(amirSec){const secili=amirSec.value;amirSec.innerHTML='<option value="">Yönetici onaylasın</option>'+data.map(p=>`<option value="${escapeHtml(p.id)}">${escapeHtml(p.isim)} ${escapeHtml(p.soyisim)}</option>`).join('');amirSec.value=secili}


        data.forEach(
            function(p) {

                html += `

                    <tr>

                        <td>
                            ${escapeHtml(p.id)}
                        </td>

                        <td>
                            <b class="tiklanabilir-personel" role="button" tabindex="0" onclick="sicilKartiAc('${escapeJs(p.id)}')" onkeydown="if(event.key==='Enter')sicilKartiAc('${escapeJs(p.id)}')">
                                ${escapeHtml(
                                    p.isim
                                )}
                                ${escapeHtml(
                                    p.soyisim
                                )}
                            </b>
                            ${p.test_personeli ? '<div style="color:#8a52c7;font-size:12px;font-weight:700">🧪 Test Personeli</div>' : ''}
                        </td>

                        <td>
                            ${escapeHtml(
                                p.departman
                            )}
                        </td>

                        <td>${(p.sube_atamalari || []).length
                            ? (p.sube_atamalari || []).map(a => `${a.ana_sube ? "🏠 " : "📍 "}${escapeHtml(a.sube_adi)}`).join("<br>")
                            : escapeHtml(p.sube_adi || "Şube Atanmamış")}</td>

                        <td>
                            ${escapeHtml(
                                p.calisma_modeli
                            )}
                        </td>

                        <td>${p.aktif ? "✅ Aktif" : "⛔ Pasif"}</td>

                        <td>
                            <button class="btn-action" onclick="sicilKartiAc('${escapeJs(p.id)}')">🪪 Sicil Kartı</button>
                            <button class="btn-action" onclick="personelDuzenle('${escapeJs(p.id)}')">✏️ Düzenle</button>
                            <button class="btn-action btn-del" onclick="personelSil('${escapeJs(p.id)}')">⛔ Pasife Al</button>
                        </td>

                    </tr>

                `;
            }
        );


        tbody.innerHTML =
            html ||
            `
                <tr>
                    <td colspan="7"
                        style="text-align:center;">
                        Personel bulunamadı.
                    </td>
                </tr>
            `;

        const arama = document.getElementById("hizli-personel-ara");
        if (arama?.value.trim()) personelHizliAra(arama.value);

    } catch (error) {

        console.error(
            "Personel listesi hatası:",
            error
        );
    }
}


/* ============================================================
   PERSONEL EKLE / GÜNCELLE
============================================================ */

function ekSubeAtamalariniTopla() {
    return Array.from(document.querySelectorAll(".ek-sube-secim:checked")).map(secim => {
        const satir = secim.closest(".sube-atama-satir");
        return {
            sube_id: secim.dataset.id,
            baslangic_tarihi: satir.querySelector(".sube-baslangic").value,
            bitis_tarihi: satir.querySelector(".sube-bitis").value
        };
    });
}

function ekSubeAlaniniDoldur(atamalar) {
    const alan = document.getElementById("p-ek-sube-listesi");
    if (!alan) return;
    const mevcut = Array.isArray(atamalar) ? atamalar : ekSubeAtamalariniTopla();
    const anaSube = String(document.getElementById("p_sube_id").value || "");
    const atamaHaritasi = new Map(mevcut.filter(a => !a.ana_sube).map(a => [String(a.sube_id), a]));
    const digerSubeler = subeVerileri.filter(s => String(s.id) !== anaSube);
    alan.innerHTML = digerSubeler.map(s => {
        const atama = atamaHaritasi.get(String(s.id));
        return `<div class="sube-atama-satir">
            <label class="sube-sec"><input type="checkbox" class="ek-sube-secim" data-id="${escapeHtml(s.id)}" ${atama ? "checked" : ""}> ${escapeHtml(s.sube_adi)}</label>
            <label>Başlangıç<input type="date" class="sube-baslangic" value="${escapeHtml(atama?.baslangic_tarihi || "")}"></label>
            <label>Bitiş<input type="date" class="sube-bitis" value="${escapeHtml(atama?.bitis_tarihi || "")}"></label>
        </div>`;
    }).join("") || '<div class="sube-yardim">Başka şube bulunmuyor.</div>';
}

async function personelKaydet(event) {
    event.preventDefault();
    const id = document.getElementById("p_id").value;
    if (!id && !document.getElementById("p_foto").files[0]) return alert("Personel fotoğrafı zorunludur.");
    if (document.getElementById("p_cinsiyet").value === "Erkek" && !document.getElementById("p_askerlik_durumu").value) return alert("Erkek personel için askerlik durumu zorunludur.");
    const formData = new FormData();
    const alanlar = {
        isim: "p_isim", soyisim: "p_soyisim", sicil_no: "p_sicil_no",
        telefon: "p_telefon", departman: "p_departman", gorev: "p_gorev",
        maas: "p_maas", calisma_modeli: "p_calisma_modeli",
        mesai_baslangic: "p_mesai_baslangic", mesai_bitis: "p_mesai_bitis",
        personel_tolerans_dakika: "p_personel_tolerans_dakika", calisma_gunleri: "p_calisma_gunleri",
        sube_id: "p_sube_id", aktif: "p_aktif", tc_kimlik_no: "p_tc_kimlik_no",
        eposta: "p_eposta", cinsiyet: "p_cinsiyet", dogum_tarihi: "p_dogum_tarihi",
        dogum_yeri: "p_dogum_yeri", medeni_durum: "p_medeni_durum", uyruk: "p_uyruk",
        il: "p_il", ilce: "p_ilce", mahalle: "p_mahalle", acik_adres: "p_acik_adres",
        posta_kodu: "p_posta_kodu", acil_kisi: "p_acil_kisi", acil_telefon: "p_acil_telefon",
        acil_yakinlik: "p_acil_yakinlik", ise_giris_tarihi: "p_ise_giris_tarihi",
        personel_turu: "p_personel_turu", ogrenim_durumu: "p_ogrenim_durumu",
        okul: "p_okul", bolum: "p_bolum", mezuniyet_yili: "p_mezuniyet_yili",
        mezuniyet_durumu: "p_mezuniyet_durumu", askerlik_durumu: "p_askerlik_durumu",
        terhis_tarihi: "p_terhis_tarihi", tecil_bitis_tarihi: "p_tecil_bitis_tarihi",
        askerlik_aciklama: "p_askerlik_aciklama", sgk_sicil_no: "p_sgk_sicil_no",
        meslek_kodu: "p_meslek_kodu", kan_grubu: "p_kan_grubu",
        ehliyet_sinifi: "p_ehliyet_sinifi", yonetici_notu: "p_yonetici_notu"
    };
    Object.keys(alanlar).forEach(k => {
        let deger = document.getElementById(alanlar[k]).value;
        if (document.getElementById("adres-elle").checked && ["il","ilce","mahalle"].includes(k)) deger = document.getElementById("p_" + k + "_elle").value;
        formData.append(k, deger);
    });
    if (document.getElementById("p_foto").files[0]) formData.append("foto", document.getElementById("p_foto").files[0]);
    if (id) formData.append("p_id", id);
    formData.append("amir_id", document.getElementById("p_amir_id").value);
    const subeAtamalari = ekSubeAtamalariniTopla();
    const gecersizTarih = subeAtamalari.some(a => a.baslangic_tarihi && a.bitis_tarihi && a.baslangic_tarihi > a.bitis_tarihi);
    if (gecersizTarih) return alert("Şube başlangıç tarihi bitiş tarihinden sonra olamaz.");
    formData.append("sube_atamalari_json", JSON.stringify(subeAtamalari));

    const endpoint = id ? "/api/admin/personel-guncelle" : "/api/admin/personel-ekle";
    try {
        const response = await fetch(window.location.origin + endpoint, {method: "POST", body: formData});
        const result = await response.json();
        alert(result.message || "İşlem tamamlandı.");
        if (result.status === "success") {
            personelFormTemizle();
            personelPenceresiKapat();
            personelListesiYenile();
        }
    } catch (error) {
        console.error(error);
        alert("Personel kaydedilirken sunucu hatası oluştu.");
    }
}

async function personelDuzenle(id) {
    const p = personelVerileri.find(x => String(x.id) === String(id));
    if (!p) return;
    document.getElementById("p_id").value = p.id || "";
    document.getElementById("p_isim").value = p.isim || "";
    document.getElementById("p_soyisim").value = p.soyisim || "";
    document.getElementById("p_sicil_no").value = p.sicil_no || "";
    document.getElementById("p_telefon").value = p.telefon || "";
    document.getElementById("p_departman").value = p.departman || "";
    document.getElementById("p_gorev").value = p.gorev || "";
    document.getElementById("p_maas").value = p.maas || 0;
    document.getElementById("p_calisma_modeli").value = p.calisma_modeli || "SABİT";
    document.getElementById("p_mesai_baslangic").value = p.mesai_baslangic || "09:00";
    document.getElementById("p_mesai_bitis").value = p.mesai_bitis || "18:00";
    document.getElementById("p_personel_tolerans_dakika").value = p.personel_tolerans_dakika || "20";
    document.getElementById("p_calisma_gunleri").value = p.calisma_gunleri || "Pzt,Sal,Çar,Per,Cum";
    document.getElementById("p_sube_id").value = p.sube_id || "";
    ekSubeAlaniniDoldur(p.sube_atamalari || []);
    document.getElementById("p_aktif").value = p.aktif ? "1" : "0";
    document.getElementById("p_amir_id").value = p.amir_id || "";
    const ekAlanlar = ["tc_kimlik_no","eposta","cinsiyet","dogum_tarihi","dogum_yeri","medeni_durum","uyruk","acik_adres","posta_kodu","acil_kisi","acil_telefon","acil_yakinlik","ise_giris_tarihi","personel_turu","ogrenim_durumu","okul","bolum","mezuniyet_yili","mezuniyet_durumu","askerlik_durumu","terhis_tarihi","tecil_bitis_tarihi","askerlik_aciklama","sgk_sicil_no","meslek_kodu","kan_grubu","ehliyet_sinifi","yonetici_notu"];
    ekAlanlar.forEach(a => { const el = document.getElementById("p_" + a); if (el) el.value = p[a] || ""; });
    await adresSeciminiYukle(p.il, p.ilce, p.mahalle);
    askerlikAlaniniGuncelle();
    document.getElementById("personel-kaydet-btn").innerText = "💾 Değişiklikleri Kaydet";
    document.getElementById("personel-modal-baslik").textContent = "✏️ Personel Düzenle";
    document.getElementById("personel-modal").classList.add("acik");
    pencereDurumu("personel-modal","normal");
    document.getElementById("p_isim").scrollIntoView({behavior: "smooth", block: "center"});
}

function personelFormTemizle() {
    document.getElementById("p_id").value = "";
    ["p_isim", "p_soyisim", "p_sicil_no", "p_telefon", "p_departman", "p_gorev", "p_tc_kimlik_no", "p_eposta", "p_dogum_tarihi", "p_dogum_yeri", "p_acik_adres", "p_posta_kodu", "p_acil_kisi", "p_acil_telefon", "p_acil_yakinlik", "p_ise_giris_tarihi", "p_okul", "p_bolum", "p_mezuniyet_yili", "p_terhis_tarihi", "p_tecil_bitis_tarihi", "p_askerlik_aciklama", "p_sgk_sicil_no", "p_meslek_kodu", "p_kan_grubu", "p_ehliyet_sinifi", "p_yonetici_notu", "p_foto", "p_il_elle", "p_ilce_elle", "p_mahalle_elle"].forEach(id => document.getElementById(id).value = "");
    ["p_cinsiyet","p_medeni_durum","p_personel_turu","p_ogrenim_durumu","p_mezuniyet_durumu","p_askerlik_durumu"].forEach(id => document.getElementById(id).value = "");
    document.getElementById("p_uyruk").value = "T.C.";
    document.getElementById("p_maas").value = "0";
    document.getElementById("p_calisma_modeli").value = "SABİT";
    document.getElementById("p_mesai_baslangic").value = "09:00";
    document.getElementById("p_mesai_bitis").value = "18:00";
    document.getElementById("p_personel_tolerans_dakika").value = "20";
    document.getElementById("p_calisma_gunleri").value = "Pzt,Sal,Çar,Per,Cum";
    document.getElementById("p_sube_id").value = "";
    ekSubeAlaniniDoldur([]);
    document.getElementById("p_aktif").value = "1";
    document.getElementById("p_amir_id").value = "";
    document.getElementById("personel-kaydet-btn").innerText = "💾 Personeli Kaydet";
    document.getElementById("adres-elle").checked = false;
    adresElleDegisti();
    document.getElementById("p_il").value = "";
    document.getElementById("p_ilce").innerHTML = '<option value="">Önce il seçiniz</option>';
    document.getElementById("p_mahalle").innerHTML = '<option value="">Önce ilçe seçiniz</option>';
    askerlikAlaniniGuncelle();
}

async function yeniPersonelPenceresiAc() {
    personelFormTemizle();
    document.getElementById("personel-modal-baslik").textContent = "👤 Yeni Personel Ekle";
    document.getElementById("personel-modal").classList.add("acik");
    pencereDurumu("personel-modal","normal");
    await illeriYukle();
}
function personelPenceresiKapat(){document.getElementById("personel-modal").classList.remove("acik","simge","tam-ekran")}
function modalDisinaTikla(e){if(e.target.id==="personel-modal")personelPenceresiKapat()}

function pencereDurumu(id,durum){const modal=document.getElementById(id);if(!modal)return;modal.classList.remove("simge","tam-ekran");if(durum==="simge")modal.classList.add("simge");if(durum==="tam")modal.classList.add("tam-ekran");if(id==="sube-modal"&&durum!=="simge")setTimeout(()=>{haritaNesnesi?.invalidateSize();kayitliSubeleriHaritadaGoster(false)},180)}
function subeFormTemizle(){document.getElementById("s_id").value="";document.getElementById("s_adi").value="";document.getElementById("s_enlem").value="";document.getElementById("s_boylam").value="";document.getElementById("s_cap").value="50";document.getElementById("s_hizli_konum").value="";document.getElementById("sube-kaydet-btn").innerText="📍 Konumu İşle ve Şubeyi Kaydet";document.getElementById("sube-modal-baslik").textContent="📍 Yeni Şube Ekle"}
function yeniSubePenceresiAc(){subeFormTemizle();document.getElementById("sube-modal").classList.add("acik");pencereDurumu("sube-modal","normal");setTimeout(()=>{haritayiIlkle();haritaNesnesi?.invalidateSize();kayitliSubeleriHaritadaGoster(true)},220)}
function subePenceresiKapat(){document.getElementById("sube-modal").classList.remove("acik","simge","tam-ekran")}
function subeModalDisinaTikla(e){if(e.target.id==="sube-modal")subePenceresiKapat()}
function sicilPenceresiKapat(){document.getElementById("sicil-modal").classList.remove("acik","simge","tam-ekran")}
function sicilModalDisinaTikla(e){if(e.target.id==="sicil-modal")sicilPenceresiKapat()}
function bilgiAlani(baslik,deger){return `<div class="sicil-alan"><small>${escapeHtml(baslik)}</small><b>${escapeHtml(deger||"-")}</b></div>`}
function sicilKartiAc(id){const p=personelVerileri.find(x=>String(x.id)===String(id));if(!p)return;const foto=p.foto_url?escapeHtml(p.foto_url):"data:image/svg+xml,"+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="180" height="220"><rect width="100%" height="100%" fill="#e7edf3"/><text x="50%" y="55%" text-anchor="middle" font-size="70">👤</text></svg>');document.getElementById("sicil-kart-icerik").innerHTML=`<div class="sicil-ust"><img class="sicil-foto" src="${foto}" alt="Personel fotoğrafı"><div><h2 style="margin:0 0 15px;color:#173b66">${escapeHtml(p.isim||"")} ${escapeHtml(p.soyisim||"")}</h2><div class="sicil-bilgi">${bilgiAlani("Sicil No",p.sicil_no)}${bilgiAlani("TC Kimlik No",p.tc_kimlik_no)}${bilgiAlani("Görev",p.gorev)}${bilgiAlani("Departman",p.departman)}${bilgiAlani("Şube",p.sube_adi)}${bilgiAlani("Çalışma Modeli",p.calisma_modeli)}${bilgiAlani("Giriş / Çıkış",(p.mesai_baslangic||"-")+" / "+(p.mesai_bitis||"-"))}${bilgiAlani("Tolerans",(p.personel_tolerans_dakika||"20")+" dk")}${bilgiAlani("Telefon",p.telefon)}${bilgiAlani("E-posta",p.eposta)}${bilgiAlani("Durum",p.aktif?"Aktif":"Pasif")}</div><div style="margin-top:18px;padding:14px;border:1px solid #dbe5ee;border-radius:12px;background:#f8fbfd">
<b>🔐 Erişim ve Güvenlik</b>
<div style="margin-top:8px">Cihaz: <b>${escapeHtml(p.cihaz_id&&p.cihaz_id!=="EŞLEŞMEDİ"?"Eşleştirilmiş":"Eşleştirilmemiş")}</b></div>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">
<button type="button" class="btn-action" onclick="dogrudanErisimSifirla('${escapeJs(p.id)}','SIFRE')">🔑 Şifre Sıfırla</button>
<button type="button" class="btn-action btn-del" onclick="dogrudanErisimSifirla('${escapeJs(p.id)}','CIHAZ')">📱 Cihaz Sıfırla</button>
<button type="button" class="btn-action" onclick="sicilPenceresiKapat();kartPenceresiAc('${escapeJs(p.id)}','${escapeJs(p.isim)} ${escapeJs(p.soyisim)}')">💳 Kart Yönetimi</button>
</div>
<small style="display:block;margin-top:9px;color:#657788">Şifre, cihaz ve kart işlemleri birbirinden bağımsızdır.</small>
</div><button type="button" class="geo-button blue" style="margin-top:15px" onclick="sicilPenceresiKapat();personelDuzenle('${escapeJs(p.id)}')">✏️ Personeli Düzenle</button></div></div>`;document.getElementById("personel-arama-sonuclari").classList.remove("acik");document.getElementById("sicil-modal").classList.add("acik");pencereDurumu("sicil-modal","normal")}
function erisimPenceresiKapat(){document.getElementById('erisim-modal')?.classList.remove('acik')}
async function erisimPenceresiAc(){document.getElementById('erisim-modal').classList.add('acik');document.getElementById('erisim-ara').value='';document.getElementById('erisim-personel-sonuc').innerHTML='';await erisimTalepleriniYukle()}
function erisimPersonelAra(kelime){
 const q=String(kelime||'').toLocaleLowerCase('tr-TR').trim(),alan=document.getElementById('erisim-personel-sonuc');
 if(!q){alan.innerHTML='';return}
 const es=personelVerileri.filter(p=>[p.isim,p.soyisim,p.sicil_no].join(' ').toLocaleLowerCase('tr-TR').includes(q)).slice(0,10);
 alan.innerHTML=es.map(p=>`<div style="padding:12px;border:1px solid #dbe5ee;border-radius:12px;margin:8px 0"><b>${escapeHtml(p.isim)} ${escapeHtml(p.soyisim)}</b><small style="display:block">Sicil: ${escapeHtml(p.sicil_no||'-')} · ${escapeHtml(p.sube_adi||'-')}</small><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"><button class="btn-action" onclick="dogrudanErisimSifirla('${escapeJs(p.id)}','SIFRE')">🔑 Şifre Sıfırla</button><button class="btn-action btn-del" onclick="dogrudanErisimSifirla('${escapeJs(p.id)}','CIHAZ')">📱 Cihaz Sıfırla</button></div></div>`).join('')||'<p>Personel bulunamadı.</p>';
}
async function dogrudanErisimSifirla(id,tur){
 const mesaj=tur==='SIFRE'?'Yalnızca personel şifresi sıfırlanacak. Cihaz değişmeyecek.':'Yalnızca cihaz eşleştirmesi sıfırlanacak. Şifre değişmeyecek.';
 if(!confirm(mesaj+' Devam edilsin mi?'))return;
 const f=new FormData();f.append('personel_id',id);
 const url=tur==='SIFRE'?'/api/admin/personel-sifre-sifirla':'/api/admin/personel-cihaz-sifirla';
 const r=await fetch(url,{method:'POST',body:f}),v=await r.json();alert(v.message);if(v.status==='success')personelListesiYenile();
}
async function erisimTalepleriniYukle(){
 try{const r=await fetch('/api/admin/erisim-talepleri',{cache:'no-store'}),v=await r.json(),d=Array.isArray(v.data)?v.data:[];
 const badge=document.getElementById('erisim-talep-badge');if(badge)badge.textContent=d.length?`(${d.length})`:'';
 const alan=document.getElementById('erisim-bekleyenler');if(!alan)return;
 alan.innerHTML=d.map(t=>`<div style="padding:12px;border:1px solid #dbe5ee;border-radius:12px;margin:8px 0"><b>${escapeHtml(t.isim)} ${escapeHtml(t.soyisim)}</b><small style="display:block">Sicil: ${escapeHtml(t.sicil_no||'-')} · Şube: ${escapeHtml(t.sube_adi||'-')} · ${escapeHtml(t.talep_zamani||'')}</small><b style="display:block;margin:7px 0">${t.talep_turu==='SIFRE_SIFIRLAMA'?'🔑 Şifre Sıfırlama':'📱 Cihaz Sıfırlama'}</b><button class="btn-action" onclick="erisimTalepKarar(${t.talep_id},'ONAYLANDI')">✅ Onayla</button> <button class="btn-action btn-del" onclick="erisimTalepKarar(${t.talep_id},'REDDEDİLDİ')">❌ Reddet</button></div>`).join('')||'<p style="color:#4b8060">✅ Bekleyen erişim talebi yok.</p>';
 }catch(e){const alan=document.getElementById('erisim-bekleyenler');if(alan)alan.textContent='Talepler yüklenemedi.'}
}
async function erisimTalepKarar(id,karar){const f=new FormData();f.append('talep_id',String(id));f.append('karar',karar);const r=await fetch('/api/admin/erisim-talebi-karar',{method:'POST',body:f}),v=await r.json();alert(v.message);await erisimTalepleriniYukle();await personelListesiYenile()}
function normalPersonelAramasinaGec(){document.getElementById("hizli-personel-ara").placeholder="Ad, soyad, sicil veya TC ile personel ara..."}
function personelAramaSec(id){document.getElementById("personel-arama-sonuclari").classList.remove("acik");sicilKartiAc(id)}
function subeSecimListesiniCiz(kelime=""){const aranan=String(kelime).toLocaleLowerCase("tr-TR").trim(),liste=document.getElementById("sube-duzenleme-listesi"),eslesen=subeVerileri.filter(s=>[s.sube_adi,s.enlem,s.boylam].join(" ").toLocaleLowerCase("tr-TR").includes(aranan));liste.innerHTML=eslesen.map(s=>`<div style="display:flex;align-items:center;gap:12px;padding:13px;border:1px solid #dbe5ee;border-radius:12px;background:#f8fbfd"><span style="font-size:30px">📍</span><div style="flex:1"><b>${escapeHtml(s.sube_adi||"Şube")}</b><small style="display:block;color:#657788;margin-top:4px">${escapeHtml(s.enlem||"")}, ${escapeHtml(s.boylam||"")} · Güvenli alan: ${escapeHtml(s.guvenli_yari_cap||50)} m</small></div><button type="button" class="btn-action" onclick="subeSecimPenceresiKapat();subeDuzenle('${escapeJs(s.id)}')">✏️ Düzenle</button></div>`).join("")||'<div style="padding:18px;text-align:center;color:#68798a">Şube bulunamadı.</div>'}
function subeDuzenlemeSecimiAc(){document.getElementById("sube-duzenleme-ara").value="";subeSecimListesiniCiz();document.getElementById("sube-secim-modal").classList.add("acik");pencereDurumu("sube-secim-modal","normal");setTimeout(()=>document.getElementById("sube-duzenleme-ara").focus(),100)}
function subeSecimPenceresiKapat(){document.getElementById("sube-secim-modal").classList.remove("acik","simge","tam-ekran")}
function subeSecimModalDisinaTikla(e){if(e.target.id==="sube-secim-modal")subeSecimPenceresiKapat()}

function personelHizliAra(kelime){
    const aranan=(kelime||"").toLocaleLowerCase("tr-TR").trim();
    const sonuc=document.getElementById("personel-arama-sonuclari");
    document.querySelectorAll("#admin-personel-table tr").forEach(satir=>{
        satir.style.display=!aranan||satir.textContent.toLocaleLowerCase("tr-TR").includes(aranan)?"":"none";
    });
    if(!aranan){sonuc.innerHTML="";sonuc.classList.remove("acik");return}
    const eslesen=personelVerileri.filter(p=>[p.isim,p.soyisim,p.sicil_no,p.tc_kimlik_no,p.departman,p.gorev].join(" ").toLocaleLowerCase("tr-TR").includes(aranan)).slice(0,12);
    sonuc.innerHTML=eslesen.map(p=>`<button type="button" class="arama-sonuc" onclick="personelAramaSec('${escapeJs(p.id)}')">${p.foto_url?`<img src="${escapeHtml(p.foto_url)}" alt="">`:`<span class="arama-avatar"></span>`}<span><b>${escapeHtml(p.isim||"")} ${escapeHtml(p.soyisim||"")}</b><small>Sicil: ${escapeHtml(p.sicil_no||"-")} · ${escapeHtml(p.departman||p.gorev||"-")}</small></span></button>`).join("")||'<div style="padding:16px;color:#68798a">Personel bulunamadı.</div>';
    sonuc.classList.add("acik");
}

function gunlukDurumPenceresiAc(filtre){
  const modal=document.getElementById('hareket-modal'),kutu=document.getElementById('hareket-bekleyen-liste');
  modal.classList.add('acik');
  const data=(window.gunlukPersonelDurumlari||[]).filter(x=>!filtre||x.durum===filtre);
  kutu.innerHTML=data.map(x=>`<div style="padding:14px;border:1px solid #dbe5ee;border-radius:12px;margin:10px 0">
    <b>${escapeHtml(x.personel)}</b> · Sicil ${escapeHtml(x.sicil_no||'-')}
    <small style="display:block;color:#657788;margin:5px 0">${escapeHtml(x.sube||'-')} · ${escapeHtml(x.calisma_modeli)} · ${escapeHtml(x.durum)}</small>
    <div>${escapeHtml(x.detay||'')}</div>
  </div>`).join('')||'<p>Bu durumda personel yok.</p>';
}
function hareketModalKapat(){document.getElementById('hareket-modal')?.classList.remove('acik')}
async function bekleyenOnaylariAc(filtre){
  const modal=document.getElementById('hareket-modal'),kutu=document.getElementById('hareket-bekleyen-liste');
  modal.classList.add('acik');kutu.innerHTML='<p>Yükleniyor...</p>';
  try{
    const r=await fetch('/api/admin/duzeltme-talepleri',{cache:'no-store'}),v=await r.json();
    let data=Array.isArray(v.data)?v.data:[];
    if(filtre)data=data.filter(t=>(t.talep_turu||'').toLocaleUpperCase('tr-TR')===filtre);
    kutu.innerHTML=data.map(t=>`<div style="padding:14px;border:1px solid #dbe5ee;border-radius:12px;margin:10px 0">
      <b>${escapeHtml(t.personel||'Personel')}</b> · ${escapeHtml(t.talep_turu||'-')}
      <small style="display:block;color:#657788;margin:6px 0">${escapeHtml((t.istenen_zaman||'').replace('T',' '))} · ${escapeHtml(t.amir||'Yönetici')}</small>
      <button class="btn-action" onclick="hareketModalKapat();document.getElementById('hizli-personel-ara').value='${escapeJs(t.personel||'')}';personelHizliAra('${escapeJs(t.personel||'')}')">🪪 Personel Sicil Kartı</button>
    </div>`).join('')||'<p style="color:#4b8060">✅ Kayıt yok.</p>';
  }catch(e){kutu.innerHTML='<p>Kayıtlar yüklenemedi.</p>'}
}
async function duzeltmeTalepleriniYukle(){
    const tbody=document.getElementById('duzeltme-talepleri-tablosu');if(!tbody)return;

    // Panel 5 saniyede bir yenileniyor. Kullanıcının seçtiği tarih/saat,
    // karar açıklaması ve devamsızlık nedenini yenileme sırasında koru.
    const taslaklar={};
    tbody.querySelectorAll('input[id^="talep-zaman-"],input[id^="talep-aciklama-"],select[id^="talep-neden-"]').forEach(el=>{
        const id=el.id.replace(/^talep-(?:zaman|aciklama|neden)-/,'');
        taslaklar[id]=taslaklar[id]||{};
        if(el.id.startsWith('talep-zaman-')) taslaklar[id].zaman=el.value;
        else if(el.id.startsWith('talep-neden-')) taslaklar[id].neden=el.value;
        else taslaklar[id].aciklama=el.value;
    });

    try{
        const r=await fetch('/api/admin/duzeltme-talepleri',{cache:'no-store'}),v=await r.json(),data=Array.isArray(v.data)?v.data:[];
        document.getElementById('duzeltme-sayisi').textContent=data.length;

        tbody.innerHTML=data.map(t=>{
            const taslak=taslaklar[String(t.talep_id)]||{};
            const tur=(t.talep_turu||'').toLocaleUpperCase('tr-TR');
            const saatDuzeltme=['GİRİŞ UNUTULDU','ÇIKIŞ UNUTULDU','İNTERNET YOKTU'].includes(tur);
            const sunucuZamani=(t.istenen_zaman||'').replace(' ','T').slice(0,16);
            const z=taslak.zaman!==undefined?taslak.zaman:sunucuZamani;
            const kararAciklamasi=taslak.aciklama!==undefined?taslak.aciklama:'';
            const neden=taslak.neden!==undefined?taslak.neden:(tur==='İŞE GELMEDİ'?'İşe gelmedi':'Onaylandı');
            const nedenSecimi=`<select id="talep-neden-${t.talep_id}" style="margin-bottom:6px"><option ${neden==='Onaylandı'?'selected':''}>Onaylandı</option><option ${neden==='Hastalık izni'?'selected':''}>Hastalık izni</option><option ${neden==='Yıllık izin'?'selected':''}>Yıllık izin</option><option ${neden==='Mazeret izni'?'selected':''}>Mazeret izni</option><option ${neden==='Ücretsiz izin'?'selected':''}>Ücretsiz izin</option><option ${neden==='Raporlu'?'selected':''}>Raporlu</option><option ${neden==='Görevli'?'selected':''}>Görevli</option><option ${neden==='İşe gelmedi'?'selected':''}>İşe gelmedi</option><option ${neden==='Diğer'?'selected':''}>Diğer</option></select>`;
            const zamanAlani=saatDuzeltme?`<input type="datetime-local" id="talep-zaman-${t.talep_id}" value="${escapeHtml(z)}">`:`<span>${escapeHtml((t.istenen_zaman||'-').replace('T',' ').slice(0,16))}</span><input type="hidden" id="talep-zaman-${t.talep_id}" value="${escapeHtml(z)}">`;
            return `<tr style="background:${tur==='İŞE GELMEDİ'?'#fff8e8':'#fff1f0'}" data-talep-turu="${escapeHtml(tur)}"><td><b>${escapeHtml(t.personel)}</b><small style="display:block">${escapeHtml(t.kaynak)}</small></td><td><span class="badge badge-gec">${escapeHtml(t.talep_turu)}</span></td><td>${zamanAlani}</td><td>${escapeHtml(t.aciklama||'-')}</td><td>${escapeHtml(t.amir||'Yönetici')}</td><td>${nedenSecimi}<input id="talep-aciklama-${t.talep_id}" placeholder="Ek açıklama" value="${escapeHtml(kararAciklamasi)}"><button class="btn-action" onclick="duzeltmeKarari(${t.talep_id},'ONAYLANDI','${escapeJs(tur)}')">✅ Onayla</button><button class="btn-action btn-del" onclick="duzeltmeKarari(${t.talep_id},'REDDEDİLDİ','${escapeJs(tur)}')">❌ Reddet</button></td></tr>`
        }).join('')||'<tr><td colspan="6" style="text-align:center;color:#4b8060">✅ Düzeltme veya devamsızlık bekleyen kayıt yok.</td></tr>'
    }catch(e){tbody.innerHTML='<tr><td colspan="6">Talepler yüklenemedi.</td></tr>'}
}
async function duzeltmeKarari(id,karar,tur){
    const zaman=document.getElementById('talep-zaman-'+id)?.value||'';
    const saatDuzeltme=['GİRİŞ UNUTULDU','ÇIKIŞ UNUTULDU','İNTERNET YOKTU'].includes((tur||'').toLocaleUpperCase('tr-TR'));
    if(karar==='ONAYLANDI'&&saatDuzeltme&&!zaman)return alert('Lütfen uygulanacak tarih ve saati seçin.');
    const neden=document.getElementById('talep-neden-'+id)?.value||'';
    const ek=document.getElementById('talep-aciklama-'+id)?.value||'';
    const aciklama=[neden,ek].filter(Boolean).join(' — ');
    const f=new FormData();f.append('talep_id',String(id));f.append('karar',karar);f.append('duzeltilmis_zaman',zaman);f.append('aciklama',aciklama);
    const r=await fetch('/api/admin/duzeltme-karar',{method:'POST',body:f,cache:'no-store'}),v=await r.json();alert(v.message);if(v.status==='success'){await duzeltmeTalepleriniYukle();await verileriYenile()}
}
document.addEventListener("click",e=>{if(!e.target.closest(".arama-kutusu"))document.getElementById("personel-arama-sonuclari")?.classList.remove("acik")})
document.addEventListener("keydown",e=>{if(e.key==="Escape"){personelPenceresiKapat();subePenceresiKapat();subeSecimPenceresiKapat();sicilPenceresiKapat();kartPenceresiKapat()}})

async function illeriYukle(){
    const sec=document.getElementById("p_il"); if(sec.options.length>1)return;
    try{const r=await fetch('/api/adres/iller');const v=await r.json();sec.innerHTML='<option value="">İl seçiniz</option>'+v.data.map(x=>`<option value="${escapeHtml(x.name)}" data-id="${x.id}">${escapeHtml(x.name)}</option>`).join('')}catch(e){document.getElementById('adres-elle').checked=true;adresElleDegisti()}
}
async function ilDegisti(){
    const il=document.getElementById('p_il'),id=il.selectedOptions[0]?.dataset.id,ilce=document.getElementById('p_ilce');document.getElementById('p_mahalle').innerHTML='<option value="">Önce ilçe seçiniz</option>';if(!id){ilce.innerHTML='<option value="">Önce il seçiniz</option>';return}ilce.innerHTML='<option value="">Yükleniyor...</option>';
    try{const r=await fetch('/api/adres/ilceler/'+id);const v=await r.json();if(!r.ok||!Array.isArray(v.data)||!v.data.length)throw new Error(v.message||'İlçe bulunamadı');ilce.innerHTML='<option value="">İlçe seçiniz</option>'+v.data.map(x=>`<option value="${escapeHtml(x.name)}" data-id="${x.id}">${escapeHtml(x.name)}</option>`).join('')}catch(e){ilce.innerHTML='<option value="">İlçeler alınamadı — elle giriş kullanın</option>'}
}
async function ilceDegisti(){
    const ilce=document.getElementById('p_ilce'),id=ilce.selectedOptions[0]?.dataset.id,m=document.getElementById('p_mahalle');if(!id){m.innerHTML='<option value="">Önce ilçe seçiniz</option>';return}m.innerHTML='<option value="">Yükleniyor...</option>';
    try{const r=await fetch('/api/adres/mahalleler/'+id);const v=await r.json();if(!r.ok||!Array.isArray(v.data)||!v.data.length)throw new Error(v.message||'Mahalle bulunamadı');m.innerHTML='<option value="">Mahalle seçiniz</option>'+v.data.map(x=>`<option value="${escapeHtml(x.name)}" data-posta="${escapeHtml(x.postalCode||'')}">${escapeHtml(x.name)}</option>`).join('')}catch(e){m.innerHTML='<option value="">Mahalleler alınamadı — elle giriş kullanın</option>'}
}
function mahalleDegisti(){const p=document.getElementById('p_mahalle').selectedOptions[0]?.dataset.posta;if(p)document.getElementById('p_posta_kodu').value=p}
function adresElleDegisti(){const elle=document.getElementById('adres-elle').checked;document.getElementById('adres-elle-alanlar').style.display=elle?'grid':'none';['p_il','p_ilce','p_mahalle'].forEach(id=>document.getElementById(id).required=!elle);['p_il_elle','p_ilce_elle','p_mahalle_elle'].forEach(id=>document.getElementById(id).required=elle)}
async function adresSeciminiYukle(il,ilce,mahalle){
    await illeriYukle();const i=document.getElementById('p_il');i.value=il||'';if(!i.value&&il){document.getElementById('adres-elle').checked=true;adresElleDegisti();document.getElementById('p_il_elle').value=il||'';document.getElementById('p_ilce_elle').value=ilce||'';document.getElementById('p_mahalle_elle').value=mahalle||'';return}await ilDegisti();document.getElementById('p_ilce').value=ilce||'';await ilceDegisti();document.getElementById('p_mahalle').value=mahalle||''
}

function askerlikAlaniniGuncelle() {
    document.getElementById("askerlik-alanlari").style.display = document.getElementById("p_cinsiyet").value === "Erkek" ? "grid" : "none";
}

async function firmaAyarlariniYukle() {
    try {
        const r = await fetch("/api/admin/firma-ayarlari"); const v = await r.json();
        if (v.status === "success") {
            document.getElementById("gec_kalma_kontrolu").value = String(v.data.gec_kalma_kontrolu || 0);
            document.getElementById("tolerans_dakika").value = v.data.tolerans_dakika ?? 20;
            document.getElementById("test_modu").value = String(v.data.test_modu || 0);
        }
    } catch(e) {}
}

async function kartPenceresiAc(id, ad){document.getElementById('kart_personel_id').value=id;document.getElementById('kart-personel-adi').textContent=ad;document.getElementById('kart-modal').classList.add('acik');await kartlariYukle()}
function kartPenceresiKapat(){document.getElementById('kart-modal').classList.remove('acik')}
async function kartlariYukle(){const id=document.getElementById('kart_personel_id').value;const r=await fetch('/api/admin/personel-kartlari/'+id);const v=await r.json();document.getElementById('kart-listesi').innerHTML=v.data.length?'<table><thead><tr><th>Kart</th><th>Tür</th><th>Durum</th><th>Geçerlilik</th></tr></thead><tbody>'+v.data.map(k=>`<tr><td>${escapeHtml(k.kart_no)}</td><td>${escapeHtml(k.kart_turu)}</td><td>${escapeHtml(k.kart_durumu)}</td><td>${escapeHtml(k.gecerlilik_tarihi||'-')}</td></tr>`).join('')+'</tbody></table>':'Henüz kart atanmamış.'}
async function kartAta(){const fd=new FormData();fd.append('personel_id',document.getElementById('kart_personel_id').value);fd.append('kart_no',document.getElementById('kart_no').value);fd.append('kart_turu',document.getElementById('kart_turu').value);fd.append('gecerlilik_tarihi',document.getElementById('kart_gecerlilik').value);const r=await fetch('/api/admin/personel-kart-ata',{method:'POST',body:fd});const v=await r.json();alert(v.message);if(v.status==='success'){document.getElementById('kart_no').value='';await kartlariYukle()}}

async function firmaAyarlariniKaydet() {
    const fd = new FormData(); fd.append("gec_kalma_kontrolu", document.getElementById("gec_kalma_kontrolu").value); fd.append("tolerans_dakika", document.getElementById("tolerans_dakika").value); fd.append("test_modu", document.getElementById("test_modu").value);
    const r = await fetch("/api/admin/firma-ayarlari", {method:"POST", body:fd}); const v = await r.json(); alert(v.message || "İşlem tamamlandı.");
}

async function tumPersonelVerileriniTemizle() {
    if (!confirm("BÜTÜN personeller ve bağlı geçmiş kayıtları kalıcı silinecek. Devam edilsin mi?")) return;
    const metin = prompt('Onaylamak için TÜM PERSONELLERİ SİL yazın:');
    if (metin !== "TÜM PERSONELLERİ SİL") return alert("Onay metni doğru yazılmadığı için işlem iptal edildi.");
    if (!confirm("Bu işlem geri alınamaz. Son kez onaylıyor musunuz?")) return;
    const fd = new FormData(); fd.append("onay_metni", metin);
    try {
        const r = await fetch("/api/admin/tum-personel-verilerini-temizle", {method:"POST", body:fd});
        const v = await r.json(); alert(v.message || "İşlem tamamlandı.");
        if (v.status === "success") personelListesiYenile();
    } catch (e) { alert("Sunucu bağlantı hatası oluştu."); }
}

async function excelOnizle(onay) {
    const excel = document.getElementById("excel_dosya").files[0];
    const fotograflar = document.getElementById("excel_fotograflar").files[0];
    if (!excel || !fotograflar) return alert("Excel ve fotoğraf ZIP dosyasını seçin.");
    const fd = new FormData(); fd.append("excel", excel); fd.append("fotograflar", fotograflar); fd.append("onay", onay ? "1" : "0");
    const alan = document.getElementById("excel-sonuc"); alan.innerHTML = "Kontrol ediliyor...";
    try {
        const cevap = await fetch("/api/admin/personel-excel-aktar", {method:"POST", body:fd});
        const veri = await cevap.json();
        if (veri.status !== "success") { alan.innerHTML = `<div style="color:#c0392b">${escapeHtml(veri.message || "Aktarım hatası")}</div>`; return; }
        const satirlar = (veri.data || []).map(x => `<tr><td>${x.satir}</td><td>${escapeHtml(x.sicil_no)}</td><td>${escapeHtml(x.ad_soyad)}</td><td style="color:${x.hatalar.length ? '#c0392b':'#16883e'}">${x.hatalar.length ? escapeHtml(x.hatalar.join(', ')) : 'Uygun'}</td></tr>`).join("");
        alan.innerHTML = `<p><b>Uygun:</b> ${veri.gecerli || 0} &nbsp; <b>Hatalı:</b> ${veri.hatali || 0}</p><div style="overflow:auto;max-height:350px"><table><thead><tr><th>Satır</th><th>Sicil</th><th>Personel</th><th>Sonuç</th></tr></thead><tbody>${satirlar}</tbody></table></div>` + (!onay && !veri.hatali ? `<button type="button" class="geo-button blue" onclick="excelOnizle(true)">Onayla ve Personelleri Aktar</button>` : "");
        if (onay) { alert(veri.message); personelListesiYenile(); }
    } catch(e) { alan.textContent = "Sunucu bağlantı hatası."; }
}

/* ============================================================
   PERSONEL SİL
============================================================ */

async function personelSil(id) {

    const onay =
        confirm(
            "Bu personeli pasif duruma almak istediğinize emin misiniz?"
        );


    if (!onay) {
        return;
    }


    const formData =
        new FormData();


    formData.append(
        "personel_id",
        id
    );


    try {

        const response =
            await fetch(
                window.location.origin +
                "/api/admin/personel-sil",
                {
                    method: "POST",
                    body: formData
                }
            );


        const result =
            await response.json();


        alert(
            result.message ||
            "İşlem tamamlandı."
        );


        personelListesiYenile();

    } catch (error) {

        console.error(error);

        alert(
            "Personel silinirken hata oluştu."
        );
    }
}


/* ============================================================
   ŞUBE LİSTESİ
============================================================ */

async function subeListesiYenile() {

    try {

        const response =
            await fetch(
                window.location.origin +
                "/api/admin/sube-listesi"
            );


        const result =
            await response.json();


        const tbody =
            document.getElementById(
                "admin-sube-table"
            );


        if (!tbody) {
            return;
        }


        let html = "";


        const data =
            Array.isArray(result.data)
                ? result.data
                : [];

        subeVerileri = data;
        kayitliSubeleriHaritadaGoster(false);
        const personelSube = document.getElementById("p_sube_id");
        if (personelSube) {
            const secili = personelSube.value;
            personelSube.innerHTML = '<option value="">Şube Atanmamış</option>' +
                data.map(s => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.sube_adi)}</option>`).join("");
            personelSube.value = secili;
            ekSubeAlaniniDoldur();
        }


        data.forEach(
            function(s) {

                html += `

                    <tr>

                        <td>
                            ${escapeHtml(s.id)}
                        </td>

                        <td>
                            <b>
                                ${escapeHtml(
                                    s.sube_adi
                                )}
                            </b>
                        </td>

                        <td>
                            ${escapeHtml(
                                s.enlem
                            )},
                            ${escapeHtml(
                                s.boylam
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                s.guvenli_yari_cap
                            )} m
                        </td>

                        <td>

                            <button
                                class="btn-action"
                                onclick="subeDuzenle('${escapeJs(s.id)}')"
                            >
                                ✏️ Düzenle
                            </button>

                            <button
                                class="btn-action btn-del"
                                onclick="subeSil('${escapeJs(s.id)}')"
                            >
                                🗑️ Sil
                            </button>

                        </td>

                    </tr>

                `;
            }
        );


        tbody.innerHTML =
            html ||
            `
                <tr>
                    <td colspan="5"
                        style="text-align:center;">
                        Tanımlı şube bulunamadı.
                    </td>
                </tr>
            `;

    } catch (error) {

        console.error(
            "Şube listesi hatası:",
            error
        );
    }
}


/* ============================================================
   ŞUBE EKLE
============================================================ */

async function subeEkle(event) {

    event.preventDefault();


    const subeAdi =
        document.getElementById(
            "s_adi"
        ).value.trim();


    const enlem =
        document.getElementById(
            "s_enlem"
        ).value.trim();


    const boylam =
        document.getElementById(
            "s_boylam"
        ).value.trim();


    const cap =
        document.getElementById(
            "s_cap"
        ).value.trim();


    const lat =
        parseFloat(
            enlem.replace(",", ".")
        );


    const lng =
        parseFloat(
            boylam.replace(",", ".")
        );


    const radius =
        parseFloat(
            cap.replace(",", ".")
        );


    if (
        !subeAdi ||
        !Number.isFinite(lat) ||
        !Number.isFinite(lng) ||
        !Number.isFinite(radius)
    ) {

        alert(
            "Lütfen geçerli şube bilgileri girin."
        );

        return;
    }


    if (
        lat < -90 ||
        lat > 90 ||
        lng < -180 ||
        lng > 180
    ) {

        alert(
            "Enlem veya boylam değeri geçersiz."
        );

        return;
    }


    if (radius <= 0) {

        alert(
            "Güvenli alan yarıçapı 0'dan büyük olmalıdır."
        );

        return;
    }


    const formData =
        new FormData();

    const subeId = document.getElementById("s_id").value;


    formData.append(
        "sube_adi",
        subeAdi
    );


    formData.append(
        "enlem",
        lat.toFixed(6)
    );


    formData.append(
        "boylam",
        lng.toFixed(6)
    );


    formData.append(
        "guvenli_yari_cap",
        radius
    );

    if (subeId) {
        formData.append("s_id", subeId);
    }


    try {

        const response =
            await fetch(
                window.location.origin +
                (subeId ? "/api/admin/sube-guncelle" : "/api/admin/sube-ekle"),
                {
                    method: "POST",
                    body: formData
                }
            );


        const result =
            await response.json();


        alert(
            result.message ||
            "Şube işlemi tamamlandı."
        );


        /*
         * Formu sıfırla
         */

        event.target.reset();


        /*
         * Çap tekrar 50 olsun
         */

        document.getElementById(
            "s_cap"
        ).value = 50;

        document.getElementById("s_id").value = "";
        document.getElementById("sube-kaydet-btn").innerText = "📍 Konumu İşle ve Şubeyi Kaydet";


        /*
         * Harita katmanlarını temizle
         */

        if (
            haritaNesnesi &&
            haritaMarker
        ) {

            haritaNesnesi.removeLayer(
                haritaMarker
            );

            haritaMarker = null;
        }


        if (
            haritaNesnesi &&
            haritaDaire
        ) {

            haritaNesnesi.removeLayer(
                haritaDaire
            );

            haritaDaire = null;
        }


        if (gpsMarker) {

            if (haritaNesnesi) {

                haritaNesnesi.removeLayer(
                    gpsMarker
                );
            }

            gpsMarker = null;
        }


        document.getElementById(
            "map-info"
        ).innerHTML =
            "📍 Yeni şube için koordinat bekleniyor...";


        /*
         * Listeyi yenile
         */

        subeListesiYenile();

    } catch (error) {

        console.error(
            "Şube ekleme hatası:",
            error
        );


        alert(
            "Şube kaydedilirken sunucu hatası oluştu."
        );
    }
}


/* ============================================================
   ŞUBE DÜZENLE
============================================================ */

function subeDuzenle(id) {
    const s = subeVerileri.find(x => String(x.id) === String(id));
    if (!s) return;
    document.getElementById("s_id").value = s.id || "";
    document.getElementById("s_adi").value = s.sube_adi || "";
    document.getElementById("s_enlem").value = s.enlem || "";
    document.getElementById("s_boylam").value = s.boylam || "";
    document.getElementById("s_cap").value = s.guvenli_yari_cap || 50;
    document.getElementById("sube-kaydet-btn").innerText = "💾 Şube Değişikliklerini Kaydet";
    document.getElementById("sube-modal-baslik").textContent = "✏️ Şube Düzenle";
    document.getElementById("sube-modal").classList.add("acik");
    pencereDurumu("sube-modal","normal");
    setTimeout(()=>{haritayiIlkle();haritaNesnesi?.invalidateSize();kayitliSubeleriHaritadaGoster(false);haritayiGuncelle()},220);
}


/* ============================================================
   ŞUBE SİL
============================================================ */

async function subeSil(id) {

    const onay =
        confirm(
            "Bu şubeyi silmek istediğinize emin misiniz?"
        );


    if (!onay) {
        return;
    }


    const formData =
        new FormData();


    formData.append(
        "sube_id",
        id
    );


    try {

        const response =
            await fetch(
                window.location.origin +
                "/api/admin/sube-sil",
                {
                    method: "POST",
                    body: formData
                }
            );


        const result =
            await response.json();


        alert(
            result.message ||
            "İşlem tamamlandı."
        );


        subeListesiYenile();

    } catch (error) {

        console.error(error);

        alert(
            "Şube silinirken hata oluştu."
        );
    }
}


/* ============================================================
   SAYAÇLAR
============================================================ */

function sayaclariGuncelle(veriler) {
    // Ana PDKS sayaçları artık ham log sayısından değil günlük çalışma planından hesaplanır.
}



/* ============================================================
   CANLI ARAMA
============================================================ */

function canliAra() {

    const search =
        document.getElementById(
            "panel-search"
        );


    if (!search) {
        return;
    }


    const kelime =
        search.value
            .toLowerCase()
            .trim();


    const filtreli =
        tumLoglar.filter(
            function(log) {

                const personel =
                    String(
                        log.personel || ""
                    ).toLowerCase();


                const sube =
                    String(
                        log.sube || ""
                    ).toLowerCase();


                const durum =
                    String(
                        log.durum_etiketi || ""
                    ).toLowerCase();


                return (
                    personel.includes(kelime) ||
                    sube.includes(kelime) ||
                    durum.includes(kelime)
                );
            }
        );


    tabloyuCiz(
        filtreli
    );
}


/* ============================================================
   HTML GÜVENLİK
============================================================ */

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }


    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* ============================================================
   JAVASCRIPT STRING GÜVENLİK
============================================================ */

function escapeJs(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }


    return String(value)
        .replaceAll("\\", "\\\\")
        .replaceAll("'", "\\'")
        .replaceAll("\n", "\\n")
        .replaceAll("\r", "\\r");
}


/* ============================================================
   SAYFA AÇILIŞI
============================================================ */

window.addEventListener(
    "DOMContentLoaded",
    function() {

        const oturum =
            localStorage.getItem(
                "pdks_admin_oturum"
            );


        if (
            oturum === "acik"
        ) {

            document.getElementById(
                "login-block-layer"
            ).style.display = "none";


            document.getElementById(
                "main-panel-view"
            ).style.display = "block";


            /*
             * Haritayı başlat
             */

            setTimeout(
                function() {

                    haritayiIlkle();

                },
                100
            );


            /*
             * Verileri getir
             */

            yonetimPaneliVerileriniYukle();
            firmaAyarlariniYukle();


            /*
             * 5 saniyede bir güncelle
             */

            if (!window.pdksInterval) {

                window.pdksInterval =
                    setInterval(
                        yonetimPaneliVerileriniYukle,
                        5000
                    );
            }

        }

    }
);

