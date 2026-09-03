"""
ELSTER/ERiC submission integration — see docs/ELSTER_ERIC_INTEGRATION.md
for the full architecture this package implements.

XML generation (`xml_builder.py`), the submission orchestration state
machine (`submission_service.py`), `StubEricClient` (used for local
development and tests), and `NativeEricClient` (the cffi binding to the
real `ericapi.dll`/`.so`, using a registered `HerstellerID`) are all real
and verified against the actual ERiC library.

`NativeEricClient` is only ever instantiated inside the separate
`eric_submitter` worker process (`app/eric_submitter/worker.py`), never
inside the main FastAPI web process — see the integration doc's "crash
isolation" rationale.
"""
