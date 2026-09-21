from pathlib import Path
from huggingface_hub import hf_hub_download

HF_REPO_ID = "steamgamerecommender/data_files_public"
DATA_DIR = Path("data/steamgamerecommender")

USER_PARTS = [
    "0",
    "20000",
    "39935",
    "59526",
]


def download_user_files():
    for part in USER_PARTS:
        folder = DATA_DIR / part
        local_path = folder / "users_games.csv"

        if local_path.exists():
            print(f"Skip: {local_path}")
            continue

        folder.mkdir(parents=True, exist_ok=True)

        print(f"Downloading: {part}/users_games.csv")

        hf_hub_download(
            repo_id=HF_REPO_ID,
            repo_type="dataset",
            filename=f"{part}/users_games.csv",
            local_dir=str(DATA_DIR),
        )

        print(f"Downloaded: {local_path}")