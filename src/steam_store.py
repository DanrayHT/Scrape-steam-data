import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from steam_chart import create_df

def get_steam_info(game_id: int) -> float:
    url = f"https://store.steampowered.com/app/{game_id}"
    headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }

    resp = requests.get(url, headers=headers, cookies={"birthtime": "568022401", "mature_content": "1"})
    soup = BeautifulSoup(resp.text, "html.parser")
    name = soup.find("div", id="appHubAppName").get_text(strip=True)
    review = soup.select_one("#userReviews span.game_review_summary").get_text(strip=True)
    tags = [
        a.get_text(strip=True)
        for a in soup.select("div.glance_tags.popular_tags a.app_tag")
    ]
    return {
        "name": name,
        "review": review,
        "tags": "|".join(tags[:5])
    }

def add_steam_info(df, max_workers=6):
    if "game_id" not in df.columns:
        raise ValueError("df must contain an 'game_id' column")

    df = df.copy()
    game_ids = df["game_id"].astype(int).unique()
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_steam_info, game_id): game_id
            for game_id in game_ids
        }

        for i, future in enumerate(as_completed(futures), 1):
            game_id = futures[future]
            results[game_id] = future.result()

            if i % 50 == 0 or i == len(game_ids):
                print(f"Progress: {i}/{len(game_ids)}")

    df["name"] = df["game_id"].astype(int).map(lambda x: results[x]["name"])
    df["review"] = df["game_id"].astype(int).map(lambda x: results[x]["review"])
    df["tags"] = df["game_id"].astype(int).map(lambda x: results[x]["tags"])

    return df