from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo

app = FastAPI(
    title="BetAI Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_URL = "https://v3.football.api-sports.io"

TURKEY_TZ = ZoneInfo("Europe/Istanbul")


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
# API-FOOTBALL İSTEK
# =========================================================

async def football_request(endpoint, params=None):

    if not API_KEY:
        return None, "API_FOOTBALL_KEY bulunamadi"

    headers = {
        "x-apisports-key": API_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.get(
                f"{API_URL}/{endpoint}",
                headers=headers,
                params=params or {}
            )

        if response.status_code != 200:
            return None, f"API-Football HTTP {response.status_code}"

        data = response.json()

        errors = data.get("errors")

        if errors:
            return None, str(errors)

        return data, None

    except Exception as error:
        return None, str(error)


# =========================================================
# BUGÜNÜN MAÇLARI
# =========================================================

@app.get("/api/matches")
async def matches():

    today = datetime.now(TURKEY_TZ).strftime("%Y-%m-%d")

    data, error = await football_request(
        "fixtures",
        {
            "date": today
        }
    )

    if error:
        return JSONResponse(
            status_code=502,
            content={
                "error": error,
                "matches": []
            }
        )

    api_matches = data.get("response", [])

    result = []

    for match in api_matches:

        fixture = match.get("fixture", {})
        teams = match.get("teams", {})
        league = match.get("league", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        timestamp = fixture.get("timestamp")

        if timestamp:
            match_time = datetime.fromtimestamp(
                timestamp,
                TURKEY_TZ
            ).strftime("%H:%M")
        else:
            match_time = "--:--"

        result.append({
            "fixture_id": fixture.get("id"),
            "league": league.get("name", "Bilinmiyor"),
            "time": match_time,
            "home": home.get("name", "Bilinmiyor"),
            "away": away.get("name", "Bilinmiyor"),
            "status": fixture.get("status", {}).get("short", ""),
            "ai_status": "Analiz bekleniyor",
            "home_probability": None,
            "draw_probability": None,
            "away_probability": None,
            "btts": None,
            "over25": None
        })

    return {
        "status": "success",
        "date": today,
        "count": len(result),
        "matches": result
    }


# =========================================================
# TEK MAÇ ANALİZİ
# =========================================================

@app.get("/api/analyze/{fixture_id}")
async def analyze(fixture_id: int):

    # Önce maç bilgisini al
    fixture_data, fixture_error = await football_request(
        "fixtures",
        {
            "id": fixture_id
        }
    )

    if fixture_error:
        return JSONResponse(
            status_code=502,
            content={
                "error": "API-Football verisi alinamadi",
                "details": fixture_error,
                "fixture_id": fixture_id
            }
        )

    fixture_response = fixture_data.get("response", [])

    if not fixture_response:
        return {
            "status": "not_found",
            "fixture_id": fixture_id,
            "message": "Mac bulunamadi."
        }

    match = fixture_response[0]

    fixture = match.get("fixture", {})
    teams = match.get("teams", {})
    league = match.get("league", {})

    home = teams.get("home", {})
    away = teams.get("away", {})

    # API-Football predictions
    prediction_data, prediction_error = await football_request(
        "predictions",
        {
            "fixture": fixture_id
        }
    )

    prediction = None

    if prediction_data:
        prediction_response = prediction_data.get(
            "response",
            []
        )

        if prediction_response:
            prediction = prediction_response[0].get(
                "predictions"
            )

    # Prediction yoksa yine maç bilgisini döndür.
    if not prediction:

        return {
            "status": "no_prediction",
            "fixture_id": fixture_id,
            "league": league.get("name"),
            "home": home.get("name"),
            "away": away.get("name"),
            "message": "Bu mac icin henuz analiz verisi yok."
        }

    percent = prediction.get("percent", {})

    return {
        "status": "success",
        "fixture_id": fixture_id,
        "league": league.get("name"),
        "home": home.get("name"),
        "away": away.get("name"),

        "prediction": {
            "winner": prediction.get("winner"),
            "advice": prediction.get("advice"),
            "under_over": prediction.get("under_over"),
            "goals": prediction.get("goals"),
            "percent": {
                "home": percent.get("home"),
                "draw": percent.get("draw"),
                "away": percent.get("away")
            }
        },

        "ai_status": "Analiz hazır"
    }


# =========================================================
# TOP PICKS
# =========================================================

@app.get("/api/top-picks")
async def top_picks():

    today = datetime.now(TURKEY_TZ).strftime("%Y-%m-%d")

    matches_data, matches_error = await football_request(
        "fixtures",
        {
            "date": today,
            "status": "NS"
        }
    )

    if matches_error:
        return JSONResponse(
            status_code=502,
            content={
                "error": matches_error,
                "matches": []
            }
        )

    fixtures = matches_data.get("response", [])

    picks = []

    # İlk 30 maçta prediction kontrolü
    # API limitlerini gereksiz tüketmemek için.
    for match in fixtures[:30]:

        fixture = match.get("fixture", {})
        fixture_id = fixture.get("id")

        if not fixture_id:
            continue

        prediction_data, prediction_error = await football_request(
            "predictions",
            {
                "fixture": fixture_id
            }
        )

        if prediction_error:
            continue

        prediction_response = prediction_data.get(
            "response",
            []
        )

        if not prediction_response:
            continue

        prediction = prediction_response[0].get(
            "predictions",
            {}
        )

        percent = prediction.get(
            "percent",
            {}
        )

        home_probability = percent.get("home")
        draw_probability = percent.get("draw")
        away_probability = percent.get("away")

        probabilities = []

        for value in [
            home_probability,
            draw_probability,
            away_probability
        ]:
            if value:
                try:
                    probabilities.append(
                        float(
                            str(value).replace("%", "")
                        )
                    )
                except:
                    pass

        if not probabilities:
            continue

        confidence = max(probabilities)

        if confidence < 55:
            continue

        teams = match.get("teams", {})
        league = match.get("league", {})

        picks.append({
            "fixture_id": fixture_id,
            "league": league.get("name"),
            "home": teams.get("home", {}).get("name"),
            "away": teams.get("away", {}).get("name"),
            "time": datetime.fromtimestamp(
                fixture.get("timestamp"),
                TURKEY_TZ
            ).strftime("%H:%M")
            if fixture.get("timestamp")
            else "--:--",

            "prediction": prediction.get("advice"),

            "home_probability": home_probability,
            "draw_probability": draw_probability,
            "away_probability": away_probability,

            "confidence": confidence,

            "ai_status": "Analiz hazır"
        })

    picks.sort(
        key=lambda x: x["confidence"],
        reverse=True
    )

    return {
        "status": "success",
        "date": today,
        "count": len(picks),
        "matches": picks[:10]
    }
