import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from steam_chart import create_df

def get_steam_info(game_id: int) -> dict:
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

    name_tag = soup.find("div", id="appHubAppName")
    review_tag = soup.select_one("#userReviews span.game_review_summary")

    if name_tag is None or review_tag is None:
        return None

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
            result = future.result()

            if result is None:
                print(f"Skip game: {game_id}")
                continue

            results[game_id] = result

            if i % 50 == 0 or i == len(game_ids):
                print(f"Progress: {i}/{len(game_ids)}")

    df = df[df["game_id"].astype(int).isin(results)].copy()
    df["name"] = df["game_id"].astype(int).map(lambda x: results[x]["name"])
    df["review"] = df["game_id"].astype(int).map(lambda x: results[x]["review"])
    df["tags"] = df["game_id"].astype(int).map(lambda x: results[x]["tags"])

    return df

def create_steam_info(max_workers=6):
    df_user, df_game = create_df(max_workers)
    original_game_count = len(df_game)
    df_game = add_steam_info(df_game, max_workers=max_workers)

    valid_game_ids = set(df_game["game_id"].astype(int))
    df_user = df_user[df_user["game_id"].astype(int).isin(valid_game_ids)].reset_index(drop=True)

    print(f"Games before Steam Store: {original_game_count}")
    print(f"Games after Steam Store: {len(df_game)}")
    print(f"Removed games: {original_game_count - len(df_game)}")
    print(f"User-game records remaining: {len(df_user)}")

    df_game.to_csv("data/game_info.csv", index=False)
    df_user.to_csv("data/user.csv", index=False)