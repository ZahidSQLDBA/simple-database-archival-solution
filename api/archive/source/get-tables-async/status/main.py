"""
Copyright 2023 Amazon.com, Inc. and its affiliates. All Rights Reserved.

Licensed under the Amazon Software License (the "License").
You may not use this file except in compliance with the License.
A copy of the License is located at

  http://aws.amazon.com/asl/

or in the "license" file accompanying this file. This file is distributed
on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
express or implied. See the License for the specific language governing
permissions and limitations under the License.
"""

import boto3
import json
import logging
import os
import traceback

DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger = logging.getLogger()

if logger.hasHandlers():
    logger.setLevel(LOG_LEVEL)
else:
    logging.basicConfig(level=LOG_LEVEL)


def mask_sensitive_data(event):
    # remove sensitive data from request object before logging
    keys_to_redact = ["authorization"]
    result = {}
    for k, v in event.items():
        if isinstance(v, dict):
            result[k] = mask_sensitive_data(v)
        elif k in keys_to_redact:
            result[k] = "<redacted>"
        else:
            result[k] = v
    return result


def build_response(http_code, body):
    return {
        "headers": {
            "Cache-Control": "no-cache, no-store",  # tell cloudfront and api gateway not to cache the response
            "Content-Type": "application/json",
        },
        "statusCode": http_code,
        "body": body,
    }


def get_job_status(job_id):
    table = dynamodb.Table(DYNAMODB_TABLE)
    response = table.get_item(Key={"id": job_id})
    if "Item" in response:
        return response["Item"]["status"]
    else:
        return "NotFound"


def lambda_handler(event, context):
    logger.info(mask_sensitive_data(event))
    query_params = event.get('queryStringParameters', {})
    job_id = query_params.get('job_id')

    if not job_id:
        return build_response(400, json.dumps({"message": "Missing job_id query parameter"}))

    try:
        status = get_job_status(job_id)
        if status == "NotFound":
            return build_response(404, json.dumps({"message": "Job not found"}))
        else:
            return build_response(200, json.dumps({"status": status}))

    except Exception as ex:
        logger.error(traceback.format_exc())
        return build_response(500, "Server Error")


if __name__ == "__main__":
    example_event = {}
    response = lambda_handler(example_event, {})
