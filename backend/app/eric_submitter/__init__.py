"""
The `eric-submitter` worker: the ONLY process allowed to load the real
ERiC library (see docs/ELSTER_ERIC_INTEGRATION.md section 2). Deliberately
its own top-level package, sibling to `app.eric` rather than nested under
it, so it's obvious at a glance this is a separate deployable process
(its own container/entrypoint), not a module the FastAPI app imports.

Run it with `python -m app.eric_submitter.worker`.
"""
