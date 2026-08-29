"""
`EricClient` — the abstraction boundary between our code and the actual
ERiC library call. `submission_service.py` depends only on this interface,
never on whether it's talking to `StubEricClient` (local dev/tests, always
"succeeds", never touches a real Finanzamt) or `NativeEricClient` (the
real integration — currently an explicit NotImplementedError, see its
docstring for why).
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass


class EricValidationError(Exception):
    """Raised when ERiC's plausibility check (EricCheckXML equivalent)
    rejects the XML."""


class EricSubmissionError(Exception):
    """Raised when the transmission itself (EricBearbeiteVorgang
    equivalent) fails -- as opposed to a validation rejection."""


@dataclass(frozen=True)
class EricSubmissionResult:
    transfer_ticket: str
    accepted: bool
    rejection_reason: str | None = None


class EricClient(ABC):
    """Abstraction over ERiC's validate-then-submit operations."""

    @abstractmethod
    def validate_xml(self, xml: str) -> None:
        """Raises EricValidationError if the XML fails plausibility checks."""

    @abstractmethod
    def submit(self, xml: str) -> EricSubmissionResult:
        """Transmits the XML and returns the Transferticket + outcome."""


class StubEricClient(EricClient):
    """Local-development / test double.

    Performs only cheap structural checks (the XML is well-formed and has
    the expected root element) and always "succeeds" with a synthetic
    Transferticket prefixed `STUB-` so it can never be confused with a
    real one. NEVER talks to the real Finanzamt — this is the default
    client until a NativeEricClient is actually implemented, and using it
    in production would silently "accept" every filing without ever
    really submitting it, so callers must not treat a StubEricClient
    success as a real submission outside of development/testing.
    """

    def validate_xml(self, xml: str) -> None:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as exc:
            raise EricValidationError(f"XML is not well-formed: {exc}") from exc

        if not root.tag.endswith("Elster"):
            raise EricValidationError(
                f"Expected root element 'Elster', got {root.tag!r}."
            )

    def submit(self, xml: str) -> EricSubmissionResult:
        self.validate_xml(xml)
        return EricSubmissionResult(transfer_ticket=f"STUB-{uuid.uuid4()}", accepted=True)


class NativeEricClient(EricClient):
    """*** NOT IMPLEMENTED ***

    This is where the real ctypes/cffi binding to the ERiC shared library
    (`libericapi.so`/`.dylib` or `eric.dll`) belongs. Building it requires,
    in order:

      1. A signed ERiC software-developer agreement with the BZSt
         (Bundeszentralamt für Steuern) — this is the actual blocker;
         nothing below is possible without it.
      2. The ERiC SDK itself (library binary + header/type definitions),
         which BZSt only distributes to registered developers.
      3. A registered Herstellernummer (vendor id) and Softwarezertifikat
         (organization certificate) — see
         docs/ELSTER_ERIC_INTEGRATION.md's security section for how the
         certificate must be stored (secrets manager, never on disk in
         the container image).

    Implementation sketch once those are available (cffi preferred over
    raw ctypes for ERiC's large C API surface — cleaner struct marshaling):
      - `EricInitialisiere()` once per worker process at startup.
      - `validate_xml()` -> `EricCheckXML(...)`, mapping ERiC's returned
        error codes back onto our field-level validation vocabulary.
      - `submit()` -> `EricBearbeiteVorgang(...)`, parsing the returned
        Transferticket/Rueckgabecode into an EricSubmissionResult.
      - `EricBeende()` at worker shutdown.

    Every method below raises immediately rather than pretending to work,
    so a misconfiguration that accidentally selects this client fails
    loudly instead of silently no-op-succeeding like StubEricClient would.
    """

    _NOT_IMPLEMENTED_MESSAGE = (
        "NativeEricClient requires the real ERiC library and a BZSt developer "
        "certificate, neither of which this project has yet -- see this "
        "class's docstring for what's needed before it can be implemented."
    )

    def validate_xml(self, xml: str) -> None:
        raise NotImplementedError(self._NOT_IMPLEMENTED_MESSAGE)

    def submit(self, xml: str) -> EricSubmissionResult:
        raise NotImplementedError(self._NOT_IMPLEMENTED_MESSAGE)
