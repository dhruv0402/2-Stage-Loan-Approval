"""Download both cited Figshare snapshots with fixed checksum verification."""
from pathlib import Path
import hashlib
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / 'data/raw'
FILES = {
    'train_lending_club.csv': ('39316160', '8efebed1a9cbaba1edb511f9026732244c2a97497c73a8eb42d1f7864c77d8c1'),
    'test_lending_club.csv': ('39495787', '51dbe82c70c98a53802dfd585182f14842228a13061b29c3ebc21e880139805c'),
}
ROOT.mkdir(parents=True, exist_ok=True)
for name, (file_id, expected) in FILES.items():
    destination = ROOT / name
    if not destination.exists():
        urllib.request.urlretrieve(f'https://ndownloader.figshare.com/files/{file_id}', destination)
    actual = hashlib.sha256(destination.read_bytes()).hexdigest()
    if actual != expected:
        destination.unlink()
        raise SystemExit(f'{name}: checksum mismatch ({actual})')
    print(f'Verified {name}: {actual}')
