import requests
import os
import re
import logging
from sgx_fetcher import ensure_dir

BASE_URL = "https://links.sgx.com/1.0.0/derivatives-historical"
OUT_DIR = "data"
MAPPING_FILE = "id_date_mapping.txt"

def fetch_with_retry(url, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=(10, 30))
            if r.status_code == 200 and r.content:
                return r
            else:
                logging.warning("No file at %s (status %s)", url, r.status_code)
                return None
        except Exception as e:
            logging.error("Request failed %s (attempt %d/%d): %s", url, attempt, retries, e)
    return None

def extract_filename(r, fallback):
    cd = r.headers.get("Content-Disposition", "")
    if "filename=" in cd:
        return cd.split("filename=")[-1].strip('"')
    return fallback

def extract_date_from_name(name):
    match = re.search(r"\d{8}", name)
    return match.group(0) if match else "UNKNOWN"

def bruteforce_download(start_id=1, end_id=50):
    ensure_dir(OUT_DIR)
    mapping_path = os.path.join(OUT_DIR, MAPPING_FILE)

    with open(mapping_path, "a", encoding="utf-8") as f:
        for file_id in range(start_id, end_id + 1):
            url = f"{BASE_URL}/{file_id}/WEBPXTICK_DT.zip"
            logging.info("Fetching id=%d from %s", file_id, url)

            r = fetch_with_retry(url)
            if not r:
                continue

            real_name = extract_filename(r, f"WEBPXTICK_DT_{file_id}.zip")
            trade_date = extract_date_from_name(real_name)

            if trade_date != "UNKNOWN":
                save_name = f"WEBPXTICK_DT-{trade_date}.zip"
            else:
                save_name = f"id{file_id}_{real_name}"

            save_path = os.path.join(OUT_DIR, save_name)
            with open(save_path, "wb") as out:
                out.write(r.content)

            f.write(f"{file_id},{real_name},{trade_date}\n")
            logging.info("Saved %s (id=%d, date=%s)", save_name, file_id, trade_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    bruteforce_download(start_id=0, end_id=6022)
