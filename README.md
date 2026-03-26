# World Narrative Compass

A Streamlit dashboard that combines a political compass, world map, and live news headlines to help you interpret current events through your own ideological lens.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Add your NewsAPI key:
   ```
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Then edit `.streamlit/secrets.toml` with your key from [newsapi.org](https://newsapi.org/).

3. Run:
   ```
   streamlit run streamlit_app.py
   ```

## Features

- **Political compass** — Position yourself on economic (left/right) and authority (libertarian/authoritarian) axes to get tailored advice on interpreting the news.
- **World map** — Filter by region and country with interactive scatter points.
- **Live headlines** — Pulled from NewsAPI, cached for 15 minutes.
- **Stress meter** — Daily randomized indicator per region (placeholder for real data).
