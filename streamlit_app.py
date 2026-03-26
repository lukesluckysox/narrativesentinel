import random
import textwrap
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st
import plotly.graph_objects as go

# -----------------------
# CONFIG
# -----------------------

st.set_page_config(
    page_title="World Narrative Compass",
    layout="wide",
    page_icon="🌍",
)

NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", "")

# -----------------------
# SAMPLE DATA & HELPERS
# -----------------------

SAMPLE_QUOTES = [
    "In the midst of chaos, there is also opportunity.",
    "You do not respond to the world; you create the world you respond to.",
    "Between stimulus and response there is a space. In that space is our power to choose.",
]

REGION_COORDS = {
    "Global": (20.0, 0.0, 1),            # FIX: zoom 0 → 1 for usability
    "North America": (40.0, -100.0, 2),
    "South America": (-15.0, -60.0, 2),
    "Europe": (54.0, 15.0, 3),
    "Africa": (5.0, 20.0, 2),
    "Asia": (30.0, 90.0, 2),
    "Oceania": (-25.0, 135.0, 3),
}

COUNTRY_POINTS = [
    (38.0, -97.0, "United States", "North America"),
    (51.0, 9.0, "Germany", "Europe"),
    (35.0, 105.0, "China", "Asia"),
    (-14.0, -51.0, "Brazil", "South America"),
    (30.0, 31.0, "Egypt", "Africa"),
    (-25.0, 133.0, "Australia", "Oceania"),
]

REGION_TO_NEWSAPI_COUNTRY = {
    "North America": "us",
    "South America": "br",
    "Europe": "de",
    "Africa": "eg",
    "Asia": "cn",
    "Oceania": "au",
}


def compute_global_stress(region: str, seed: int) -> int:
    """Seeded random stress value so it stays stable across reruns on the same day."""
    rng = random.Random(seed + hash(region))
    base = rng.randint(40, 70)
    if region == "Global":
        return base + 10
    return base


# -----------------------
# NEWS FETCHING
# -----------------------

@st.cache_data(show_spinner="Fetching headlines…", ttl=timedelta(minutes=15))
def fetch_news(region: str, country_name: Optional[str] = None):
    """
    Fetch headlines from NewsAPI.
    Uses top-headlines only (free-tier compatible).
    """
    if not NEWS_API_KEY:
        return [], "Add NEWS_API_KEY to st.secrets"

    headers = {"X-Api-Key": NEWS_API_KEY}       # FIX: use header, not query param
    params = {
        "pageSize": 10,
    }

    url = "https://newsapi.org/v2/top-headlines"

    if country_name:
        # Search headlines by keyword (stays on top-headlines, free-tier safe)
        params["q"] = country_name
        # Still need a country or category or sources param for top-headlines
        if region in REGION_TO_NEWSAPI_COUNTRY:
            params["country"] = REGION_TO_NEWSAPI_COUNTRY[region]
        else:
            params["language"] = "en"
    else:
        if region in REGION_TO_NEWSAPI_COUNTRY:
            params["country"] = REGION_TO_NEWSAPI_COUNTRY[region]
        else:
            # FIX: Global with no country → use 'us' as default to avoid API error
            params["country"] = "us"

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return [], f"News error: {e}"

    if data.get("status") != "ok":
        return [], f"News API status not ok: {data.get('message')}"

    articles = data.get("articles", [])
    events = []
    for art in articles:
        title = art.get("title") or "Untitled"
        source_name = (art.get("source") or {}).get("name") or "Unknown"
        desc = art.get("description") or ""
        url_article = art.get("url") or ""
        events.append(
            {
                "title": title,
                "region": region,
                "country": country_name or "N/A",
                "description": desc,
                "source_name": source_name,
                "url": url_article,
            }
        )
    return events, None


# -----------------------
# POLITICAL COMPASS
# -----------------------

def interpret_political_compass(x: int, y: int) -> str:
    # FIX: use <= to close the gaps at boundaries
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
    return f"{header}\n\n{wrapped}"                 # FIX: real newlines


def political_compass_plot(x, y):
    fig = go.Figure()

    # Quadrant background shading
    fig.add_shape(type="rect", x0=-10, x1=0, y0=0, y1=10,
                  fillcolor="rgba(220,50,50,0.08)", line_width=0)
    fig.add_shape(type="rect", x0=0, x1=10, y0=0, y1=10,
                  fillcolor="rgba(50,50,220,0.08)", line_width=0)
    fig.add_shape(type="rect", x0=-10, x1=0, y0=-10, y1=0,
                  fillcolor="rgba(50,180,50,0.08)", line_width=0)
    fig.add_shape(type="rect", x0=0, x1=10, y0=-10, y1=0,
                  fillcolor="rgba(180,130,50,0.08)", line_width=0)

    # Axes lines
    fig.add_shape(type="line", x0=-10, x1=10, y0=0, y1=0,
                  line=dict(color="gray", width=1))
    fig.add_shape(type="line", x0=0, x1=0, y0=-10, y1=10,
                  line=dict(color="gray", width=1))

    # User's position
    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            marker=dict(size=16, color="#4C6FFF"),
            text=["You"],
            textposition="top center",
            textfont=dict(color="#E5E7EB", size=12),
            name="You",
        )
    )

    fig.update_layout(
        xaxis=dict(range=[-10, 10], zeroline=False,
                    title="Economic: Left (−10) ↔ Right (10)"),
        yaxis=dict(range=[-10, 10], zeroline=False,
                    title="Authority: Libertarian (−10) ↔ Authoritarian (10)"),
        height=350,
        margin=dict(l=40, r=40, t=30, b=40),
        plot_bgcolor="#020617",
        paper_bgcolor="#020617",
        font=dict(color="#E5E7EB"),
        showlegend=False,
    )
    return fig


# -----------------------
# SIDEBAR
# -----------------------

with st.sidebar:
    st.header("Filters")
    region = st.selectbox("Region", list(REGION_COORDS.keys()))
    region_countries = [c for c in COUNTRY_POINTS if c[3] == region or region == "Global"]
    country_names = ["All"] + [c[2] for c in region_countries]
    country = st.selectbox("Country", country_names)

    st.markdown("---")
    st.subheader("Political compass")
    x_axis = st.slider("Economic (Left −10 ↔ Right 10)", -10, 10, 0)
    y_axis = st.slider("Authority (Libertarian −10 ↔ Authoritarian 10)", -10, 10, 0)

# -----------------------
# LAYOUT
# -----------------------

# Seed once at the top so all random values are stable for the day
day_seed = date.today().toordinal()
random.seed(day_seed)

left_col, right_col = st.columns([3, 4])

# LEFT: Quote + Stress + Map
with left_col:
    quote = random.choice(SAMPLE_QUOTES)
    st.markdown("### Quote of the day")
    st.info(f"\u201c{quote}\u201d")             # FIX: proper Unicode curly quotes

    st.markdown("### Global stress meter")
    stress = compute_global_stress(region, day_seed)    # FIX: stable across reruns
    st.progress(stress / 100.0)
    st.caption(f"Estimated stress level for {region}: {stress}/100")

    st.markdown("### World map")

    lat, lon, zoom = REGION_COORDS[region]
    df_map = pd.DataFrame(
        [
            {"lat": c[0], "lon": c[1], "country": c[2]}
            for c in region_countries
            if country == "All" or c[2] == country
        ]
    )
    if df_map.empty:
        df_map = pd.DataFrame([{"lat": lat, "lon": lon, "country": "Center"}])

    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=zoom, pitch=0)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position="[lon, lat]",
        get_color="[200, 30, 0, 160]",
        get_radius=200_000,                         # FIX: clear underscore grouping
        pickable=True,
    )
    tooltip = {"text": "{country}"}
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/light-v9",
    )
    st.pydeck_chart(deck, use_container_width=True)

# RIGHT: Compass + Narratives
with right_col:
    st.markdown("### Political compass")
    st.plotly_chart(political_compass_plot(x_axis, y_axis), use_container_width=True)

    st.markdown("#### How you should deal with today's events")
    advice_text = interpret_political_compass(x_axis, y_axis)
    st.markdown(advice_text)                        # FIX: was st.code → st.markdown

    st.markdown("### Narratives & events")

    selected_country_name = None
    if country != "All":
        selected_country_name = country

    events, error = fetch_news(region, selected_country_name)

    if error:
        st.warning(error)
        st.info(
            "Set NEWS_API_KEY in Streamlit secrets to enable live events "
            "(Settings → Secrets in Streamlit Cloud)."
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
                    f"{ev['source_name']} · {ev['region']} / {ev['country']}"
                )

st.markdown("---")
st.caption(
    "Prototype: World Narrative Compass. Replace NewsAPI with your own world-events "
    "summarizer, add LLM-generated frames, and refine the compass logic."
)
