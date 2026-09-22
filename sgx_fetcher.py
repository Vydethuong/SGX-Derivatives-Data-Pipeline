import os, time, logging, requests, zipfile
import sqlite3

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def is_html(path):
    try:
        with open(path, "rb") as f:
            head = f.read(4096).lower()
        return b"<html" in head
    except:
        return False

def is_valid_zip(path):
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except:
        return False


def download_file(url, save_path, max_retries=3):
    ensure_dir(os.path.dirname(save_path))
    tmp = save_path + ".part"

    attempt = 0
    while attempt < max_retries:
        try:
            resume_header = {}
            pos = 0
            if os.path.exists(tmp):
                pos = os.path.getsize(tmp)
                if pos > 0:
                    resume_header = {"Range": f"bytes={pos}-"}
                    logging.info("Resuming download from byte %d: %s", pos, url)

            r = requests.get(url, stream=True, timeout=60, headers=resume_header)

            if r.status_code in (200, 206):  
                content_type = r.headers.get("Content-Type", "").lower()
                content_length = int(r.headers.get("Content-Length") or 0)

                if content_length and content_length < 200:
                    logging.warning("File is too small (%d bytes): %s", content_length, url)

                if "html" in content_type:
                    raise Exception("Received HTML instead of data")

                mode = "ab" if pos > 0 else "wb"
                with open(tmp, mode) as f:
                    for chunk in r.iter_content(1024 * 256):
                        if chunk:
                            f.write(chunk)

                # validate & rename
                ext = os.path.splitext(save_path)[1].lower()
                if ext == ".zip" and not is_valid_zip(tmp):
                    raise Exception("Invalid ZIP file")
                elif ext in (".txt", ".dat") and is_html(tmp):
                    raise Exception("Text file contains HTML instead of data")

                os.replace(tmp, save_path)
                logging.info("Download successful: %s", save_path)
                return True
            else:
                raise Exception(f"HTTP {r.status_code}")

        except Exception as e:
            attempt += 1
            logging.warning("Error occurred while downloading (attempt %d/%d): %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(2)

    logging.error("Download failed completely after %d attempts: %s", max_retries, url)
    return False
