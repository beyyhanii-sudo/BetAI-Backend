from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import os
import httpx

from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# BetAI BACKEND
# =========================================================

app = FastAPI(
    title="BetAI Backend",
    version="2.1.0"
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
# AYARLAR
# =========================================================

API_KEY = os.getenv("API_FOOTBALL_KEY")

API_URL = "https://v3.football.api-sports.io"

TURKEY_TZ = ZoneInfo("Europe/Istanbul")


# =========================================================
# API-FOOTBALL İSTEĞİ
# =========================================================

async def football_request(endpoint, params=None):

    if not API_KEY:

        return None, "API_FOOTBALL_KEY bulunamadi"

    headers = {
        "x-apisports-key": API_KEY
    }

    try:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.get(
                f"{API_URL}/{endpoint}",
                headers=headers,
                params=params or {}
            )

        # HTTP kontrolü
        if response.status_code != 200:

            return None, (
                f"API HTTP hatasi: "
                f"{response.status_code} - "
                f"{response.text[:500]}"
            )

        data = response.json()

        # API-Football kendi hata sistemi
        errors = data.get("errors")

        if errors:

            return None, str(errors)

        return data, None

    except Exception as error:

        return None, str(error)


# =========================================================
# ANA SAYFA
# =========================================================

@app.get("/")
async def home():

    return {
        "status": "online",
        "app": "BetAI",
        "version": "2.1.0",
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
# BUGÜNÜN MAÇLARI
# =========================================================

@app.get("/api/matches")
async def matches():

    today = datetime.now(
        TURKEY_TZ
    ).strftime("%Y-%m-%d")

    data, error = await football_request(
        "fixtures",
        {
            "date": today,
            "timezone": "Europe/Istanbul"
        }
    )

    # API hatası
    if error:

        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "error": "API-Football verisi alinamadi",
                "details": error,
                "date": today,
                "matches": []
            }
        )

    if not data:

        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "error": "API-Football bos cevap verdi",
                "date": today,
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

        home = teams.get(
            "home",
            {}
        )

        away = teams.get(
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
                home.get(
                    "name",
                    "Bilinmiyor"
                ),

            "away":
                away.get(
                    "name",
                    "Bilinmiyor"
                ),

            "status":
                fixture.get(
                    "status",
                    {}
                ).get(
                    "short",
                    ""
                ),

            "ai_status":
                "Analiz bekleniyor",

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

    # =====================================================
    # CEVAP
    # =====================================================

    return {

        "status":
            "success",

        "date":
            today,

        "count":
            len(result),

        "matches":
            result
    }


# =========================================================
# TEK MAÇ BİLGİSİ
# =========================================================

@app.get("/api/fixture/{fixture_id}")
async def fixture_info(
    fixture_id: int
):

    data, error = await football_request(
        "fixtures",
        {
            "id": fixture_id,
            "timezone": "Europe/Istanbul"
        }
    )

    if error:

        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "error": error,
                "fixture_id": fixture_id
            }
        )

    response = data.get(
        "response",
        []
    )

    if not response:

        return {
            "status": "not_found",
            "fixture_id": fixture_id,
            "message": "Mac bulunamadi."
        }

    return {
        "status": "success",
        "fixture_id": fixture_id,
        "fixture": response[0]
    }


# =========================================================
# SON 5 MAÇ
# =========================================================

async def get_recent_matches(team_id):

    data, error = await football_request(
        "fixtures",
        {
            "team": team_id,
            "last": 5
        }
    )

    if error:
        return []

    if not data:
        return []

    return data.get(
        "response",
        []
    )


# =========================================================
# FORM HESABI
# =========================================================

def calculate_form(
    fixtures,
    team_id
):

    points = 0
    goals_for = 0
    goals_against = 0
    games = 0

    for match in fixtures:

        teams = match.get(
            "teams",
            {}
        )

        goals = match.get(
            "goals",
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

        home_id = home.get(
            "id"
        )

        away_id = away.get(
            "id"
        )

        home_goals = goals.get(
            "home"
        )

        away_goals = goals.get(
            "away"
        )

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        games += 1

        if home_id == team_id:

            goals_for += home_goals
            goals_against += away_goals

            if home_goals > away_goals:

                points += 3

            elif home_goals == away_goals:

                points += 1

        elif away_id == team_id:

            goals_for += away_goals
            goals_against += home_goals

            if away_goals > home_goals:

                points += 3

            elif away_goals == home_goals:

                points += 1

    if games == 0:

        return {
            "games": 0,
            "points": 0,
            "goals_for": 0,
            "goals_against": 0,
            "form": 0
        }

    form = (
        points / (games * 3)
    ) * 100

    return {

        "games":
            games,

        "points":
            points,

        "goals_for":
            goals_for,

        "goals_against":
            goals_against,

        "form":
            round(
                form,
                1
            )
    }


# =========================================================
# BETAI TAHMİN MOTORU
# =========================================================

def calculate_prediction(
    home_form,
    away_form
):

    if (
        home_form["games"] == 0
        or away_form["games"] == 0
    ):

        return None

    home_games = home_form["games"]
    away_games = away_form["games"]

    home_attack = (
        home_form["goals_for"]
        / home_games
    )

    away_attack = (
        away_form["goals_for"]
        / away_games
    )

    home_defence = (
        home_form["goals_against"]
        / home_games
    )

    away_defence = (
        away_form["goals_against"]
        / away_games
    )

    home_form_score = (
        home_form["form"]
        / 100
    )

    away_form_score = (
        away_form["form"]
        / 100
    )

    # -----------------------------------------------------
    # 1X2 PUANLARI
    # -----------------------------------------------------

    home_score = (
        50
        + (
            home_form_score
            - away_form_score
        ) * 25
        + 7
        + (
            home_attack
            - away_defence
        ) * 5
    )

    away_score = (
        50
        + (
            away_form_score
            - home_form_score
        ) * 25
        + (
            away_attack
            - home_defence
        ) * 5
    )

    draw_score = (
        100
        - abs(
            home_score
            - away_score
        )
    )

    draw_score = max(
        20,
        draw_score
    )

    total = (
        home_score
        + draw_score
        + away_score
    )

    home_probability = (
        home_score
        / total
    ) * 100

    draw_probability = (
        draw_score
        / total
    ) * 100

    away_probability = (
        away_score
        / total
    ) * 100

    # -----------------------------------------------------
    # GOL HESABI
    # -----------------------------------------------------

    expected_goals = (
        home_attack
        + away_attack
        + home_defence
        + away_defence
    ) / 2

    over25 = (
        35
        + expected_goals * 18
    )

    over25 = max(
        10,
        min(
            90,
            over25
        )
    )

    btts = (
        30
        + (
            home_attack
            + away_attack
        ) * 18
    )

    btts = max(
        10,
        min(
            90,
            btts
        )
    )

    # -----------------------------------------------------
    # TAHMİN
    # -----------------------------------------------------

    probabilities = {

        "Ev sahibi":
            home_probability,

        "Beraberlik":
            draw_probability,

        "Deplasman":
            away_probability
    }

    prediction = max(
        probabilities,
        key=probabilities.get
    )

    confidence = max(
        home_probability,
        draw_probability,
        away_probability
    )

    return {

        "prediction":
            prediction,

        "home_probability":
            round(
                home_probability,
                1
            ),

        "draw_probability":
            round(
                draw_probability,
                1
            ),

        "away_probability":
            round(
                away_probability,
                1
            ),

        "btts":
            round(
                btts,
                1
            ),

        "over25":
            round(
                over25,
                1
            ),

        "confidence":
            round(
                confidence,
                1
            ),

        "expected_goals":
            round(
                expected_goals,
                2
            )
    }


# =========================================================
# TEK MAÇ ANALİZİ
# =========================================================

@app.get("/api/analyze/{fixture_id}")
async def analyze(
    fixture_id: int
):

    data, error = await football_request(
        "fixtures",
        {
            "id": fixture_id,
            "timezone": "Europe/Istanbul"
        }
    )

    if error:

        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "error": "API-Football verisi alinamadi",
                "details": error,
                "fixture_id": fixture_id
            }
        )

    response = data.get(
        "response",
        []
    )

    if not response:

        return {
            "status": "not_found",
            "fixture_id": fixture_id,
            "message": "Mac bulunamadi."
        }

    match = response[0]

    teams = match.get(
        "teams",
        {}
    )

    league = match.get(
        "league",
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

    home_id = home.get(
        "id"
    )

    away_id = away.get(
        "id"
    )

    if not home_id or not away_id:

        return {
            "status": "error",
            "message": "Takim bilgileri bulunamadi."
        }

    home_recent = await get_recent_matches(
        home_id
    )

    away_recent = await get_recent_matches(
        away_id
    )

    home_form = calculate_form(
        home_recent,
        home_id
    )

    away_form = calculate_form(
        away_recent,
        away_id
    )

    prediction = calculate_prediction(
        home_form,
        away_form
    )

    if not prediction:

        return {
            "status": "insufficient_data",

            "fixture_id":
                fixture_id,

            "home":
                home.get("name"),

            "away":
                away.get("name"),

            "message":
                "Yeterli son mac verisi bulunamadi."
        }

    return {

        "status":
            "success",

        "fixture_id":
            fixture_id,

        "league":
            league.get("name"),

        "home":
            home.get("name"),

        "away":
            away.get("name"),

        "ai_status":
            "BetAI analiz hazir",

        "analysis":
            prediction,

        "home_form":
            home_form,

        "away_form":
            away_form
    }


# =========================================================
# TOP PICKS
# =========================================================

@app.get("/api/top-picks")
async def top_picks():

    today = datetime.now(
        TURKEY_TZ
    ).strftime("%Y-%m-%d")

    data, error = await football_request(
        "fixtures",
        {
            "date": today,
            "timezone": "Europe/Istanbul"
        }
    )

    if error:

        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "error": error,
                "date": today,
                "matches": []
            }
        )

    fixtures = data.get(
        "response",
        []
    )

    picks = []

    for match in fixtures:

        status = match.get(
            "fixture",
            {}
        ).get(
            "status",
            {}
        ).get(
            "short"
        )

        # Sadece başlamamış maçlar
        if status != "NS":
            continue

        fixture = match.get(
            "fixture",
            {}
        )

        teams = match.get(
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

        home_id = home.get(
            "id"
        )

        away_id = away.get(
            "id"
        )

        if not home_id or not away_id:
            continue

        home_recent = await get_recent_matches(
            home_id
        )

        away_recent = await get_recent_matches(
            away_id
        )

        home_form = calculate_form(
            home_recent,
            home_id
        )

        away_form = calculate_form(
            away_recent,
            away_id
        )

        prediction = calculate_prediction(
            home_form,
            away_form
        )

        if not prediction:
            continue

        if prediction["confidence"] < 55:
            continue

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

        picks.append({

            "fixture_id":
                fixture.get("id"),

            "league":
                match.get(
                    "league",
                    {}
                ).get(
                    "name",
                    "Bilinmiyor"
                ),

            "time":
                match_time,

            "home":
                home.get(
                    "name"
                ),

            "away":
                away.get(
                    "name"
                ),

            "prediction":
                prediction[
                    "prediction"
                ],

            "home_probability":
                prediction[
                    "home_probability"
                ],

            "draw_probability":
                prediction[
                    "draw_probability"
                ],

            "away_probability":
                prediction[
                    "away_probability"
                ],

            "btts":
                prediction[
                    "btts"
                ],

            "over25":
                prediction[
                    "over25"
                ],

            "confidence":
                prediction[
                    "confidence"
                ],

            "expected_goals":
                prediction[
                    "expected_goals"
                ],

            "ai_status":
                "BetAI analiz hazir"
        })

    picks.sort(
        key=lambda item:
            item["confidence"],
        reverse=True
    )

    return {

        "status":
            "success",

        "date":
            today,

        "count":
            len(picks),

        "matches":
            picks[:10]
    }
