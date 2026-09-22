import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.steam_chart import create_df


def is_blocked(resp: requests.Response) -> bool:
    if resp.status_code in (429, 403, 503):
        print(resp.status_code)
        return True

    return False


def fetch_with_backoff(url, headers, cookies=None, max_retries=5, base_delay=30):
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}, retry...")
            time.sleep(base_delay * (2 ** (attempt - 1)))
            continue

        if not is_blocked(resp):
            return resp

        delay = base_delay * (2 ** (attempt - 1))
        print(f"Get block (attempt {attempt}/{max_retries}), wait {delay}s to retry")
        time.sleep(delay)

    print("Too much retry attemp -> skip")
    return None

def get_steam_info(game_id: int) -> dict | None:
    url = f"https://store.steampowered.com/app/{game_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    }
    cookies = {
        "birthtime": "568022401",
        "mature_content": "1",
        "wants_mature_content": "1",
        "lastagecheckage": "1-0-1990"
    }

    api_url = f"https://store.steampowered.com/api/appdetails?appids={game_id}"
    print(f"[{game_id}] API start", flush=True)
    api_resp = fetch_with_backoff(api_url, headers)

    if api_resp is None:
        return None

    try:
        api_data = api_resp.json()
    except ValueError:
        return None

    app_data = api_data.get(str(game_id))
    if not app_data or not app_data.get("success"):
        return None

    name = app_data["data"]["name"]

    resp = fetch_with_backoff(url, headers, cookies)
    print(f"[{game_id}] STORE done", flush=True)
    if resp is None:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    review_tag = soup.select_one("#userReviews span.game_review_summary")

    if review_tag is None:
        return None

    review = review_tag.get_text(strip=True)
    tags = [
        a.get_text(strip=True)
        for a in soup.select("div.glance_tags.popular_tags a.app_tag")
    ]
    return {"name": name, "review": review, "tags": "|".join(tags[:5])}

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
            try:
                result = future.result()
            except Exception as e:
                print(f"[{game_id}] Error: {e}")
                continue

            if result is None:
                print(f"Skip game: {game_id}")
                continue

            results[game_id] = result
            print(f"Progress: {i}/{len(game_ids)}")              

    df = df[df["game_id"].astype(int).isin(results)].copy()
    df["name"] = df["game_id"].astype(int).map(lambda x: results[x]["name"])
    df["review"] = df["game_id"].astype(int).map(lambda x: results[x]["review"])
    df["tags"] = df["game_id"].astype(int).map(lambda x: results[x]["tags"])

    return df

def create_steam_info(max_workers=1):
    # create_df(max_workers) # Data get from 22/9/2026, only track 4963 games because steam chart have limit data
    df_game = pd.read_csv("data/game_chart.csv")
    print("read df_game")
    df_user = pd.read_csv("data/user.csv")
    print("read df_user")
    original_game_count = len(df_game)
    print("start scraping data")
    df_game = add_steam_info(df_game, max_workers=max_workers)

    valid_game_ids = set(df_game["game_id"].astype(int))
    df_user = df_user[df_user["game_id"].astype(int).isin(valid_game_ids)].reset_index(drop=True)

    print(f"Games before Steam Store: {original_game_count}")
    print(f"Games after Steam Store: {len(df_game)}")
    print(f"Removed games: {original_game_count - len(df_game)}")
    print(f"User-game records remaining: {len(df_user)}")

    df_game.to_csv("data/game_info.csv", index=False)
    df_user.to_csv("data/user_final.csv", index=False)