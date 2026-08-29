"""
ELSTER/ERiC submission integration — see docs/ELSTER_ERIC_INTEGRATION.md
for the full architecture this package implements.

Everything in this package that CAN be real without a BZSt (Bundeszentralamt
für Steuern) developer certificate and the actual ERiC shared library is
real: XML generation (`xml_builder.py`), the submission orchestration state
machine (`submission_service.py`), and a fully working `StubEricClient` used
for local development and tests. The one piece that genuinely cannot exist
without external credentials this project doesn't have — `NativeEricClient`
in `client.py`, the ctypes/cffi binding to the real `libericapi`/`eric.dll`
— is an explicit `NotImplementedError` stub with instructions for what
completing it requires, not a fake success path.

In production this package's `submission_service` is meant to run inside
its own isolated worker process/container (see the integration doc's
"crash isolation" rationale), not inside the main FastAPI web process —
it is scaffolded here in the same codebase for development convenience,
not because it should be deployed that way.
"""
