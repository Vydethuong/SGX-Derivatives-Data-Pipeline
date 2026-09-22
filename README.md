````markdown
# SGX Derivatives Data Downloader

---

## I. Introduction & Setup

### 1. Overview
This project downloads daily derivatives data from the Singapore Exchange (SGX). Files are fetched from the SGX website via an API and include:
- `WEBPXTICK_DT-*.zip`: Primary tick data files
- `TickData_structure.dat`: Schema for `WEBPXTICK_DT-*.zip`
- `TC_*.txt`: TC data files
- `TC_structure.dat`: Schema for `TC_*.txt`

The project supports downloading both historical files (not just the current day) and today’s data.

### 2. Requirements
- Python 3.x
- Required libraries:
  - `airflow` (for running the DAG)
  - `requests`
  - `PyYAML`
  - `python-dateutil`
  - `sqlite3` (for logging to a database)

Install the dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
````

---

## II. Usage & Configuration

### 3. How to Use

#### 3.1. Download data for a specific date

Use the `--date` argument:

```bash
python sgx_downloader.py --date 2025-09-01
```

#### 3.2. Download data for a date range

Use the `--start` and `--end` arguments:

```bash
python sgx_downloader.py --start 2025-09-01 --end 2025-09-03
```

#### 3.3. Command-line options

* `--date`: Download data for a specific date.
* `--start` and `--end`: Download data from the start date through the end date.
* `--force`: Force re-download even if the file already exists.
* `-v`: Set log verbosity (e.g., `-v` for `INFO`, `-vv` for `DEBUG`).

### 4. Configuration

Project configuration is stored in `config.yml`. You can customize parameters such as the download directory and API settings.

Example `config.yml`:

```yaml
start_date: "2025-06-01"
api:
  list_url: "https://api3.sgx.com/infofeed/Apps?A=COW_Tickdownload_Content&B=TimeSalesData&C_T=20"
  base_url: "https://links.sgx.com/1.0.0/derivatives-historical"
download_dir: "data"
log_dir: "logs"
db_log_enabled: true  # Enable database logging
db_log_batch_size: 20  # Number of logs batched per commit
db_path: "logs/db_log.db"  # Path to SQLite database
```

---

## III. Logging & Error Handling

### 5. Logging and Error Handling

* Errors are written to the console, a log file, and the database.
* If a download fails, the system will automatically retry (up to 3 times).
* If files are missing between the start date and today and are listed on the website, the system will automatically re-download the missing files.

---

## IV. Error Logging to the Database (DB)

The system records critical errors in a database (DB). This helps persist and track errors and makes it easy to query them later. Errors are logged to the database according to the settings in **`config.yml`**. Errors are only stored if **`db_log_enabled`** is **True**.

### **DB Logging Configuration**

When **`db_log_enabled`** is enabled in **`config.yml`**, error logs are written to a SQL database (e.g., **SQLite**).

In **`config.yml`**, set the following to enable DB logging:

```yaml
# DB logging configuration
db_log_enabled: true      # Enable DB logging
db_log_batch_size: 20     # Batch size before committing
db_path: "logs/db_log.db" # Path to the (SQLite) database
```

### **Logging Process**

* **DBLogHandler** writes errors to the database. When an error occurs during file downloads (e.g., unable to fetch a file from SGX), the error is recorded via DBLogHandler in addition to console and file logs.

* Each error record includes:

  * **Timestamp**
  * **Error message**
  * **Context information** (e.g., module, function, line number)

* You can inspect the log table with: `python inspect_db.py`

### **Benefits of DB Logging**

* Easy to **query** errors when needed.
* Enables **analysis and statistics** over time.
* Helps **track and manage** long-term issues.

---

## V. Design & Recovery Plan

### 7. Addressing Design Concerns

1. **Historical data downloads**

   * **Issue**: The SGX API only provides the latest files and the dates currently available on the website. If an older date is not available, the API returns no data.
   * **Solution**: The system attempts to download all files from the configured `start_date` up to today. 
     - If the file for a given date is still available via the API, it will be downloaded normally through `sgx_downloader.py`.
     - If the file is no longer available through the API, the system logs this event and informs the user. The log includes the missing date so that users can cross-check and manually construct the download URL.
     - Additionally, as an **optional extension**, the script `brute_force_crawler.py` can brute-force the SGX file server to build a complete `{id ↔ filename ↔ date}` mapping. This mapping (`id_mapping.txt`) can then be used to recover historical files beyond the API’s limits.
     - All attempted download URLs from sgx_downloader.py are recorded in logs. This allows users to manually reconstruct links for recovery if the API no longer provides older files.

   * **Manual Recovery via URL Template**:  
     If a file is not retrievable via the API, users can reconstruct the download link using the logged date and the following URL template (replace `{id}` with the numeric code and `{date}` with the target date):

     - Tick data:  
       `https://links.sgx.com/1.0.0/derivatives-historical/{id}/WEBPXTICK_DT.zip`
     - Tick data structure:  
       `https://links.sgx.com/1.0.0/derivatives-historical/{id}/TickData_structure.dat`
     - TC data:  
       `https://links.sgx.com/1.0.0/derivatives-historical/{id}/TC.txt`
     - TC data structure:  
       `https://links.sgx.com/1.0.0/derivatives-historical/{id}/TC_structure.dat`


2. **Handling failed downloads**

   * **Issue**: Downloads may fail due to unstable network connections or temporary SGX-side errors.
   * **Solution**: The system implements automatic retries—up to 3 attempts with exponential backoff. If all attempts fail, the task will fail and **Airflow will send an error notification** so the user can intervene if necessary.

3. **Duplicate files**

   * **Issue**: Some files may already exist and do not need to be re-downloaded.
   * **Solution**: Provide a `--force` option so users can force re-download even if the file is present.

4. **Error reporting and email alerts**

   * **Issue**: Users need to be alerted when errors occur during downloads.
   * **Solution**: Use an Airflow DAG to automate downloads and send email alerts when tasks fail. This ensures timely notifications to operators/users.

5. **Scalability and maintenance**

   * **Issue**: SGX data and endpoints may change or expand over time.
   * **Solution**: The codebase is designed for easy maintenance and extension, with clean structure and clear configuration. API URLs, storage directories, and logging parameters can be adjusted in `config.yml`.

6. **Logging and Error Handling**

   * **Error destinations**: All errors are written to three places — the console, a log file, and the database (if enabled).  
   * **Automatic retries**: If a download fails, the system will automatically retry up to 3 times with exponential backoff.  
   * **Missing file recovery**: If files are missing between the configured start date and today but are still listed on the SGX website, the system will automatically re-download those missing files.  
   * **Logged URLs for manual recovery**: Every attempted download URL is recorded in the logs. This ensures that even if a file cannot be fetched automatically (e.g., due to SGX removing older files or endpoint changes), users can still manually re-download files later using the logged URLs.


---

### 8. Recovery Plan

1. **If downloads fail on one or more days, how do we re-download missing files?**

   * **Solution**: When a file fails to download, the system logs the error and notifies the user. The system will automatically retry up to 3 times (with exponential backoff). If it still fails, the task will fail and **Airflow will send an error notification**. Users can check the logs and use the saved URLs to re-download files.

2. **Is re-downloading automatic or manual?**

   * **Automatic**: The system automatically retries failed downloads up to 3 times. If it still cannot download the file, the task fails and **Airflow sends an error email**.
   * **Manual**: If automatic retries fail (e.g., persistent network issues or the file is unavailable), users can copy the URLs from the logs and re-download necessary files manually—without rerunning the entire job from scratch.

3. **The website lists only recent files. Can we download older files?**

   * **Solution**: By default, the SGX API only exposes recent files. However, if download URLs were saved in past logs, users can still fetch historical files again using those logged links. Previously downloaded files remain accessible even if they are no longer listed by the current API.

   * **Optional Extension**: A separate script `brute_force_crawler.py` can brute-force all possible `{id ↔ filename ↔ date}` mappings (including `.tic`, `.gz`, and `.zip` formats). The result is saved into `id_mapping.txt`, which can then be used to restore historical files beyond the API’s limits.

   * **Note**: If historical files cannot be obtained via either the API or the mapping, users may request them directly from SGX through official support channels.

4. **Resuming from `.part` files**

   * **Resume partial downloads**: If the download process is interrupted, the system creates a `.part` file containing the partial data. On rerun, the system checks for the `.part` file and resumes from where it left off instead of starting over.
   * **Benefit**: Saves time and bandwidth when interruptions occur (e.g., connection loss or temporary errors).

---

## VI. Airflow Integration & Error Notifications

### 9. Error Detection and Email Alerts (Airflow DAG)

If you use Airflow to automate downloads, the system can send email notifications upon task failures:

* **Detecting errors & re-downloading missing files**:

  * If a file fails to download, the system automatically retries up to 3 times with exponential backoff. If all attempts fail, Airflow reports the failure via email so the user can take manual action.
  * If a file is **missing** and **not** available on the SGX website, the system will **not** download it. Only missing files that are available on the website will be retrieved. If there is no data for a requested date, the system will report that no data exists for that date and mark the task as successful (to avoid unnecessary pipeline disruption). Users can request historical files directly from SGX if needed.

* **Re-downloading missing files**:

  * Use an Airflow DAG to automate re-downloads of missing files.
  * The DAG runs daily and pulls required files from SGX, including both historical files (when available) and today’s data.

* **Email alerts on task failure**:

  * When an Airflow task fails (e.g., a file can’t be downloaded), Airflow sends an error email to the operator. This ensures issues aren’t overlooked.

10. **Optional Extensions**

   * **Solution**: In addition to the main API-based sgx_downloader.py, the project provides a separate script `brute_force_crawler.py` that brute-forces all possible IDs on SGX’s historical file server.
   * **Output**: The script generates a mapping `{id ↔ filename ↔ date}` and saves it into `id_mapping.txt`. This file acts as a catalog of all available historical files (including `.tic`, `.gz`, `.zip` formats).
   * **Usage**:  After `id_mapping.txt` has been generated, users do **not** need to run `brute_force_crawler.py` again. Instead, they can directly consult `id_mapping.txt` whenever they need to locate and restore historical files.  
   * **Purpose**:  The brute-force crawler is designed as a **research and recovery tool** to ensure that historical files remain accessible even if SGX changes its API or stops exposing older files.  
   In normal operation, `sgx_downloader.py` (API-based) is sufficient. The brute-force crawler is optional and only useful when the API cannot provide the required historical data.
   * **Benefit**: With `id_mapping.txt`, users can restore or re-download historical files beyond the API’s listing limits. This ensures that older data remains recoverable even if SGX changes the API endpoint or restricts access to older files in the future.


```
