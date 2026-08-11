# webmate Python SDK <img src="https://avatars.githubusercontent.com/u/13346605" alt="webmate logo" width="28"/> ![pypi](https://img.shields.io/pypi/v/webmate-sdk)

This directory contains a webmate Python SDK. 
`WebmateSession` aggregates service
clients for browser sessions, the job engine, device control, test management,
mail testing, artifacts, images, Selenium services, blob storage, and package
management.

## Quick start

```python
from webmate_sdk import AuthInfo, WebmateEnvironment, WebmateSession

session = WebmateSession(
    auth=AuthInfo(api_token="<token>", email="user@example.com"),
    environment=WebmateEnvironment(),
    project_id=None,  # set to ProjectId(...) if you work in a fixed project
)

# Query Selenium capabilities in the default project:
capabilities = session.selenium.get_capabilities()

# Trigger a job run:
from webmate_sdk.jobs import JobConfigName, PortName, WMValue, WMDataType

inputs = {
    PortName("vehicleSpec"): WMValue(WMDataType("LiveExpeditionSpec"), {"foo": "bar"}),
}
run_id = session.job_engine.start_job(
    JobConfigName("MyJob"),
    job_instance_name="Nightly",
    input_values=inputs,
)
```

Most client methods accept either the strongly typed identifier wrappers from
`webmate_sdk.ids` or plain strings/UUIDs.

> **Note:** Certain responses are returned as plain dictionaries instead of
> bespoke value objects. Extend or adapt the models to match your use cases.

## Requirements

- Python 3.9+
- `requests>=2.31` (installed automatically with the package)

## Install

Install the SDK in editable mode:

```bash
pip install webmate-sdk
```

## SDK tests

Run the SDK unit tests:

```bash
pytest tests -v
```
