import argparse
import hashlib
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

PACK = "buffalo_l"
FALLBACK_BASE_URL = "https://github.com/deepinsight/insightface/releases/download/v0.7"
ZIP_SHA256 = "80ffe37d8a5940d59a7384c201a2a38d4741f2f3c51eef46ebb28218a7b0ca2f"
EXPECTED_FILES = {
    "1k3d68.onnx": "df5c06b8a0c12e422b2ed8947b8869faa4105387f199c477af038aa01f9a45cc",
    "2d106det.onnx": "f001b856447c413801ef5c42091ed0cd516fcd21f2d6b79635b1e733a7109dbf",
    "det_10g.onnx": "5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91",
    "genderage.onnx": "4fde69b1c810857b88c64a335084f1c3fe8f01246c9a191b48c7bb756d6652fb",
    "w600k_r50.onnx": "4c06341c33c2ca1f86781dab0e829f88ad5b64be9fba56e56bc9ebdefc619e43",
}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def base_url():
    try:
        from insightface.utils import storage

        return storage.BASE_REPO_URL.rstrip("/")
    except Exception:
        return FALLBACK_BASE_URL


def is_complete(target):
    if not target.is_dir():
        return False
    for name, expected in EXPECTED_FILES.items():
        path = target / name
        if not path.is_file() or sha256(path) != expected:
            return False
    return True


def download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "FaceNexa-model-downloader/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        with open(destination, "wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                stream.write(chunk)
                received += len(chunk)
                if total:
                    print(f"\r  {received / 1048576:.1f} / {total / 1048576:.1f} MB", end="", flush=True)
    print()


def main():
    parser = argparse.ArgumentParser(description="Download and verify the InsightFace ONNX models used by Face Nexa")
    parser.add_argument("--model-dir", default=str(Path(__file__).resolve().parent / "models" / "insightface"))
    parser.add_argument("--force", action="store_true", help="Download even if verified models already exist")
    parser.add_argument("--keep-zip", action="store_true", help="Keep the downloaded model pack archive")
    parser.add_argument("--url", default=None, help="Override the model pack download URL")
    args = parser.parse_args()

    root = Path(args.model_dir).expanduser().resolve()
    models_dir = root / "models"
    target = models_dir / PACK
    target.mkdir(parents=True, exist_ok=True)

    if not args.force and is_complete(target):
        print(f"Models already present and verified in {target}")
        return 0

    url = args.url or f"{base_url()}/{PACK}.zip"
    archive_path = models_dir / f"{PACK}.zip"
    temp_path = Path(str(archive_path) + ".part")
    print(f"Downloading {PACK} from {url}")
    try:
        download(url, temp_path)
        actual = sha256(temp_path)
        if actual != ZIP_SHA256:
            raise RuntimeError(f"archive checksum mismatch: expected {ZIP_SHA256}, got {actual}")
        with zipfile.ZipFile(temp_path) as archive:
            names = set(archive.namelist())
            if names != set(EXPECTED_FILES):
                raise RuntimeError(f"unexpected archive contents: {sorted(names)}")
            archive.extractall(target)
        invalid = [name for name, expected in EXPECTED_FILES.items() if sha256(target / name) != expected]
        if invalid:
            raise RuntimeError(f"model checksum verification failed for: {', '.join(invalid)}")
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        print(f"Failed to install models: {exc}", file=sys.stderr)
        return 1

    if args.keep_zip:
        os.replace(temp_path, archive_path)
    else:
        temp_path.unlink(missing_ok=True)
    print(f"Models ready in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
