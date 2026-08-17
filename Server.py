 from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
import math


# =========================================================
# BetAI
# =========================================================

app = FastAPI(
    title="BetAI Backend",
    version="2.0.0"
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
# API İSTEĞİ
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
            return None, f"API HTTP {response.status_code}"

        data = response.json()

        if data.get("errors"):
            return None, str(data["errors"])

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
        "version": "2.0.0",
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

    fixtures = data.get(
        "response",
        []
    )

    result = []

    for match in fixtures:

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
# TAKIM İSTATİSTİKLERİ
# =========================================================

async def get_team_statistics(
    team_id,
    league_id,
    season
):

    data, error = await football_request(
        "teams/statistics",
        {
            "team": team_id,
            "league": league_id,
            "season": season
        }
    )

    if error:
        return None

    if not data:
        return None

    response = data.get(
        "response"
    )

    if not response:
        return None

    return response


# =========================================================
# SON MAÇLAR
# =========================================================

async def get_recent_matches(
    team_id
):

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
# TAKIM FORM HESABI
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
            "points": 0,
            "goals_for": 0,
            "goals_against": 0,
            "games": 0,
            "form": 0
        }

    form = (
        points / (games * 3)
    ) * 100

    return {

        "points":
            points,

        "goals_for":
            goals_for,

        "goals_against":
            goals_against,

        "games":
            games,

        "form":
            round(form, 2)
    }


# =========================================================
# BETAI ANALİZ MOTORU
# =========================================================

def calculate_prediction(
    home_form,
    away_form
):

    home_games = home_form["games"]
    away_games = away_form["games"]

    if (
        home_games == 0
        or away_games == 0
    ):

        return None

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

    home_strength = (
        home_form["form"]
        / 100
    )

    away_strength = (
        away_form["form"]
        / 100
    )

    # Ev sahibi avantajı
    home_score = (
        50
        + (
            home_strength
            - away_strength
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
            away_strength
            - home_strength
        ) * 25
        + (
            away_attack
            - home_defence
        ) * 5
    )

    draw_score = 100 - abs(
        home_score - away_score
    )

    if draw_score < 20:
        draw_score = 20

    total = (
        home_score
        + away_score
        + draw_score
    )

    home_probability = (
        home_score / total
    ) * 100

    draw_probability = (
        draw_score / total
    ) * 100

    away_probability = (
        away_score / total
    ) * 100

    # Gol tahmini
    expected_goals = (
        home_attack
        + away_attack
        + home_defence
        + away_defence
    ) / 2

    over25 = min(
        90,
        max(
            10,
            35 + expected_goals * 18
        )
    )

    btts = min(
        90,
        max(
            10,
            30
            + (
                home_attack
                + away_attack
            ) * 18
        )
    )

    probabilities = {

        "home":
            home_probability,

        "draw":
            draw_probability,

        "away":
            away_probability
    }

    best_result = max(
        probabilities,
        key=probabilities.get
    )

    if best_result == "home":

        advice = "Ev sahibi kazanir"

    elif best_result == "away":

        advice = "Deplasman kazanir"

    else:

        advice = "Beraberlik"

    confidence = max(
        home_probability,
        draw_probability,
        away_probability
    )

    return {

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

        "prediction":
            advice,

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
            "id": fixture_id
        }
    )

    if error:

        return JSONResponse(
            status_code=502,
            content={
                "error":
                    "API-Football verisi alinamadi",

                "details":
                    error,

                "fixture_id":
                    fixture_id
            }
        )

    response = data.get(
        "response",
        []
    )

    if not response:

        return {
            "status":
                "not_found",

            "fixture_id":
                fixture_id,

            "message":
                "Mac bulunamadi."
        }

    match = response[0]

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

    home_id = home.get(
        "id"
    )

    away_id = away.get(
        "id"
    )

    league_id = league.get(
        "id"
    )

    season = league.get(
        "season"
    )

    if not home_id or not away_id:

        return {
            "status":
                "error",

            "message":
                "Takim bilgileri bulunamadi."
        }

    # Son 5 maç
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
            "status":
                "insufficient_data",

            "fixture_id":
                fixture_id,

            "home":
                home.get("name"),

            "away":
                away.get("name"),

            "message":
                "Yeterli veri bulunamadi."
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

        "analysis":
            prediction,

        "home_form":
            home_form,

        "away_form":
            away_form,

        "ai_status":
            "BetAI analiz hazir"
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

    fixtures = data.get(
        "response",
        []
    )

    picks = []

    # API limitlerini korumak için
    # sadece oynanmamış maçları değerlendir.
    upcoming = []

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

        if status == "NS":

            upcoming.append(match)

    # En fazla 15 maç analiz edilir.
    for match in upcoming[:15]:

        fixture_id = match.get(
            "fixture",
            {}
        ).get(
            "id"
        )

        if not fixture_id:
            continue

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

        # Sadece %55 ve üzeri güven
        # gösterilecek.
        if prediction["confidence"] < 55:
            continue

        fixture = match.get(
            "fixture",
            {}
        )

        timestamp = fixture.get(
            "timestamp"
        )

        if timestamp:

            time = datetime.fromtimestamp(
                timestamp,
                TURKEY_TZ
            ).strftime("%H:%M")

        else:

            time = "--:--"

        picks.append({

            "fixture_id":
                fixture_id,

            "league":
                match.get(
                    "league",
                    {}
                ).get(
                    "name"
                ),

            "time":
                time,

            "home":
                home.get(
                    "name"
                ),

            "away":
                away.get(
                    "name"
                ),

            "prediction":
                prediction["prediction"],

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
                prediction["btts"],

            "over25":
                prediction["over25"],

            "confidence":
                prediction["confidence"],

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
