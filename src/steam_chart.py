import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from download_user_data import DATA_DIR, USER_PARTS, download_user_files

def get_last_30d_avg(game_id: int) -> float:
    url = f"https://steamcharts.com/app/{game_id}"
    headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }

    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    cell = soup.find("td", string=lambda t: "Last 30 Days" in t)
    if cell is None:
        return None
    row = cell.find_parent("tr")
    num = row.find("td", class_="num-f").get_text(strip=True).replace(",", "")
    return float(num)


def add_30d_avg(df, max_workers=6):
    if "game_id" not in df.columns:
        raise ValueError("df must contain an 'game_id' column")

    df = df.copy()

    game_ids = df["game_id"].astype(int).unique()
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_last_30d_avg, game_id): game_id
            for game_id in game_ids
        }

        for i, future in enumerate(as_completed(futures), 1):
            game_id = futures[future]
            results[game_id] = future.result()

            if i % 50 == 0 or i == len(game_ids):
                print(f"Progress: {i}/{len(game_ids)}")

    df["last_30d_avg"] = df["game_id"].astype(int).map(results)

    return df

def create_df(max_workers):
    download_user_files()

    df_user = pd.concat([pd.read_csv(DATA_DIR / part / "users_games.csv")for part in USER_PARTS],
                        ignore_index=True,
    )

    df_game = df_user[["game_id"]].drop_duplicates().reset_index(drop=True)
    
    df_game = add_30d_avg(df_game, max_workers=max_workers)
    original_game_count = len(df_game)
    print(f"Unique games: {original_game_count}")

    df_game = df_game.dropna(subset=["last_30d_avg"]).reset_index(drop=True)
    valid_game_ids = set(df_game["game_id"])
    df_user = df_user[df_user["game_id"].isin(valid_game_ids)].reset_index(drop=True)

    print(f"Tracked games: {len(df_game)}")
    print(f"Removed games: {original_game_count - len(valid_game_ids)}")
    print(f"User-game records remaining: {len(df_user)}")

    return df_user, df_game