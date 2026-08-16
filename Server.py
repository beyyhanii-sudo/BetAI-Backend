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
    version="1.0.0"
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

API_URL = "https://v3.football.api-sports.io/fixtures"


# Türkiye saati
TURKEY_TZ = ZoneInfo("Europe/Istanbul")


# =========================================================
# ANA SAYFA
# =========================================================

@app.get("/")
async def home():

    return JSONResponse(
        content={
            "status": "online",
            "app": "BetAI",
            "message": "BetAI Backend calisiyor!"
        }
    )


# =========================================================
# SAĞLIK KONTROLÜ
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

    # API anahtarı kontrolü
    if not API_KEY:

        return JSONResponse(
            status_code=500,
            content={
                "error": "API_FOOTBALL_KEY bulunamadi",
                "matches": []
            }
        )


    # Türkiye tarihini kullan
    today = datetime.now(
        TURKEY_TZ
    ).strftime("%Y-%m-%d")


    # API-Football header
    headers = {
        "x-apisports-key": API_KEY
    }


    # API parametreleri
    params = {
        "date": today
    }


    try:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.get(
                API_URL,
                headers=headers,
                params=params
            )


        # API hata kontrolü
        if response.status_code != 200:

            return JSONResponse(
                status_code=502,
                content={
                    "error": "API-Football hata verdi",
                    "api_status": response.status_code,
                    "matches": []
                }
            )


        data = response.json()


        # API response
        api_matches = data.get(
            "response",
            []
        )


        result = []


        # =================================================
        # MAÇLARI İŞLE
        # =================================================

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


            # -----------------------------
            # Takımlar
            # -----------------------------

            home_team = teams.get(
                "home",
                {}
            )

            away_team = teams.get(
                "away",
                {}
            )


            home_name = home_team.get(
                "name",
                "Bilinmiyor"
            )

            away_name = away_team.get(
                "name",
                "Bilinmiyor"
            )


            # -----------------------------
            # Lig
            # -----------------------------

            league_name = league.get(
                "name",
                "Bilinmiyor"
            )


            # -----------------------------
            # Saat
            # -----------------------------

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


            # =================================================
            # MAÇ VERİSİ
            # =================================================

            result.append({

                "fixture_id":
                    fixture.get("id"),

                "league":
                    league_name,

                "time":
                    match_time,

                "home":
                    home_name,

                "away":
                    away_name,

                "status":
                    fixture.get(
                        "status",
                        {}
                    ).get(
                        "short",
                        ""
                    ),

                # -----------------------------------------
                # Şimdilik tahmin alanları
                # -----------------------------------------

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


        # =================================================
        # JSON CEVABI
        # =================================================

        return JSONResponse(
            content={
                "status": "success",
                "date": today,
                "count": len(result),
                "matches": result
            }
        )


    # =====================================================
    # HATA
    # =====================================================

    except Exception as error:

        return JSONResponse(
            status_code=500,
            content={
                "error": str(error),
                "matches": []
            }
        )
