import os
from typing import Any

import requests
import streamlit as st

DEFAULT_API_BASE_URL = "http://localhost:8000"


st.set_page_config(page_title="Word Count Client", page_icon=":page_facing_up:", layout="wide")
st.title("Word Count Frontend")
st.write("Upload one or more files. Each file is sent to the FastAPI backend for processing.")
st.caption("If this page loads, the frontend service is running.")

api_base_url = st.text_input(
    "API Base URL",
    value=os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL),
    help="Example: https://<your-api-service-url>",
)

with st.expander("Backend connection status", expanded=True):
    if api_base_url.strip():
        try:
            health_response = requests.get(f"{api_base_url.rstrip('/')}/health", timeout=10)
            if health_response.ok:
                st.success(f"Backend reachable at {api_base_url.rstrip('/')} (health: {health_response.status_code})")
            else:
                st.warning(
                    f"Backend responded with status {health_response.status_code} at {api_base_url.rstrip('/')}/health"
                )
        except Exception as exc:
            st.error(f"Could not reach backend health endpoint: {exc}")
    else:
        st.info("Enter an API Base URL to test backend connectivity.")

uploaded_files = st.file_uploader(
    "Upload files",
    type=["txt", "md", "csv", "log", "json", "xml", "yaml", "yml", "rtf", "pdf", "docx"],
    accept_multiple_files=True,
)


def call_word_count_api(base_url: str, uploaded_file: Any) -> dict:
    file_content = uploaded_file.getvalue()
    files = {
        "file": (
            uploaded_file.name,
            file_content,
            uploaded_file.type or "application/octet-stream",
        )
    }

    response = requests.post(f"{base_url.rstrip('/')}/api/v1/word-count", files=files, timeout=120)
    response.raise_for_status()
    payload = response.json()
    payload["size_bytes"] = len(file_content)
    return payload


if st.button("Count Words", type="primary"):
    if not uploaded_files:
        st.warning("Please upload at least one file.")
    elif not api_base_url.strip():
        st.warning("Please provide the API base URL.")
    else:
        successes = []
        failures = []

        for uploaded_file in uploaded_files:
            try:
                result = call_word_count_api(api_base_url, uploaded_file)
                successes.append(result)
            except requests.HTTPError as exc:
                detail = "Unknown backend error"
                try:
                    detail = exc.response.json().get("detail", detail)
                except Exception:
                    detail = exc.response.text or detail
                failures.append({"filename": uploaded_file.name, "error": detail})
            except Exception as exc:
                failures.append({"filename": uploaded_file.name, "error": str(exc)})

        if successes:
            st.subheader("Word Count Results")
            st.dataframe(successes, use_container_width=True)

        if failures:
            st.subheader("Files With Errors")
            st.dataframe(failures, use_container_width=True)

        st.success(
            f"Processed {len(uploaded_files)} files: {len(successes)} succeeded, {len(failures)} failed."
        )
