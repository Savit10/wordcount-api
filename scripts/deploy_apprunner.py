#!/usr/bin/env python3
import json
import os
import sys
from typing import Optional

import boto3
from botocore.exceptions import ClientError


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_service_arn(apprunner_client, service_name: str) -> Optional[str]:
    next_token = None
    while True:
        request = {}
        if next_token:
            request["NextToken"] = next_token

        page = apprunner_client.list_services(**request)
        for service in page.get("ServiceSummaryList", []):
            if service.get("ServiceName") == service_name:
                return service.get("ServiceArn")

        next_token = page.get("NextToken")
        if not next_token:
            break
    return None


def get_runtime_env_vars() -> list[dict[str, str]]:
    raw = os.getenv("RUNTIME_ENV_VARS_JSON", "").strip()
    if not raw:
        return []

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError("RUNTIME_ENV_VARS_JSON must be a JSON object.")

    env_vars = []
    for key, value in parsed.items():
        env_vars.append({"Name": str(key), "Value": str(value)})
    return env_vars


def main() -> int:
    region = require_env("AWS_REGION")
    service_name = require_env("SERVICE_NAME")
    image_uri = require_env("IMAGE_URI")
    access_role_arn = require_env("APPRUNNER_ECR_ACCESS_ROLE_ARN")
    container_port = os.getenv("CONTAINER_PORT", "8000")
    runtime_env_vars = get_runtime_env_vars()

    apprunner = boto3.client("apprunner", region_name=region)

    source_configuration = {
        "AuthenticationConfiguration": {"AccessRoleArn": access_role_arn},
        "AutoDeploymentsEnabled": False,
        "ImageRepository": {
            "ImageIdentifier": image_uri,
            "ImageRepositoryType": "ECR",
            "ImageConfiguration": {
                "Port": container_port,
                "RuntimeEnvironmentVariables": runtime_env_vars,
            },
        },
    }

    service_arn = get_service_arn(apprunner, service_name)

    try:
        if service_arn:
            print(f"Updating App Runner service: {service_name}")
            apprunner.update_service(
                ServiceArn=service_arn,
                SourceConfiguration=source_configuration,
            )
        else:
            print(f"Creating App Runner service: {service_name}")
            response = apprunner.create_service(
                ServiceName=service_name,
                SourceConfiguration=source_configuration,
            )
            service_arn = response["Service"]["ServiceArn"]

        describe = apprunner.describe_service(ServiceArn=service_arn)
        service_url = describe["Service"]["ServiceUrl"]
        status = describe["Service"]["Status"]

        print(f"Service ARN: {service_arn}")
        print(f"Service URL: https://{service_url}")
        print(f"Current status: {status}")
        print(f"SERVICE_URL=https://{service_url}")
        return 0
    except ClientError as exc:
        print(f"AWS API error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
