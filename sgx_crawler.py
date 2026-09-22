import requests, logging, time, os
from datetime import datetime, timedelta
from sgx_fetcher import download_file
from sgx_fetcher import ensure_dir


def fetch_with_retry(url, retries=3, delay=2):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=(10, 30))
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error("API call failed %s (lần %d/%d): %s", url, attempt, retries, e)
            if attempt < retries:
                time.sleep(delay * attempt)  # exponential backoff
            else:
                return None

# Get file links for a specific date
def get_links_for_date(list_url, base_url, date_str, retries=3):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    target = d.strftime("%d %b %Y")

    try:
        r = fetch_with_retry(list_url, retries=retries, delay=2)
        if not r:
            logging.error("Failed to call API after multiple retries")
            return []
        data = r.json()
    except requests.exceptions.RequestException as e:
        logging.error("Failed to call API SGX: %s", e)
        return []
    except Exception as e:
        logging.error("Failed parse JSON from API: %s", e)
        return []

    for item in data.get("items", []):
        if item.get("Date") == target:
            key = item["key"]
            return [
                f"{base_url}/{key}/{item['Data File']}",
                f"{base_url}/{key}/{item['Tick Data Structure File']}",
                f"{base_url}/{key}/TC.txt",
                f"{base_url}/{key}/{item['TC Data Structure File']}"
            ]
    return []


def get_missing_files(start_date, list_url, base_url, out_dir):
    today = datetime.now().date()
    missing_files = []

    for delta in range((today - start_date).days + 1):
        date = start_date + timedelta(days=delta)
        date_str = date.strftime("%Y-%m-%d")

        urls = get_links_for_date(list_url, base_url, date_str)
        for url in urls:
            fname = os.path.basename(url)
            save_path = os.path.join(out_dir, fname)

            if not os.path.exists(save_path):
                if fname == "TC.txt":
                    fname = f"TC_{date.strftime('%Y%m%d')}.txt"  
                    save_path = os.path.join(out_dir, fname)

                missing_files.append(url)

    return missing_files

def download_missing_files_from_start_date(cfg):
    start_date = datetime.strptime(cfg["start_date"], "%Y-%m-%d").date()
    list_url = cfg["api"]["list_url"]
    base_url = cfg["api"]["base_url"]
    out_dir = cfg.get("download_dir", "data")
    
    ensure_dir(out_dir)

    missing_files = get_missing_files(start_date, list_url, base_url, out_dir)
    
    if missing_files:
        for url in missing_files:
            fname = os.path.basename(url)
            save_path = os.path.join(out_dir, fname)

            if fname == "TC.txt" and not os.path.exists(save_path):
                fname = f"TC_{start_date.strftime('%Y%m%d')}.txt"
                save_path = os.path.join(out_dir, fname)

            logging.info(f"Down missing file: {url}")
            download_file(url, save_path)
    else:
        logging.info("No missing files from start_date to today.")