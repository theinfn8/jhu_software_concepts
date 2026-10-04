"""
S3 data fetch utility for the Grad School Cafe data pipeline.

This module provides a helper function for downloading the applicant
dataset from Amazon S3 into a SageMaker notebook environment for local
processing.

:module: fetch_s3
:synopsis: Download applicant_data.json from S3 for notebook processing.
"""

import os
import boto3

def download_applicant_data(
    bucket_name="grad-cafe-cc",
    key="applicant_data.json",
    local_filename="applicant_data_SM.json",
    local_dir="."
):
    """
    Download applicant_data.json from an S3 bucket and save it locally.

    Uses :meth:`boto3.client.download_file` to stream the object directly
    to disk. Relies on the ambient AWS credentials available in the
    execution environment (e.g. a SageMaker execution role) rather than
    accepting explicit credentials.

    :param bucket_name: Name of the S3 bucket containing the file.
    :type bucket_name: str
    :param key: S3 object key (path) for the source file.
    :type key: str
    :param local_filename: Name to save the downloaded file as locally.
    :type local_filename: str
    :param local_dir: Local directory to save the file into.
    :type local_dir: str
    :raises FileNotFoundError: If the specified key does not exist in the
        bucket, or the bucket itself does not exist or is not accessible.
    :raises RuntimeError: If the download fails for any other reason
        (e.g. permissions, network errors).
    :returns: The full local path to the downloaded file.
    :rtype: str
    """

    s3 = boto3.client("s3")
    local_path = os.path.join(local_dir, local_filename)

    try:
        s3.download_file(bucket_name, key, local_path)
        size_kb = os.path.getsize(local_path) / 1024
        print(f"Downloaded s3://{bucket_name}/{key} -> {local_path} ({size_kb:.1f} KB)")
        return local_path
    except s3.exceptions.NoSuchKey as e:
        raise FileNotFoundError(f"'{key}' not found in bucket '{bucket_name}'.") from e
    except s3.exceptions.NoSuchBucket as e:
        raise FileNotFoundError(f"Bucket '{bucket_name}' \
does not exist or is not accessible.") from e
    except Exception as e:
        raise RuntimeError(f"Failed to download '{key}' from '{bucket_name}': {e}") from e
