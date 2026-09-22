# Steam Data Scraper

A Python scraper that builds a **user–game playtime dataset** enriched with game metadata (name, review summary, popular tags) for a Steam game recommender.

## What the code does

The pipeline runs in two stages:

### 1. `src/steam_chart.py` - `create_df()`
- Downloads the original user playtime dataset from [steamgamerecommender/data_files_public](https://huggingface.co/datasets/steamgamerecommender/data_files_public) (4 CSV parts, cached in `data/steamgamerecommender/`).
- Concatenates them into one user–game dataframe.
- Scrapes [Steam Charts](https://steamcharts.com) to get the **average concurrent players over the last 30 days** for every unique game (concurrent requests via `ThreadPoolExecutor`).
- Drops games that Steam Charts doesn't track, and filters user records to only tracked games.
- Outputs:
  - `data/game_chart.csv` - unique games + `last_30d_avg`
  - `data/user.csv` - user–game records for tracked games

### 2. `src/steam_store.py` - `create_steam_info()`
- Reads `data/game_chart.csv` and `data/user.csv`.
- For each game, scrapes:
  - **Name** - from the Steam Store API (`/api/appdetails`)
  - **Review summary** and **top 5 popular tags** - from the Steam Store page
- Uses exponential backoff with retries to handle rate limiting (429/403/503).
- Drops games that can't be scraped (unavailable or region-locked), and filters user records accordingly.
- Outputs:
  - `data/game_info.csv` - final game metadata
  - `data/user_final.csv` - final user–game playtime records

Run with:

```bash
python main.py
```

> **Tip:** Use a proxy (e.g., rotate proxies in `requests`) for faster and more reliable scraping - Steam rate-limits aggressively, and proxies help avoid blocks and speed up the run.

## Dataset sizes

| Stage | Games |
|---|---|
| Unique games in original dataset | ~34,000 |
| After Steam Charts (before Steam Store) | 4,963 |
| After Steam Store (final) | 4,891 |

- Steam Charts only tracks a limited number of games, so most of the ~34k games are dropped in stage 1.
- The remaining ~72 games are dropped in stage 2 because they can't be accessed or are region-locked.

## Output data

### `data/user_final.csv`
User–game playtime records (kept only for games that survived both scraping stages). Each row links a user to a game with their playtime, so it can be joined with `game_info.csv` on `game_id` for recommendation features.

### `data/game_info.csv`
One row per game with:
- `game_id` - Steam App ID
- `last_30d_avg` - average concurrent players over the last 30 days (from Steam Charts, Data get from 22/9/2026)
- `name` - game name
- `review` - review summary (e.g., "Overwhelmingly Positive")
- `tags` - top 5 popular tags, pipe-separated (e.g., `Action|Adventure|Open World`)

## Hosted dataset

The final scraped dataset is available on Hugging Face:
[DanrayHT/steam_data_with_playtime](https://huggingface.co/datasets/DanrayHT/steam_data_with_playtime/)

## Project structure

```
├── main.py                  # Entry point
├── src/
│   ├── download_user_data.py  # Downloads original dataset from Hugging Face
│   ├── steam_chart.py         # Stage 1: Steam Charts scraping
│   └── steam_store.py         # Stage 2: Steam Store scraping
└── data/
    ├── game_chart.csv         # Stage 1 output
    ├── user.csv               # Stage 1 output
    ├── game_info.csv          # Final game metadata
    └── user_final.csv         # Final user–game records
```

## Proof of concept
You can try to get user data without outside dataset. It will required Steam web API key and a list of steamid.