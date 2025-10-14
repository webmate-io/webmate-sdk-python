# webmate Python SDK (preview)

This directory contains an experimental Python port of the webmate Java SDK.
The package mirrors the Java structure: a `WebmateSession` aggregates service
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

> **Note:** The port emphasises idiomatic Python while staying close to the Java
> structure. Certain responses are returned as plain dictionaries instead of
> bespoke value objects. Extend or adapt the models to match your use cases.
