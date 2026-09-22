#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
import yaml

from sgx_crawler import get_links_for_date
from sgx_fetcher import download_file, ensure_dir


# ---------------- Logging ----------------
def setup_logging(cfg, log_level="INFO"):
    log_dir = cfg.get("log_dir", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"sgx_{datetime.now().strftime('%Y%m%d')}.log")

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter_console = logging.Formatter("[%(levelname)s] %(message)s")
    formatter_file = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # 1. Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter_console)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    # 2. File
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter_file)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    # 3. DB log (nếu bật)
    if cfg.get("db_log_enabled", False):
        from db_logger import DBLogHandler
        batch_size = cfg.get("db_log_batch_size", 10)
        dh = DBLogHandler(os.path.join(log_dir, "db_log.db"), batch_size=batch_size)
        dh.setFormatter(formatter_file)
        dh.setLevel(logging.ERROR)
        logger.addHandler(dh)


# ---------------- Helpers ----------------
def load_config(path="config.yml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_dates(args):
    if args.date:
        return [datetime.strptime(args.date, "%Y-%m-%d").date()]
    if args.start and args.end:
        d0 = datetime.strptime(args.start, "%Y-%m-%d").date()
        d1 = datetime.strptime(args.end, "%Y-%m-%d").date()
        out, cur = [], d0
        while cur <= d1:
            out.append(cur)
            cur += timedelta(days=1)
        return out
    return [datetime.now().date()]  # default: today


# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser(description="SGX Derivatives Data Downloader")
    parser.add_argument("--config", default="config.yml", help="Path to config.yml")
    parser.add_argument("--date", help="YYYY-MM-DD (download a specific day)")
    parser.add_argument("--start", help="YYYY-MM-DD (start date, used with --end)")
    parser.add_argument("--end", help="YYYY-MM-DD (end date, used with --start)")
    parser.add_argument("--force", action="store_true", help="Force re-download even if file exists")
    parser.add_argument("-v", action="count", default=0, help="-v=INFO, -vv=DEBUG")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.v == 0:
        log_level = "WARNING"
    elif args.v == 1:
        log_level = "INFO"
    else:
        log_level = "DEBUG"
    setup_logging(cfg, log_level)

    list_url = cfg["api"]["list_url"]
    base_url = cfg["api"]["base_url"]
    out_dir = cfg.get("download_dir", "data")
    ensure_dir(out_dir)

    had_fail = False

    days = iter_dates(args)
    logging.info("Number of days to download: %d", len(days))

    start_date = datetime.strptime(cfg["start_date"], "%Y-%m-%d").date()
    today = datetime.now().date()
    missing_files = []

    for delta in range((today - start_date).days + 1):
        date = start_date + timedelta(days=delta)
        date_str = date.strftime("%Y-%m-%d")
        urls = get_links_for_date(list_url, base_url, date_str)

        for url in urls:
            fname = os.path.basename(url)
            if fname == "TC.txt":
                fname = f"TC_{date.strftime('%Y%m%d')}.txt"
            save_path = os.path.join(out_dir, fname)

            if not os.path.exists(save_path):
                missing_files.append((url, date))

    if missing_files:
        for url, date in missing_files:
            fname = os.path.basename(url)
            if fname == "TC.txt":
                fname = f"TC_{date.strftime('%Y%m%d')}.txt"
            save_path = os.path.join(out_dir, fname)

            logging.info(f"Missing file: {url}")
            success = download_file(url, save_path)
            if not success:
                logging.error("Download failed after 3 attempts: %s", url)
                had_fail = True
    else:
        logging.info("No missing files from start-date to today.")

    for d in days:
        d_str = d.strftime("%Y-%m-%d")
        logging.info("Date to download: %s", d_str)

        urls = get_links_for_date(list_url, base_url, d_str)
        if not urls:
            logging.warning("No data found for date %s", d_str)
            continue

        for url in urls:
            fname = os.path.basename(url)
            if fname == "TC.txt":
                fname = f"TC_{d.strftime('%Y%m%d')}.txt"
            save_path = os.path.join(out_dir, fname)

            if os.path.exists(save_path) and not args.force:
                logging.info("Already exists: %s", save_path)
                continue

            logging.info("Downloading: %s", url)
            success = download_file(url, save_path)
            if not success:
                logging.error("Download failed completely: %s", url)
                had_fail = True

    return not had_fail   


if __name__ == "__main__":
    try:
        ok = main()
        if not ok:
            sys.exit(1)  # Airflow will mark the task as FAILED
    except KeyboardInterrupt:
        logging.warning("User interrupted the program with Ctrl+C.")
        sys.exit(1)
    except Exception as e:
        logging.exception("Unexpected error: %s", e)
        sys.exit(1)
