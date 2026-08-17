from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import os
import httpx

from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# BetAI Backend
# =========================================================

app = FastAPI(
    title="BetAI Backend",
    version="2.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# API AYARLARI
# =========================================================

API_KEY = os.getenv("API_FOOTBALL_KEY")

API_BASE = "https://v3.football.api-sports.io"

TURKEY_TZ = ZoneInfo("Europe/Istanbul")


# =========================================================
# API İSTEK FONKSİYONU
# =========================================================

async def api_get(endpoint, params=None):

    headers = {
        "x-apisports-key": API_KEY
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.get(
            f"{API_BASE}/{endpoint}",
            headers=headers,
            params=params or {}
        )

    if response.status_code != 200:
        return None

    return response.json()


# =========================================================
# ANA SAYFA
# =========================================================

@app.get("/")
async def home():

    return {
        "status": "online",
        "app": "BetAI",
        "message": "BetAI Backend calisiyor!"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "api_key": bool(API_KEY),
        "service": "BetAI Backend"
    }


# =========================================================
# TEK MAÇ ANALİZİ
# =========================================================

@app.get("/api/analyze/{fixture_id}")
async def analyze_match(fixture_id: int):

    if not API_KEY:

        return JSONResponse(
            status_code=500,
            content={
                "error": "API_FOOTBALL_KEY bulunamadi"
            }
        )

    data = await api_get(
        "predictions",
        {
            "fixture": fixture_id
        }
    )

    if not data:

        return JSONResponse(
            status_code=502,
            content={
                "error": "API-Football predictions verisi alinamadi"
            }
        )

    predictions = data.get(
        "response",
        []
    )

    if not predictions:

        return {
            "status": "no_prediction",
            "fixture_id": fixture_id,
            "message": "Bu mac icin henuz analiz verisi yok."
        }

    prediction = predictions[0]

    teams = prediction.get(
        "teams",
        {}
    )

    home = teams.get(
        "home",
        {}
    )

    away = teams.get(
        "away",
        {}
    )

    predictions_data = prediction.get(
        "predictions",
        {}
    )

    percent = predictions_data.get(
        "percent",
        {}
    )

    goals = predictions_data.get(
        "goals",
        {}
    )

    score = predictions_data.get(
        "score",
        {}
    )

    # -------------------------------------------------------
    # Yüzdeleri sayıya çevir
    # -------------------------------------------------------

    def percentage(value):

        if value is None:
            return None

        try:
            return float(
                str(value).replace("%", "")
            )

        except:
            return None

    home_probability = percentage(
        percent.get("home")
    )

    draw_probability = percentage(
        percent.get("draw")
    )

    away_probability = percentage(
        percent.get("away")
    )

    # -------------------------------------------------------
    # En yüksek olasılık
    # -------------------------------------------------------

    probabilities = {
        "Ev Sahibi": home_probability or 0,
        "Beraberlik": draw_probability or 0,
        "Deplasman": away_probability or 0
    }

    best_prediction = max(
        probabilities,
        key=probabilities.get
    )

    best_probability = probabilities[
        best_prediction
    ]

    # -------------------------------------------------------
    # KG / ÜST ALT
    # -------------------------------------------------------

    advice = predictions_data.get(
        "advice"
    )

    under_over = predictions_data.get(
        "under_over"
    )

    win_or_draw = predictions_data.get(
        "win_or_draw"
    )

    # -------------------------------------------------------
    # CEVAP
    # -------------------------------------------------------

    return {
        "status": "success",

        "fixture_id": fixture_id,

        "home": home.get(
            "name",
            "Bilinmiyor"
        ),

        "away": away.get(
            "name",
            "Bilinmiyor"
        ),

        "prediction": {

            "winner": predictions_data.get(
                "winner",
                {}
            ),

            "advice": advice,

            "best_prediction": best_prediction,

            "confidence": round(
                best_probability,
                1
            ),

            "home_probability":
                home_probability,

            "draw_probability":
                draw_probability,

            "away_probability":
                away_probability,

            "under_over":
                under_over,

            "win_or_draw":
                win_or_draw,

            "goals": goals,

            "predicted_score": score
        }
    }


# =========================================================
# BUGÜNÜN MAÇLARI
# =========================================================

@app.get("/api/matches")
async def matches():

    if not API_KEY:

        return JSONResponse(
            status_code=500,
            content={
                "error": "API_FOOTBALL_KEY bulunamadi",
                "matches": []
            }
        )

    today = datetime.now(
        TURKEY_TZ
    ).strftime("%Y-%m-%d")

    data = await api_get(
        "fixtures",
        {
            "date": today,
            "timezone": "Europe/Istanbul"
        }
    )

    if not data:

        return JSONResponse(
            status_code=502,
            content={
                "error": "API-Football verisi alinamadi",
                "matches": []
            }
        )

    api_matches = data.get(
        "response",
        []
    )

    result = []

    # =====================================================
    # MAÇLARI İŞLE
    # =====================================================

    for match in api_matches:

        fixture = match.get(
            "fixture",
            {}
        )

        teams = match.get(
            "teams",
            {}
        )

        league = match.get(
            "league",
            {}
        )

        home_team = teams.get(
            "home",
            {}
        )

        away_team = teams.get(
            "away",
            {}
        )

        timestamp = fixture.get(
            "timestamp"
        )

        if timestamp:

            match_time = datetime.fromtimestamp(
                timestamp,
                TURKEY_TZ
            ).strftime("%H:%M")

        else:

            match_time = "--:--"

        result.append({

            "fixture_id":
                fixture.get("id"),

            "league":
                league.get(
                    "name",
                    "Bilinmiyor"
                ),

            "time":
                match_time,

            "home":
                home_team.get(
                    "name",
                    "Bilinmiyor"
                ),

            "away":
                away_team.get(
                    "name",
                    "Bilinmiyor"
                ),

            "home_team_id":
                home_team.get("id"),

            "away_team_id":
                away_team.get("id"),

            "status":
                fixture.get(
                    "status",
                    {}
                ).get(
                    "short",
                    ""
                ),

            "ai_status":
                "Analiz için hazır",

            "home_probability":
                None,

            "draw_probability":
                None,

            "away_probability":
                None,

            "btts":
                None,

            "over25":
                None
        })

    return {
        "status": "success",
        "date": today,
        "count": len(result),
        "matches": result
    }


# =========================================================
# ÖNE ÇIKAN MAÇLAR
# =========================================================

@app.get("/api/top-picks")
async def top_picks():

    if not API_KEY:

        return JSONResponse(
            status_code=500,
            content={
                "error": "API_FOOTBALL_KEY bulunamadi",
                "matches": []
            }
        )

    today = datetime.now(
        TURKEY_TZ
    ).strftime("%Y-%m-%d")

    data = await api_get(
        "fixtures",
        {
            "date": today,
            "timezone": "Europe/Istanbul"
        }
    )

    if not data:

        return JSONResponse(
            status_code=502,
            content={
                "error": "Maclar alinamadi",
                "matches": []
            }
        )

    fixtures = data.get(
        "response",
        []
    )

    picks = []

    # -------------------------------------------------------
    # Sadece oynanmamış maçlar
    # -------------------------------------------------------

    upcoming = []

    for match in fixtures:

        status = match.get(
            "fixture",
            {}
        ).get(
            "status",
            {}
        ).get(
            "short",
            ""
        )

        if status == "NS":
            upcoming.append(match)

    # -------------------------------------------------------
    # İlk 20 maç üzerinde analiz
    #
    # API kotasını gereksiz yere tüketmemek için
    # bütün 144 maçı aynı anda analiz etmiyoruz.
    # -------------------------------------------------------

    for match in upcoming[:20]:

        fixture = match.get(
            "fixture",
            {}
        )

        fixture_id = fixture.get(
            "id"
        )

        try:

            prediction_data = await api_get(
                "predictions",
                {
                    "fixture": fixture_id
                }
            )

            responses = prediction_data.get(
                "response",
                []
            ) if prediction_data else []

            if not responses:
                continue

            prediction = responses[0]

            teams = prediction.get(
                "teams",
                {}
            )

            home = teams.get(
                "home",
                {}
            )

            away = teams.get(
                "away",
                {}
            )

            pred = prediction.get(
                "predictions",
                {}
            )

            percent = pred.get(
                "percent",
                {}
            )

            def pct(value):

                try:

                    return float(
                        str(value).replace(
                            "%",
                            ""
                        )
                    )

                except:

                    return 0

            hp = pct(
                percent.get("home")
            )

            dp = pct(
                percent.get("draw")
            )

            ap = pct(
                percent.get("away")
            )

            probabilities = {
                "Ev Sahibi": hp,
                "Beraberlik": dp,
                "Deplasman": ap
            }

            best = max(
                probabilities,
                key=probabilities.get
            )

            confidence = probabilities[
                best
            ]

            # Sadece %60 ve üzerindeki
            # tahminleri öne çıkar
            if confidence >= 60:

                picks.append({

                    "fixture_id":
                        fixture_id,

                    "league":
                        match.get(
                            "league",
                            {}
                        ).get(
                            "name",
                            "Bilinmiyor"
                        ),

                    "home":
                        home.get(
                            "name",
                            "Bilinmiyor"
                        ),

                    "away":
                        away.get(
                            "name",
                            "Bilinmiyor"
                        ),

                    "prediction":
                        best,

                    "confidence":
                        round(
                            confidence,
                            1
                        ),

                    "home_probability":
                        hp,

                    "draw_probability":
                        dp,

                    "away_probability":
                        ap,

                    "advice":
                        pred.get(
                            "advice"
                        ),

                    "under_over":
                        pred.get(
                            "under_over"
                        ),

                    "predicted_score":
                        pred.get(
                            "score"
                        )
                })

        except Exception:
            continue

    # -------------------------------------------------------
    # Güven oranına göre sırala
    # -------------------------------------------------------

    picks.sort(
        key=lambda x:
            x["confidence"],
        reverse=True
    )

    return {

        "status": "success",

        "date": today,

        "count":
            len(picks),

        "matches":
            picks[:10]
    }
