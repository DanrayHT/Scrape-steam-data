import requests
import pandas as pd


API_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"


def get_owned_games(api_key, steam_id):
    params = {
        "key": api_key,
        "steamid": steam_id,
        "format": "json",
    }

    response = requests.get(API_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()
    return data.get("response", {}).get("games", [])


def create_df(api_key, steam_ids):
    rows = []

    for user_id, steam_id in enumerate(steam_ids, start=1):
        games = get_owned_games(api_key, steam_id)

        print(
            f"SteamID {steam_id}: "
            f"{len(games)} games"
        )

        for game in games:
            rows.append({
                "user_id": user_id,
                "game_id": game["appid"],
                "playtime_forever": game["playtime_forever"],
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    API_KEY = input("Steam Web API key: ").strip()

    steam_ids = [
        "76561197960434622",
        "76561198978946242",
    ]

    df = create_df(API_KEY, steam_ids)

    print(df)
    df.to_csv("Poc (will not finish)/steam_user_games.csv", index=False)