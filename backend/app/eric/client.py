"""
`EricClient` — the abstraction boundary between our code and the actual
ERiC library call. `submission_service.py` depends only on this interface,
never on whether it's talking to `StubEricClient` (local dev/tests, always
"succeeds", never touches a real Finanzamt) or `NativeEricClient` (the
real cffi binding to ericapi.dll/.so, see native_bindings.py).
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from app.eric import native_bindings


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
    """Abstraction over ERiC's validate-then-submit operations.

    `datenart_version` (e.g. `"ESt_2024"`) is the ERiC schema/plugin
    version the XML must match -- required by the real API
    (EricCheckXML/EricBearbeiteVorgang both reject a mismatch) but
    meaningless to StubEricClient, so it's optional here and each
    implementation decides whether to enforce it.
    """

    @abstractmethod
    def validate_xml(self, xml: str, datenart_version: str | None = None) -> None:
        """Raises EricValidationError if the XML fails plausibility checks."""

    @abstractmethod
    def submit(self, xml: str, datenart_version: str | None = None) -> EricSubmissionResult:
        """Transmits the XML and returns the Transferticket + outcome."""


class StubEricClient(EricClient):
    """Local-development / test double.

    Performs only cheap structural checks (the XML is well-formed and has
    the expected root element) and always "succeeds" with a synthetic
    Transferticket prefixed `STUB-` so it can never be confused with a
    real one. NEVER talks to the real Finanzamt -- this is the default
    client in `submission_service.py` until NativeEricClient is wired into
    a real deployment (see that class's docstring for why it isn't yet),
    so callers must not treat a StubEricClient success as a real
    submission outside of development/testing.
    """

    def validate_xml(self, xml: str, datenart_version: str | None = None) -> None:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as exc:
            raise EricValidationError(f"XML is not well-formed: {exc}") from exc

        if not root.tag.endswith("Elster"):
            raise EricValidationError(
                f"Expected root element 'Elster', got {root.tag!r}."
            )

    def submit(self, xml: str, datenart_version: str | None = None) -> EricSubmissionResult:
        self.validate_xml(xml)
        return EricSubmissionResult(transfer_ticket=f"STUB-{uuid.uuid4()}", accepted=True)


class NativeEricClient(EricClient):
    """Real ERiC integration via cffi bindings to ericapi.dll/.so
    (native_bindings.py), obtained through ELSTER Developer Area access --
    see docs/ELSTER_ERIC_INTEGRATION.md for how that access was acquired
    and what it does/doesn't unblock.

    Scope of what this class actually does, and doesn't, cover:

    - It only ever sends unauthenticated ("KOMPRIMIERT"/no-signature)
      submissions -- `cryptoParameter` is always NULL in the
      EricBearbeiteVorgang() call below. Authentication is per-taxpayer,
      not per-vendor (docs/ELSTER_ERIC_INTEGRATION.md section 6); a real
      personal-certificate path would need a `cryptoParameter` built from
      the taxpayer's own certificate, which this project doesn't support.
    - It never requests a PDF (`druckParameter` is always NULL) -- the
      KOMPRIMIERT paper cover sheet is generated separately by
      `cover_sheet.py`, not by ERiC's own print facility.
    - `xml_builder.py` maps most real E10 Anlagen now (verified against
      this exact class -- see docs/ELSTER_ERIC_INTEGRATION.md), but the
      Vorsatz block still needs `format_steuernummer_for_elster()` below
      called first and its result threaded in; without a `HerstellerID`
      and a filer's Finanzamt BuFa-Nummer, EricCheckXML()/
      EricBearbeiteVorgang() will still legitimately reject the XML --
      the honest, expected outcome of those still-open gaps, not a bug in
      this class.
    - Per docs/ELSTER_ERIC_INTEGRATION.md section 2, ericapi.dll/.so must
      never be loaded inside the main FastAPI web process (crash
      isolation, ERiC's yearly-versioned release cycle, ctypes/cffi memory
      safety) -- this class is deliberately NOT wired into
      `submission_service.py`'s default client. It's meant to be
      instantiated by a separate `eric-submitter` worker process once that
      exists; until then it's usable standalone (e.g. from a script) for
      integration testing against the real library.

    Lifecycle: `EricInitialisiere()` runs lazily on first use and once per
    instance; call `close()` (which runs `EricBeende()`) when done --
    typically once per worker process, not once per submission.
    """

    def __init__(self, sdk_path: str | Path, log_path: str | None = None) -> None:
        self._library = native_bindings.load(sdk_path)
        self._log_path = log_path
        self._initialized = False

    def close(self) -> None:
        """Runs EricBeende() -- must be called once, at process/worker
        shutdown, per the Init/Beende lifecycle EricBeende()'s own docs
        require ("als letztes muss EricBeende() aufgerufen werden")."""
        if self._initialized:
            self._library.lib.EricBeende()
            self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        ffi, lib = self._library.ffi, self._library.lib
        plugin_path = self._library.plugin_path.encode("utf-8")
        log_path = self._log_path.encode("utf-8") if self._log_path else ffi.NULL
        ret = lib.EricInitialisiere(plugin_path, log_path)
        if ret != native_bindings.ERIC_OK:
            raise EricSubmissionError(f"EricInitialisiere failed with ERiC code {ret}.")
        self._initialized = True

    def _new_buffer(self):
        handle = self._library.lib.EricRueckgabepufferErzeugen()
        if handle == self._library.ffi.NULL:
            raise EricSubmissionError("EricRueckgabepufferErzeugen returned NULL.")
        return handle

    def _read_buffer(self, handle) -> str:
        lib, ffi = self._library.lib, self._library.ffi
        length = lib.EricRueckgabepufferLaenge(handle)
        content = lib.EricRueckgabepufferInhalt(handle)
        if content == ffi.NULL:
            return ""
        return ffi.buffer(content, length)[:].decode("utf-8")

    def _error_text(self, code: int) -> str:
        handle = self._new_buffer()
        try:
            ret = self._library.lib.EricHoleFehlerText(code, handle)
            if ret != native_bindings.ERIC_OK:
                return f"ERiC error {code} (EricHoleFehlerText itself returned {ret})."
            return self._read_buffer(handle) or f"ERiC error {code} (no text available)."
        finally:
            self._library.lib.EricRueckgabepufferFreigeben(handle)

    @staticmethod
    def _require_datenart_version(datenart_version: str | None) -> str:
        if not datenart_version:
            raise ValueError(
                "NativeEricClient requires datenart_version (e.g. 'ESt_2024') -- "
                "ERiC rejects a mismatch between this and the XML payload."
            )
        return datenart_version

    def validate_xml(self, xml: str, datenart_version: str | None = None) -> None:
        version = self._require_datenart_version(datenart_version)
        self._ensure_initialized()
        lib = self._library.lib

        handle = self._new_buffer()
        try:
            ret = lib.EricCheckXML(xml.encode("utf-8"), version.encode("utf-8"), handle)
            if ret == native_bindings.ERIC_OK:
                return
            message = self._read_buffer(handle) or self._error_text(ret)
            raise EricValidationError(message)
        finally:
            lib.EricRueckgabepufferFreigeben(handle)

    def submit(self, xml: str, datenart_version: str | None = None) -> EricSubmissionResult:
        version = self._require_datenart_version(datenart_version)
        self._ensure_initialized()
        lib, ffi = self._library.lib, self._library.ffi

        rueckgabe_handle = self._new_buffer()
        serverantwort_handle = self._new_buffer()
        try:
            flags = native_bindings.ERIC_VALIDIERE | native_bindings.ERIC_SENDE
            ret = lib.EricBearbeiteVorgang(
                xml.encode("utf-8"),
                version.encode("utf-8"),
                flags,
                ffi.NULL,  # druckParameter -- no ERiC-generated PDF, see cover_sheet.py
                ffi.NULL,  # cryptoParameter -- unauthenticated KOMPRIMIERT send
                rueckgabe_handle,
                serverantwort_handle,
            )
            rueckgabe_xml = self._read_buffer(rueckgabe_handle)

            if ret == native_bindings.ERIC_OK:
                telenummer = self._extract_telenummer(rueckgabe_xml)
                return EricSubmissionResult(transfer_ticket=telenummer or "UNKNOWN", accepted=True)
            if ret == native_bindings.ERIC_GLOBAL_PRUEF_FEHLER:
                raise EricValidationError(rueckgabe_xml or self._error_text(ret))
            raise EricSubmissionError(self._error_text(ret))
        finally:
            lib.EricRueckgabepufferFreigeben(rueckgabe_handle)
            lib.EricRueckgabepufferFreigeben(serverantwort_handle)

    def format_steuernummer_for_elster(
        self,
        steuernummer: str,
        *,
        landesnr: str | None = None,
        bundesfinanzamtsnr: str | None = None,
    ) -> str:
        """Converts a regional Steuernummer (as printed on official
        letters, e.g. "191/815/08155") into ERiC's unified 13-digit
        format, via the real `EricMakeElsterStnr()` -- needed for the
        Vorsatz cover-sheet block's `StNr` field (see xml_builder.py's
        module docstring). At least one of `landesnr` (2-letter Bundesland
        code) or `bundesfinanzamtsnr` (4-digit BuFa-Nummer) is required by
        the real API; for Bavarian/Berlin Steuernummern in BBB/UUUUP
        format it REQUIRES `bundesfinanzamtsnr` specifically (its own docs
        are explicit about this), so prefer passing that when known.

        Raises:
            ValueError: if neither `landesnr` nor `bundesfinanzamtsnr` is given.
            EricValidationError: if ERiC rejects the Steuernummer/routing combination.
            EricSubmissionError: on any other ERiC error.
        """
        if not landesnr and not bundesfinanzamtsnr:
            raise ValueError(
                "format_steuernummer_for_elster requires landesnr or bundesfinanzamtsnr "
                "(or both) -- EricMakeElsterStnr rejects having neither."
            )
        self._ensure_initialized()
        lib, ffi = self._library.lib, self._library.ffi

        handle = self._new_buffer()
        try:
            ret = lib.EricMakeElsterStnr(
                steuernummer.encode("utf-8"),
                landesnr.encode("utf-8") if landesnr else ffi.NULL,
                bundesfinanzamtsnr.encode("utf-8") if bundesfinanzamtsnr else ffi.NULL,
                handle,
            )
            if ret == native_bindings.ERIC_OK:
                return self._read_buffer(handle)
            if ret == native_bindings.ERIC_GLOBAL_PRUEF_FEHLER:
                raise EricValidationError(self._read_buffer(handle) or self._error_text(ret))
            raise EricSubmissionError(self._error_text(ret))
        finally:
            lib.EricRueckgabepufferFreigeben(handle)

    @staticmethod
    def _extract_telenummer(rueckgabe_xml: str) -> str | None:
        """Pulls <Telenummer> out of the EricBearbeiteVorgang.xsd response
        (see API-Rueckgabe-Schemata/EricBearbeiteVorgang.xsd in the SDK)."""
        try:
            root = ET.fromstring(rueckgabe_xml)
        except ET.ParseError:
            return None
        for element in root.iter():
            if element.tag.endswith("Telenummer") and element.text:
                return element.text.strip()
        return None
