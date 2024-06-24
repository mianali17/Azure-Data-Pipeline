import os
import logging
from datetime import datetime

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from azure.storage.blob import BlobServiceClient, BlobClient, BlobType
import pyarrow.csv as pv
import pyarrow.parquet as pq

# Set up environment variables for Azure
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.environ.get("AZURE_CONTAINER_NAME")
FILE_SYSTEM_NAME = os.environ.get("AZURE_FILE_SYSTEM_NAME")

AIRFLOW_HOME = os.environ.get("AIRFLOW_HOME", "/opt/airflow")

URL_PREFIX = f"https://github.com/DataTalksClub/nyc-tlc-data/releases/download/green/"
URL_TEMPLATE = URL_PREFIX + 'green_tripdata_{{ execution_date.strftime(\'%Y-%m\') }}.csv.gz'   
OUTPUT_FILE_TEMPLATE = 'green_{{ execution_date.strftime(\'%Y-%m\') }}.csv'

PARQUET_FILE = OUTPUT_FILE_TEMPLATE.replace('.csv', '.parquet')

def format_to_parquet(src_file):
    if not src_file.endswith('.csv'):
        logging.error("Can only accept source files in CSV format, for the moment")
        return
    table = pv.read_csv(src_file)
    pq.write_table(table, src_file.replace('.csv', '.parquet'))

# def upload_to_azure(blob_service_client, container_name, object_name, local_file):
#     blob_client = blob_service_client.get_blob_client(container=container_name, blob=object_name)

#     chunk_size = 4 * 1024 * 1024  # 4 MB chunks

#     with open(local_file, "rb") as data:
#         for chunk in iter(lambda: data.read(chunk_size), b""):
#             blob_client.upload_blob(chunk, blob_type=BlobType.AppendBlob, overwrite=True)


def upload_to_azure(blob_service_client, container_name, object_name, local_file, timeout=600):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=object_name)

    with open(local_file, "rb") as data:
        blob_client.upload_blob(data, blob_type=BlobType.BlockBlob, overwrite=True, timeout=timeout)



default_args = {
    "owner": "airflow",
    "start_date": datetime(2019, 1, 1),
    "end_date": datetime(2021, 7, 2),   
    "depends_on_past": False,
    "retries": 1,
}

with DAG(
    dag_id="data_ingestion_azure_dag_greentaxis",
    schedule_interval="@monthly",
    default_args=default_args,
    catchup=True,
    max_active_runs=1,
    tags=['dtc-de-all-greentaxis'],
) as dag:

    download_dataset_task = BashOperator(
        task_id="download_dataset_task",
        bash_command=f"curl -sSL {URL_TEMPLATE} | gunzip -c > {AIRFLOW_HOME}/{OUTPUT_FILE_TEMPLATE}"
    )

    format_to_parquet_task = PythonOperator(
        task_id="format_to_parquet_task",
        python_callable=format_to_parquet,
        op_kwargs={
            "src_file": f"{AIRFLOW_HOME}/{OUTPUT_FILE_TEMPLATE}",
        },
    )

    local_to_azure_task = PythonOperator(
        task_id="local_to_azure_task",
        python_callable=upload_to_azure,
        op_kwargs={
            "blob_service_client": BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING),
            "container_name": CONTAINER_NAME,
            "object_name": f"raw/{PARQUET_FILE}",
            "local_file": f"{AIRFLOW_HOME}/{PARQUET_FILE}",
            "timeout": 600,
        },
    )

    remove_files_task = BashOperator(
        task_id="remove_files_task",
        bash_command=f"rm {AIRFLOW_HOME}/{OUTPUT_FILE_TEMPLATE} {AIRFLOW_HOME}/{PARQUET_FILE}"
    )

    download_dataset_task >> format_to_parquet_task >> local_to_azure_task >> remove_files_task