"""Download Home Credit Default Risk relational parquets from Hugging Face mirror."""
from pathlib import Path
import urllib.request
import sys

DATA_DIR = Path(__file__).resolve().parents[1] / 'data/home_credit'
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = 'https://huggingface.co/datasets/mohameddhameem/home-credit-default-risk/resolve/main'
FILES = {
    'application_train.parquet': f'{BASE_URL}/application_train_dated/train-00000-of-00001.parquet',
    'bureau.parquet': f'{BASE_URL}/bureau/train-00000-of-00001.parquet',
    'previous_application_0.parquet': f'{BASE_URL}/previous_application/train-00000-of-00002.parquet',
    'previous_application_1.parquet': f'{BASE_URL}/previous_application/train-00001-of-00002.parquet',
}

def download_all():
    print(f"Downloading Home Credit relational parquets to {DATA_DIR}...")
    for filename, url in FILES.items():
        dest = DATA_DIR / filename
        if dest.exists() and dest.stat().st_size > 1000000:
            print(f"✓ {filename} already exists ({dest.stat().st_size / (1024*1024):.1f} MB)")
            continue
        print(f"Fetching {filename}...")
        urllib.request.urlretrieve(url, dest)
        print(f"✓ Saved {filename} ({dest.stat().st_size / (1024*1024):.1f} MB)")
    print("All Home Credit files successfully downloaded and verified.")

if __name__ == '__main__':
    download_all()
