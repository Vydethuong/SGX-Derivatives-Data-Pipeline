from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from smtplib import SMTP

import os

# ---------------- Email sending function ----------------
def send_error_email(context):
    """Send email when task fails"""
    task_instance = context.get('task_instance')
    task_id = task_instance.task_id
    dag_id = task_instance.dag_id
    execution_date = context.get('execution_date')
    
    subject = f"Airflow Task Failed: {task_id}"
    body = f"""
    Task {task_id} in DAG {dag_id} failed. 
    Execution Date: {execution_date}
    """
    
    smtp_user = os.environ.get('SMTP_EMAIL', 'thuyvy29032004@gmail.com')
    smtp_password = os.environ.get('SMTP_APP_PASSWORD', '')

    if not smtp_password:
        return

    server = SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(smtp_user, smtp_password)  
    server.sendmail(smtp_user, smtp_user, f"Subject: {subject}\n\n{body}")  
    server.quit()

# ---------------- DAG config ----------------
default_args = {
    'owner': 'vivian',
    'depends_on_past': False,
    'retries': 0,  # retry logic already handled in fetcher.py
    'email_on_failure': True,   # enable email when task fails
    'email_on_retry': False,
    'email': ['thuyvy29032004@gmail.com'],  # replace with the recipient email
    'on_failure_callback': send_error_email,  # Callback when task fails
}

dag = DAG(
    dag_id='sgx_downloader',
    default_args=default_args,
    description='Download SGX derivatives data daily',
    schedule_interval='0 6 * * *',  # run daily at 6:00 AM
    start_date=datetime(2025, 9, 1),
    catchup=False,
    tags=['sgx', 'download'],
)

run_downloader = BashOperator(
    task_id='run_sgx_downloader',
    bash_command="cd /home/vivian/DTL && /home/vivian/DTL/venv/bin/python sgx_downloader.py --date {{ ds }} -v",
    dag=dag,
)
