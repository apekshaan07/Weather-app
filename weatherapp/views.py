from django.shortcuts import render
from django.contrib import messages
import requests, urllib.parse
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_KEY  = os.getenv("OPENWEATHER_KEY")
GOOGLE_KEY       = os.getenv("GOOGLE_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

DEFAULT_BG = "https://images.pexels.com/photos/3008509/pexels-photo-3008509.jpeg?auto=compress&cs=tinysrgb&w=1600"

def to_local(ts: int, tz_offset_seconds: int) -> datetime:
    return datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc) + timedelta(seconds=tz_offset_seconds)

def get_city_image(city: str) -> str:
    # If keys missing, just return default
    if not GOOGLE_KEY or not SEARCH_ENGINE_ID:
        return DEFAULT_BG
    try:
        q = urllib.parse.quote_plus(f"{city} skyline 1920x1080")
        url = (
            "https://www.googleapis.com/customsearch/v1"
            f"?key={GOOGLE_KEY}&cx={SEARCH_ENGINE_ID}"
            f"&q={q}&searchType=image&imgSize=xlarge&num=5"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        items = r.json().get("items") or []
        for it in items:
            link = it.get("link")
            if link:
                return link
    except requests.RequestException:
        pass
    return DEFAULT_BG

def home(request):
    ctx = {
        "description": "",
        "icon": "",
        "temp": "",
        "day": "",
        "city": "Salt Lake City",
        "image_url": DEFAULT_BG,
        "exception_occurred": False,
        "local_time": "--:--",
        "sunrise": "--:--",
        "sunset":  "--:--",
    }

    if request.method == "POST":
        city = (request.POST.get("city") or "").strip()
        ctx["city"] = city or ctx["city"]

        try:
            if not OPENWEATHER_KEY:
                raise RuntimeError("Missing OPENWEATHER_KEY")

            weather_url = "https://api.openweathermap.org/data/2.5/weather"
            res = requests.get(
                weather_url,
                params={"q": ctx["city"], "appid": OPENWEATHER_KEY, "units": "metric"},
                timeout=8
            )
            data = res.json()

            if res.status_code != 200 or "main" not in data:
                raise ValueError("City not found")

            ctx["description"] = (data["weather"][0].get("description","")).capitalize()
            ctx["icon"] = data["weather"][0].get("icon","01d")
            ctx["temp"] = round(float(data["main"].get("temp", 0.0)), 1)

            tz_offset = int(data.get("timezone", 0))  # seconds
            obs_dt = int(data.get("dt", datetime.now(timezone.utc).timestamp()))
            obs_local = to_local(obs_dt, tz_offset)
            ctx["local_time"] = obs_local.strftime("%I:%M %p")
            ctx["day"] = obs_local.strftime("%b %d, %Y")

            sr = int(data.get("sys", {}).get("sunrise", obs_dt))
            ss = int(data.get("sys", {}).get("sunset",  obs_dt))
            ctx["sunrise"] = to_local(sr, tz_offset).strftime("%I:%M %p")
            ctx["sunset"]  = to_local(ss, tz_offset).strftime("%I:%M %p")

            ctx["image_url"] = get_city_image(ctx["city"])

        except Exception:
            ctx["exception_occurred"] = True
            messages.error(request, "City information is not available")
            now = datetime.now(timezone.utc)
            ctx.update({
                "description": "Clear sky",
                "icon": "01d",
                "temp": 25,
                "city": "Salt Lake City",
                "image_url": DEFAULT_BG,
                "local_time": now.strftime("%I:%M %p"),
                "day": now.strftime("%b %d, %Y"),
                "sunrise": "--:--",
                "sunset":  "--:--",
            })

    return render(request, "index.html", ctx)
