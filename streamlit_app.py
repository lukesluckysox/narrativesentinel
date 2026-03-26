import random
import textwrap
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# -----------------------
# CONFIG
# -----------------------

st.set_page_config(
    page_title="World Narrative Compass",
    layout="wide",
    page_icon="🌍",
)

# -----------------------
# API KEY MANAGEMENT
# -----------------------
# Supports multiple news APIs. Add any/all keys to .streamlit/secrets.toml:
#   NEWSAPI_KEY = "..."          # newsapi.org (free: 100 req/day, dev only)
#   NEWSDATA_KEY = "..."         # newsdata.io (free: 200 req/day)
#   GUARDIAN_KEY = "..."         # open-platform.theguardian.com (free: 500 req/day)
#   CURRENTS_KEY = "..."         # currentsapi.services (free: 600 req/day)

NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "") or st.secrets.get("NEWS_API_KEY", "")
NEWSDATA_KEY = st.secrets.get("NEWSDATA_KEY", "")
GUARDIAN_KEY = st.secrets.get("GUARDIAN_KEY", "")
CURRENTS_KEY = st.secrets.get("CURRENTS_KEY", "")

# -----------------------
# SAMPLE DATA & HELPERS
# -----------------------

SAMPLE_QUOTES = [
    "In the midst of chaos, there is also opportunity.",
    "You do not respond to the world; you create the world you respond to.",
    "Between stimulus and response there is a space. In that space is our power to choose.",
]

# Full country list with region, lat/lon, and ISO alpha-3 for the choropleth
COUNTRIES = [
    # North America
    {"name": "United States", "region": "North America", "lat": 38.0, "lon": -97.0, "iso": "USA"},
    {"name": "Canada", "region": "North America", "lat": 56.0, "lon": -106.0, "iso": "CAN"},
    {"name": "Mexico", "region": "North America", "lat": 23.6, "lon": -102.5, "iso": "MEX"},
    # South America
    {"name": "Brazil", "region": "South America", "lat": -14.0, "lon": -51.0, "iso": "BRA"},
    {"name": "Argentina", "region": "South America", "lat": -38.4, "lon": -63.6, "iso": "ARG"},
    {"name": "Colombia", "region": "South America", "lat": 4.6, "lon": -74.1, "iso": "COL"},
    # Europe
    {"name": "Germany", "region": "Europe", "lat": 51.0, "lon": 9.0, "iso": "DEU"},
    {"name": "United Kingdom", "region": "Europe", "lat": 55.4, "lon": -3.4, "iso": "GBR"},
    {"name": "France", "region": "Europe", "lat": 46.6, "lon": 1.9, "iso": "FRA"},
    {"name": "Italy", "region": "Europe", "lat": 41.9, "lon": 12.6, "iso": "ITA"},
    {"name": "Spain", "region": "Europe", "lat": 40.5, "lon": -3.7, "iso": "ESP"},
    {"name": "Ukraine", "region": "Europe", "lat": 48.4, "lon": 31.2, "iso": "UKR"},
    {"name": "Poland", "region": "Europe", "lat": 51.9, "lon": 19.1, "iso": "POL"},
    # Africa
    {"name": "Egypt", "region": "Africa", "lat": 26.8, "lon": 30.8, "iso": "EGY"},
    {"name": "Nigeria", "region": "Africa", "lat": 9.1, "lon": 8.7, "iso": "NGA"},
    {"name": "South Africa", "region": "Africa", "lat": -30.6, "lon": 22.9, "iso": "ZAF"},
    {"name": "Kenya", "region": "Africa", "lat": -0.02, "lon": 37.9, "iso": "KEN"},
    # Asia
    {"name": "China", "region": "Asia", "lat": 35.9, "lon": 104.2, "iso": "CHN"},
    {"name": "India", "region": "Asia", "lat": 20.6, "lon": 78.9, "iso": "IND"},
    {"name": "Japan", "region": "Asia", "lat": 36.2, "lon": 138.3, "iso": "JPN"},
    {"name": "South Korea", "region": "Asia", "lat": 35.9, "lon": 127.8, "iso": "KOR"},
    {"name": "Israel", "region": "Asia", "lat": 31.0, "lon": 34.9, "iso": "ISR"},
    {"name": "Saudi Arabia", "region": "Asia", "lat": 23.9, "lon": 45.1, "iso": "SAU"},
    {"name": "Turkey", "region": "Asia", "lat": 39.0, "lon": 35.2, "iso": "TUR"},
    {"name": "Indonesia", "region": "Asia", "lat": -0.8, "lon": 113.9, "iso": "IDN"},
    # Oceania
    {"name": "Australia", "region": "Oceania", "lat": -25.3, "lon": 133.8, "iso": "AUS"},
    {"name": "New Zealand", "region": "Oceania", "lat": -40.9, "lon": 174.9, "iso": "NZL"},
]

ALL_COUNTRY_NAMES = sorted([c["name"] for c in COUNTRIES])

REGIONS = ["Global", "North America", "South America", "Europe", "Africa", "Asia", "Oceania"]

# Map zoom/center per region (for Plotly geo scope or fitbounds)
REGION_GEO = {
    "Global":        {"scope": "world",          "center": {"lat": 20, "lon": 0},    "projection_scale": 1},
    "North America": {"scope": "north america",  "center": {"lat": 40, "lon": -100}, "projection_scale": 1},
    "South America": {"scope": "south america",  "center": {"lat": -15, "lon": -60}, "projection_scale": 1},
    "Europe":        {"scope": "europe",          "center": {"lat": 54, "lon": 15},   "projection_scale": 1},
    "Africa":        {"scope": "africa",          "center": {"lat": 5, "lon": 20},    "projection_scale": 1},
    "Asia":          {"scope": "asia",            "center": {"lat": 30, "lon": 90},   "projection_scale": 1},
    "Oceania":       {"scope": "world",           "center": {"lat": -25, "lon": 145}, "projection_scale": 3},
}

# ISO-2 codes for each country (used by NewsAPI / NewsData top-headlines)
COUNTRY_ISO2 = {
    "United States": "us", "Canada": "ca", "Mexico": "mx",
    "Brazil": "br", "Argentina": "ar", "Colombia": "co",
    "Germany": "de", "United Kingdom": "gb", "France": "fr",
    "Italy": "it", "Spain": "es", "Ukraine": "ua", "Poland": "pl",
    "Egypt": "eg", "Nigeria": "ng", "South Africa": "za", "Kenya": "ke",
    "China": "cn", "India": "in", "Japan": "jp", "South Korea": "kr",
    "Israel": "il", "Saudi Arabia": "sa", "Turkey": "tr", "Indonesia": "id",
    "Australia": "au", "New Zealand": "nz",
}

# Build region → list of ISO-2 codes
REGION_ISO2_CODES = {}
for _c in COUNTRIES:
    _rgn = _c["region"]
    _code = COUNTRY_ISO2.get(_c["name"])
    if _code:
        REGION_ISO2_CODES.setdefault(_rgn, []).append(_code)

# Guardian section mapping for regions
REGION_TO_GUARDIAN_SECTION = {
    "North America": "us-news", "Europe": "world", "Asia": "world",
    "Africa": "world", "South America": "world", "Oceania": "australia-news",
}


def compute_global_stress(region: str, seed: int) -> int:
    rng = random.Random(seed + hash(region))
    base = rng.randint(40, 70)
    return base + 10 if region == "Global" else base


# -----------------------
# NEWS FETCHING — MULTI-API
# -----------------------

def _resolve_country_codes(region: str, country_name: Optional[str]) -> list:
    """
    Return a list of (iso2_code, display_name) pairs to query.
    - Specific country → just that country.
    - Region selected  → all countries in that region.
    - Global           → one representative per region for breadth.
    """
    if country_name:
        code = COUNTRY_ISO2.get(country_name)
        return [(code, country_name)] if code else [(None, country_name)]

    if region != "Global" and region in REGION_ISO2_CODES:
        return [
            (COUNTRY_ISO2[c["name"]], c["name"])
            for c in COUNTRIES if c["region"] == region and c["name"] in COUNTRY_ISO2
        ]

    # Global: pick one representative per region
    reps = {"us": "United States", "br": "Brazil", "gb": "United Kingdom",
            "ng": "Nigeria", "in": "India", "au": "Australia"}
    return list(reps.items())


def _newsapi_one(code: str, country_label: str, region: str) -> list:
    """Fetch top-headlines for a single country code from NewsAPI."""
    headers = {"X-Api-Key": NEWSAPI_KEY}
    params = {"pageSize": 5}              # fewer per country so totals stay reasonable
    if code:
        params["country"] = code
    else:
        # fallback: keyword search
        params["q"] = country_label
        params["language"] = "en"
    try:
        r = requests.get("https://newsapi.org/v2/top-headlines",
                         params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    if data.get("status") != "ok":
        return []
    return [
        {
            "title": a.get("title") or "Untitled",
            "region": region,
            "country": country_label,
            "description": a.get("description") or "",
            "source_name": (a.get("source") or {}).get("name") or "Unknown",
            "url": a.get("url") or "",
            "api": "NewsAPI",
        }
        for a in data.get("articles", [])
    ]


def _newsdata_one(code: str, country_label: str, region: str) -> list:
    """Fetch latest news for a single country from NewsData."""
    params = {"apikey": NEWSDATA_KEY, "language": "en", "size": 5}
    if code:
        params["country"] = code
    else:
        params["q"] = country_label
    try:
        r = requests.get("https://newsdata.io/api/1/latest", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    if data.get("status") != "success":
        return []
    return [
        {
            "title": a.get("title") or "Untitled",
            "region": region,
            "country": country_label,
            "description": a.get("description") or "",
            "source_name": a.get("source_name") or a.get("source_id") or "Unknown",
            "url": a.get("link") or "",
            "api": "NewsData",
        }
        for a in data.get("results", [])
    ]


def _fetch_guardian(region: str, country_name: Optional[str]) -> list:
    """Guardian uses keyword/section search — one call covers a region."""
    if not GUARDIAN_KEY:
        return []
    params = {"api-key": GUARDIAN_KEY, "page-size": 10,
              "show-fields": "trailText", "order-by": "newest"}
    if country_name:
        params["q"] = country_name
    elif region in REGION_TO_GUARDIAN_SECTION:
        params["section"] = REGION_TO_GUARDIAN_SECTION[region]
        # Add the region name as a keyword to improve relevance
        if region not in ("Global",):
            params["q"] = region
    try:
        r = requests.get("https://content.guardianapis.com/search",
                         params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    return [
        {
            "title": a.get("webTitle") or "Untitled",
            "region": region,
            "country": country_name or region,
            "description": (a.get("fields") or {}).get("trailText") or "",
            "source_name": "The Guardian",
            "url": a.get("webUrl") or "",
            "api": "Guardian",
        }
        for a in data.get("response", {}).get("results", [])
    ]


def _fetch_currents(region: str, country_name: Optional[str]) -> list:
    """Currents uses keyword search — one call covers a region."""
    if not CURRENTS_KEY:
        return []
    params = {"apiKey": CURRENTS_KEY, "language": "en", "page_size": 10}
    if country_name:
        params["keywords"] = country_name
    elif region != "Global":
        params["keywords"] = region
    try:
        r = requests.get("https://api.currentsapi.services/v1/latest-news",
                         params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []
    if data.get("status") != "ok":
        return []
    return [
        {
            "title": a.get("title") or "Untitled",
            "region": region,
            "country": country_name or region,
            "description": a.get("description") or "",
            "source_name": a.get("author") or "Unknown",
            "url": a.get("url") or "",
            "api": "Currents",
        }
        for a in data.get("news", [])
    ]


@st.cache_data(show_spinner="Fetching headlines\u2026", ttl=timedelta(minutes=15))
def fetch_news(region: str, country_name: Optional[str] = None):
    """
    Fetch news tied to the selected region/country.
    For country-code APIs (NewsAPI, NewsData), queries each country in the
    region individually so results actually span the whole region.
    For keyword APIs (Guardian, Currents), uses region name as search term.
    """
    all_events = []
    targets = _resolve_country_codes(region, country_name)

    # Country-code APIs: query per country in the region
    if NEWSAPI_KEY:
        for code, label in targets:
            all_events.extend(_newsapi_one(code, label, region))

    if NEWSDATA_KEY:
        for code, label in targets:
            all_events.extend(_newsdata_one(code, label, region))

    # Keyword-based APIs: one call with region/country name
    all_events.extend(_fetch_guardian(region, country_name))
    all_events.extend(_fetch_currents(region, country_name))

    # Deduplicate by title
    seen = set()
    unique = []
    for ev in all_events:
        key = ev["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    if not unique:
        configured = sum(bool(k) for k in [NEWSAPI_KEY, NEWSDATA_KEY, GUARDIAN_KEY, CURRENTS_KEY])
        if configured == 0:
            return [], "No API keys configured"
        return [], None
    return unique, None


# -----------------------
# INTERACTIVE WORLD MAP
# -----------------------

def build_world_map(selected_region: str, selected_country: str):
    """
    Plotly choropleth + scatter: no Mapbox token needed.
    Highlights countries in the selected region; marks country points.
    """
    df = pd.DataFrame(COUNTRIES)

    # Assign a numeric value for coloring by region membership
    if selected_region == "Global":
        df["highlight"] = 1
    else:
        df["highlight"] = df["region"].apply(lambda r: 2 if r == selected_region else 0.5)

    if selected_country and selected_country != "All":
        df["highlight"] = df["name"].apply(lambda n: 3 if n == selected_country else 0.3)

    # Choropleth for shading
    fig = go.Figure()

    fig.add_trace(go.Choropleth(
        locations=df["iso"],
        z=df["highlight"],
        text=df["name"],
        hoverinfo="text",
        colorscale=[
            [0, "rgba(30,30,50,0.3)"],
            [0.33, "rgba(60,60,100,0.4)"],
            [0.66, "rgba(76,111,255,0.5)"],
            [1, "rgba(76,111,255,0.8)"],
        ],
        showscale=False,
        marker_line_color="rgba(100,100,140,0.4)",
        marker_line_width=0.5,
    ))

    # Scatter dots for each country
    fig.add_trace(go.Scattergeo(
        lat=df["lat"],
        lon=df["lon"],
        text=df["name"],
        hoverinfo="text",
        mode="markers",
        marker=dict(
            size=8,
            color="#4C6FFF",
            line=dict(width=1, color="white"),
        ),
    ))

    geo_cfg = REGION_GEO.get(selected_region, REGION_GEO["Global"])

    fig.update_geos(
        scope=geo_cfg["scope"],
        showframe=False,
        showcoastlines=True,
        coastlinecolor="rgba(100,100,140,0.5)",
        showland=True,
        landcolor="#0F172A",
        showocean=True,
        oceancolor="#020617",
        showlakes=False,
        showcountries=True,
        countrycolor="rgba(100,100,140,0.3)",
        projection_type="natural earth",
    )

    # For Oceania, use center + scale since scope="world"
    if selected_region == "Oceania":
        fig.update_geos(
            center=geo_cfg["center"],
            projection_scale=geo_cfg["projection_scale"],
        )

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#020617",
        geo_bgcolor="#020617",
        font=dict(color="#E5E7EB"),
    )

    return fig


# -----------------------
# POLITICAL COMPASS
# -----------------------

def interpret_political_compass(x: int, y: int) -> str:
    if x <= -2 and y <= -2:
        quadrant = "left-libertarian"
    elif x <= -2 and y >= 2:
        quadrant = "left-authoritarian"
    elif x >= 2 and y <= -2:
        quadrant = "right-libertarian"
    elif x >= 2 and y >= 2:
        quadrant = "right-authoritarian"
    else:
        quadrant = "centrist / mixed"

    advice_map = {
        "left-libertarian": (
            "Emphasize grassroots solutions, mutual aid, and bottom-up reforms. "
            "Look for stories about community resilience and democratic participation, "
            "and ask how power can be redistributed closer to ordinary people."
        ),
        "left-authoritarian": (
            "Focus on systemic reforms and strong institutions that can correct injustice. "
            "Look for policies that protect vulnerable groups, and evaluate whether current "
            "leaders are using power to reduce inequality and harm."
        ),
        "right-libertarian": (
            "Pay attention to how current events affect individual choice, markets, "
            "and personal responsibility. Favor decentralized solutions, and ask where "
            "regulations may be doing more harm than good."
        ),
        "right-authoritarian": (
            "Prioritize order, security, and institutional stability. "
            "Look for narratives about cohesion, adherence to rules, and national interest, "
            "and question whether chaos or fragmentation is being amplified."
        ),
        "centrist / mixed": (
            "Balance competing values instead of choosing a single lens. "
            "Seek multiple credible sources, compare narratives, and look for pragmatic steps "
            "that reduce harm without amplifying polarization."
        ),
    }

    advice = advice_map[quadrant]
    header = f"From a {quadrant} perspective:"
    wrapped = textwrap.fill(advice, width=80)
    return f"{header}\n\n{wrapped}"


def political_compass_plot(x, y):
    fig = go.Figure()

    fig.add_shape(type="rect", x0=-10, x1=0, y0=0, y1=10,
                  fillcolor="rgba(220,50,50,0.08)", line_width=0)
    fig.add_shape(type="rect", x0=0, x1=10, y0=0, y1=10,
                  fillcolor="rgba(50,50,220,0.08)", line_width=0)
    fig.add_shape(type="rect", x0=-10, x1=0, y0=-10, y1=0,
                  fillcolor="rgba(50,180,50,0.08)", line_width=0)
    fig.add_shape(type="rect", x0=0, x1=10, y0=-10, y1=0,
                  fillcolor="rgba(180,130,50,0.08)", line_width=0)

    fig.add_shape(type="line", x0=-10, x1=10, y0=0, y1=0,
                  line=dict(color="gray", width=1))
    fig.add_shape(type="line", x0=0, x1=0, y0=-10, y1=10,
                  line=dict(color="gray", width=1))

    fig.add_trace(go.Scatter(
        x=[x], y=[y],
        mode="markers+text",
        marker=dict(size=16, color="#4C6FFF"),
        text=["You"], textposition="top center",
        textfont=dict(color="#E5E7EB", size=12),
        name="You",
    ))

    fig.update_layout(
        xaxis=dict(range=[-10, 10], zeroline=False,
                    title="Economic: Left (\u221210) \u2194 Right (10)"),
        yaxis=dict(range=[-10, 10], zeroline=False,
                    title="Authority: Libertarian (\u221210) \u2194 Authoritarian (10)"),
        height=350,
        margin=dict(l=40, r=40, t=30, b=40),
        plot_bgcolor="#020617",
        paper_bgcolor="#020617",
        font=dict(color="#E5E7EB"),
        showlegend=False,
    )
    return fig


# -----------------------
# SESSION STATE DEFAULTS
# -----------------------

if "selected_region" not in st.session_state:
    st.session_state.selected_region = "Global"
if "selected_country" not in st.session_state:
    st.session_state.selected_country = "All"


def set_region(r: str):
    st.session_state.selected_region = r
    st.session_state.selected_country = "All"


def set_country_from_search():
    val = st.session_state.get("country_search_box", "")
    if val and val in ALL_COUNTRY_NAMES:
        st.session_state.selected_country = val
        # Also set the region to match
        for c in COUNTRIES:
            if c["name"] == val:
                st.session_state.selected_region = c["region"]
                break


# -----------------------
# SIDEBAR — Region boxes + Country search
# -----------------------

with st.sidebar:
    st.header("Regions")

    # Clickable region buttons laid out as a grid
    # Use 2 columns of buttons
    region_pairs = [REGIONS[i:i+2] for i in range(0, len(REGIONS), 2)]
    for pair in region_pairs:
        cols = st.columns(len(pair))
        for col, rgn in zip(cols, pair):
            with col:
                is_active = st.session_state.selected_region == rgn
                label = f"{'● ' if is_active else ''}{rgn}"
                st.button(
                    label,
                    key=f"sidebar_region_{rgn}",
                    on_click=set_region,
                    args=(rgn,),
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                )

    st.markdown("---")

    # Country search bar
    st.subheader("Country search")
    region_countries = [c["name"] for c in COUNTRIES
                        if st.session_state.selected_region == "Global"
                        or c["region"] == st.session_state.selected_region]
    country_options = sorted(region_countries)

    st.selectbox(
        "Search for a country",
        options=["All"] + country_options,
        index=0 if st.session_state.selected_country == "All"
              else (["All"] + country_options).index(st.session_state.selected_country)
                   if st.session_state.selected_country in country_options else 0,
        key="country_select_box",
        on_change=lambda: st.session_state.update(
            selected_country=st.session_state.country_select_box
        ),
    )

    # Also provide a free-text search that works across all countries
    st.text_input(
        "Or type any country name",
        key="country_search_box",
        on_change=set_country_from_search,
        placeholder="e.g. Japan, Nigeria...",
    )

    # Show which APIs are active
    st.markdown("---")
    st.subheader("News sources")
    apis = {
        "NewsAPI.org": bool(NEWSAPI_KEY),
        "NewsData.io": bool(NEWSDATA_KEY),
        "The Guardian": bool(GUARDIAN_KEY),
        "Currents API": bool(CURRENTS_KEY),
    }
    for name, active in apis.items():
        icon = "\U0001f7e2" if active else "\u26aa"
        st.caption(f"{icon} {name}")
    if not any(apis.values()):
        st.info("Add at least one API key to .streamlit/secrets.toml")


# Read current selections
region = st.session_state.selected_region
country = st.session_state.selected_country

# -----------------------
# LAYOUT
# -----------------------

day_seed = date.today().toordinal()
random.seed(day_seed)

left_col, right_col = st.columns([3, 4])

# LEFT: Quote + Stress + Map
with left_col:
    quote = random.choice(SAMPLE_QUOTES)
    st.markdown("### Quote of the day")
    st.info(f"\u201c{quote}\u201d")

    st.markdown("### Global stress meter")
    stress = compute_global_stress(region, day_seed)
    st.progress(stress / 100.0)
    st.caption(f"Estimated stress level for {region}: {stress}/100")

    st.markdown("### World map")
    st.plotly_chart(
        build_world_map(region, country),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # Clickable region buttons below the map too
    st.caption("Jump to region:")
    map_cols = st.columns(len(REGIONS))
    for col, rgn in zip(map_cols, REGIONS):
        with col:
            is_active = region == rgn
            st.button(
                rgn,
                key=f"map_region_{rgn}",
                on_click=set_region,
                args=(rgn,),
                use_container_width=True,
                type="primary" if is_active else "secondary",
            )

# RIGHT: Compass + Narratives
with right_col:
    st.markdown("### Political compass")
    st.plotly_chart(
        political_compass_plot(
            st.session_state.get("x_axis", 0),
            st.session_state.get("y_axis", 0),
        ),
        use_container_width=True,
    )

    slider_left, slider_right = st.columns(2)
    with slider_left:
        x_axis = st.slider("Economic (Left \u221210 \u2194 Right 10)", -10, 10, 0, key="x_axis")
    with slider_right:
        y_axis = st.slider("Authority (Libertarian \u221210 \u2194 Authoritarian 10)", -10, 10, 0, key="y_axis")

    st.markdown("#### How you should deal with today's events")
    advice_text = interpret_political_compass(x_axis, y_axis)
    st.markdown(advice_text)

    selected_country_name = None
    if country and country != "All":
        selected_country_name = country

    # Dynamic heading tied to what's selected
    if selected_country_name:
        st.markdown(f"### Narratives: {selected_country_name}")
    elif region != "Global":
        st.markdown(f"### Narratives: {region}")
    else:
        st.markdown("### Narratives: Global")

    events, error = fetch_news(region, selected_country_name)

    if error:
        st.warning(error)
        st.info(
            "Add API keys to .streamlit/secrets.toml to enable live events. "
            "See README for supported providers."
        )
    elif not events:
        st.warning("No events found yet for this selection.")
    else:
        for ev in events:
            with st.expander(ev["title"]):
                st.markdown(ev["description"])
                if ev["url"]:
                    st.markdown(f"[Read full article]({ev['url']})")
                st.caption(
                    f"{ev['source_name']} \u00b7 {ev['region']} / {ev['country']} \u00b7 via {ev['api']}"
                )

st.markdown("---")
st.caption(
    "Prototype: World Narrative Compass. Replace news APIs with your own world-events "
    "summarizer, add LLM-generated frames, and refine the compass logic."
)
