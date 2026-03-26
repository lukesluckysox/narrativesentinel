# World Narrative Compass

A Streamlit dashboard that combines a political compass, world map, and live news headlines to help you interpret current events through your own ideological lens.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure API keys:
   ```
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   Then add at least one key. The app supports multiple news APIs simultaneously — it queries all configured APIs and merges the results.

3. Run:
   ```
   streamlit run streamlit_app.py
   ```

## Supported News APIs

| Provider | Free tier | Sign up |
|----------|-----------|---------|
| [NewsAPI.org](https://newsapi.org) | 100 req/day (dev only) | [Register](https://newsapi.org/register) |
| [NewsData.io](https://newsdata.io) | 200 req/day | [Register](https://newsdata.io/register) |
| [The Guardian](https://open-platform.theguardian.com) | 500 req/day (non-commercial) | [Register](https://open-platform.theguardian.com/access/) |
| [Currents API](https://currentsapi.services) | 600 req/day | [Register](https://currentsapi.services/en/register) |

You can use any combination. The sidebar shows which APIs are active.

## Features

- **Political compass** — Position yourself on economic (left/right) and authority (libertarian/authoritarian) axes to get tailored advice on interpreting the news. Sliders sit directly below the chart.
- **World map** — Filter by region and country with interactive scatter points.
- **Multi-source headlines** — Pulls from up to 4 news APIs, deduplicates, and shows the source for each article.
- **Stress meter** — Daily randomized indicator per region (placeholder for real data).
