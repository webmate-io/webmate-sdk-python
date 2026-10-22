# Changelog

All notable changes to the webmate Python SDK will be documented in this file.

## [Unreleased]
### New Features
- `DeviceClient.install_app` accepts `wait=True` (with optional `timeout_seconds` / `poll_interval`) to block until the device reports the app as installed, and returns the id of the installed package
- New method `DeviceClient.wait_for_installed_package` that waits until a device reports a package as installed; it raises `WebmateApiError` if the installation failed and `WebmateTimeoutError` if it does not finish in time. With `installation_id` it only considers that installation (`install_app(wait=True)` uses this, so a previous installation of the same package is not mistaken for the requested one)
### Bug Fixes
- `DeviceClient.install_app` now installs the concrete package behind the given package id (`origPackageId`, or `instrumentedPackageId` if `instrumented=True`) instead of writing the package document id into the requirement, which the device could not install. The package type is taken from the package unless `package_type` is given.

## [0.1.2] - 2026-09-09
### New Features
- `DeviceClient.request_device` accepts an optional `use_deployed` flag, passed through to the API as a query parameter

## [0.1.1] - 2026-08-11
### New Features
- New method `packages.getPackagesForProject` that allows to query complete info for all packages of a given Project

## [0.1.0] - 2026-02-27
Initial Release