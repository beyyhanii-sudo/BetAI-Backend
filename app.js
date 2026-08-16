// ===============================
// BetAI - app.js
// ===============================

// Backend adresini daha sonra buraya yazacağız.
// Şimdilik boş bırakıyoruz.
const BACKEND_URL = "";

// Sayfadaki elemanları bul
const matchesBox = document.getElementById("matches");
const statusBox = document.getElementById("status");
const dateBox = document.getElementById("date");
const refreshButton = document.getElementById("refreshBtn");


// ===============================
// BUGÜNÜN TARİHİ
// ===============================

function showDate() {

    const now = new Date();

    dateBox.textContent =
        now.toLocaleDateString("tr-TR", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric"
        });
}


// ===============================
// GÜVENLİ METİN
// ===============================

function safeText(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ===============================
// YÜKLENİYOR
// ===============================

function loading() {

    matchesBox.innerHTML = `
        <div class="loading">
            ⚡ Maçlar yükleniyor...
        </div>
    `;

    statusBox.textContent =
        "Sistem hazırlanıyor...";
}


// ===============================
// BACKEND YOKSA
// ===============================

function backendNotReady() {

    matchesBox.innerHTML = `
        <div class="empty">

            <h3>🤖 BetAI Hazır</h3>

            <p>
                Maç sistemi henüz sunucuya bağlanmadı.
            </p>

            <p>
                Backend bağlantısını bir sonraki
                aşamada kuracağız.
            </p>

        </div>
    `;

    statusBox.textContent =
        "Backend bekleniyor";
}


// ===============================
// MAÇLARI GETİR
// ===============================

async function loadMatches() {

    loading();

    refreshButton.disabled = true;

    // Backend adresi henüz girilmediyse
    if (!BACKEND_URL) {

        backendNotReady();

        refreshButton.disabled = false;

        return;
    }


    try {

        statusBox.textContent =
            "Sunucuya bağlanıyor...";


        const response =
            await fetch(
                BACKEND_URL + "/api/matches"
            );


        if (!response.ok) {

            throw new Error(
                "Sunucu cevap vermedi. HTTP: " +
                response.status
            );
        }


        const data =
            await response.json();


        if (
            !data.matches ||
            data.matches.length === 0
        ) {

            matchesBox.innerHTML = `
                <div class="empty">

                    Bugün için maç bulunamadı.

                </div>
            `;

            statusBox.textContent =
                "0 maç bulundu";

            return;
        }


        statusBox.textContent =
            data.matches.length +
            " maç bulundu";


        showMatches(data.matches);


    } catch (error) {

        console.log(error);

        matchesBox.innerHTML = `
            <div class="empty error">

                <h3>⚠️ Bağlantı kurulamadı</h3>

                <p>
                    ${safeText(error.message)}
                </p>

            </div>
        `;

        statusBox.textContent =
            "Bağlantı hatası";

    } finally {

        refreshButton.disabled = false;
    }
}


// ===============================
// MAÇLARI EKRANA BAS
// ===============================

function showMatches(matches) {

    matchesBox.innerHTML = "";


    matches.forEach(function(match) {

        const home =
            safeText(match.home);

        const away =
            safeText(match.away);

        const league =
            safeText(match.league);

        const time =
            safeText(match.time);


        const homeProbability =
            match.home_probability ??
            "—";

        const drawProbability =
            match.draw_probability ??
            "—";

        const awayProbability =
            match.away_probability ??
            "—";

        const btts =
            match.btts ??
            "—";

        const over25 =
            match.over25 ??
            "—";


        const card =
            document.createElement("div");


        card.className =
            "match";


        card.innerHTML = `

            <div class="match-head">

                <span>
                    ${league}
                </span>

                <span class="time">
                    ${time}
                </span>

            </div>


            <div class="teams">

                <div class="team">
                    ${home}
                </div>

                <div class="vs">
                    VS
                </div>

                <div class="team">
                    ${away}
                </div>

            </div>


            <div class="ai">

                <div class="ai-title">

                    <b>
                        🤖 AI ANALİZ
                    </b>

                    <span>
                        BetAI
                    </span>

                </div>


                <div class="probs">

                    <div class="prob">

                        <strong>
                            ${homeProbability}%
                        </strong>

                        <small>
                            Ev Sahibi
                        </small>

                    </div>


                    <div class="prob">

                        <strong>
                            ${drawProbability}%
                        </strong>

                        <small>
                            Beraberlik
                        </small>

                    </div>


                    <div class="prob">

                        <strong>
                            ${awayProbability}%
                        </strong>

                        <small>
                            Deplasman
                        </small>

                    </div>

                </div>


                <div class="extra">

                    <div>

                        KG

                        <b>
                            ${btts}%
                        </b>

                    </div>


                    <div>

                        2.5 Üst

                        <b>
                            ${over25}%
                        </b>

                    </div>

                </div>

            </div>


            <button
                class="detail"
                onclick="showDetails(
                    '${home}',
                    '${away}'
                )">

                Detaylı Analiz

            </button>

        `;


        matchesBox.appendChild(card);

    });
}


// ===============================
// DETAY
// ===============================

function showDetails(home, away) {

    alert(
        "🤖 BetAI\n\n" +
        home +
        " - " +
        away +
        "\n\n" +
        "Detaylı istatistik ve AI " +
        "analiz motoru backend " +
        "bağlandıktan sonra çalışacak."
    );
}


// ===============================
// YENİLE BUTONU
// ===============================

refreshButton.addEventListener(
    "click",
    loadMatches
);


// ===============================
// BAŞLAT
// ===============================

showDate();

loadMatches();