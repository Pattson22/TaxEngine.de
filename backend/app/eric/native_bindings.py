"""
cffi bindings to the real ERiC C API (ericapi.dll / libericapi.so).

Every signature below is copied verbatim from the ERiC 44.2.4.1 SDK's own
`include/ericapi.h` and `include/eric_types.h` (obtained via ELSTER
Developer Area access, see docs/ELSTER_ERIC_INTEGRATION.md) -- not guessed
or reconstructed from prose documentation. Only the subset of ERiC's much
larger API surface this project actually calls is declared here: process
lifecycle, buffer management, schema validation, and the unauthenticated
("KOMPRIMIERT"/no-signature) submission path described in
docs/ELSTER_ERIC_INTEGRATION.md section 6. Certificate handling, the
Multithreading API, Otto/data-retrieval, and everything else ERiC exposes
is out of scope until this project supports per-taxpayer certificates.

`eric_druck_parameter_t` and `eric_verschluesselungs_parameter_t` are
declared as opaque (incomplete) struct types: this project's KOMPRIMIERT
flow always passes NULL for both (no PDF-print parameter, no
authenticated-transmission parameter -- see EricBearbeiteVorgang's
documented parameter semantics), so their real field layouts are never
needed and are not guessed at here.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

import cffi

_CDEF = """
typedef struct EricReturnBufferApi* EricRueckgabepufferHandle;
typedef struct eric_druck_parameter_t eric_druck_parameter_t;
typedef struct eric_verschluesselungs_parameter_t eric_verschluesselungs_parameter_t;

int EricInitialisiere(const char *pluginPfad, const char *logPfad);
int EricBeende(void);

int EricCheckXML(const char *xml, const char *datenartVersion,
                  EricRueckgabepufferHandle fehlertextPuffer);

int EricBearbeiteVorgang(const char *datenpuffer, const char *datenartVersion,
                          uint32_t bearbeitungsFlags,
                          const eric_druck_parameter_t *druckParameter,
                          const eric_verschluesselungs_parameter_t *cryptoParameter,
                          EricRueckgabepufferHandle rueckgabeXmlPuffer,
                          EricRueckgabepufferHandle serverantwortXmlPuffer);

EricRueckgabepufferHandle EricRueckgabepufferErzeugen(void);
int EricRueckgabepufferFreigeben(EricRueckgabepufferHandle handle);
const char *EricRueckgabepufferInhalt(EricRueckgabepufferHandle handle);
uint32_t EricRueckgabepufferLaenge(EricRueckgabepufferHandle handle);

int EricHoleFehlerText(int fehlerkode, EricRueckgabepufferHandle rueckgabePuffer);
"""

# eric_bearbeitung_flag_t (eric_types.h) -- OR'd into EricBearbeiteVorgang's
# bearbeitungsFlags. Only the values this project's KOMPRIMIERT flow uses;
# ERIC_DRUCKE (PDF output) is deliberately omitted -- see cover_sheet.py's
# module docstring for why the official BZSt printout isn't produced here.
ERIC_VALIDIERE = 1 << 1
ERIC_SENDE = 1 << 2
ERIC_PRUEFE_HINWEISE = 1 << 7

# eric_fehlercode enum (eric_fehlercodes.h) -- only the codes this project's
# client.py branches on; EricHoleFehlerText() covers everything else.
ERIC_OK = 0
ERIC_GLOBAL_UNKNOWN = 610001001
ERIC_GLOBAL_PRUEF_FEHLER = 610001002
ERIC_GLOBAL_HINWEISE = 610001003


class EricLibraryNotFoundError(RuntimeError):
    """Raised when the ERiC shared library can't be located under sdk_path."""


def _platform_layout() -> tuple[str, str]:
    """Returns (library path relative to sdk_path, plugin dir relative to
    sdk_path) for the running OS.

    Verified against the actual downloaded SDK archives (each
    `ERiC-<version>-<Platform>.jar` is a zip): Windows ships
    `dll/ericapi.dll` + `dll/plugins/`, Linux ships `lib/libericapi.so` +
    `lib/plugins/`. `sdk_path` is expected to point at one platform's
    extracted `ERiC-<version>/<Platform>/` directory (e.g.
    `ERiC-44.2.4.0/Windows-x86_64/`), not the archive root.
    """
    system = platform.system()
    if system == "Windows":
        return "dll/ericapi.dll", "dll/plugins"
    if system == "Linux":
        return "lib/libericapi.so", "lib/plugins"
    if system == "Darwin":
        return "lib/libericapi.dylib", "lib/plugins"
    raise EricLibraryNotFoundError(f"No known ERiC SDK layout for platform {system!r}.")


@dataclass(frozen=True)
class EricLibrary:
    """A loaded ericapi library plus the cffi FFI it was declared against
    (needed to build C strings/buffers for calls) and the plugin directory
    EricInitialisiere() should be pointed at."""

    ffi: cffi.FFI
    lib: object
    plugin_path: str


def load(sdk_path: str | Path) -> EricLibrary:
    """Loads ericapi.dll/.so from `sdk_path` (one platform's extracted SDK
    directory, see `_platform_layout`'s docstring). Raises
    EricLibraryNotFoundError if it isn't there -- never falls back to
    silently pretending the library loaded."""
    root = Path(sdk_path)
    lib_rel, plugins_rel = _platform_layout()
    lib_path = root / lib_rel
    if not lib_path.is_file():
        raise EricLibraryNotFoundError(
            f"ERiC library not found at {lib_path}. sdk_path must point at "
            f"one platform's extracted SDK directory (the contents of "
            f"ERiC-<version>-<Platform>.jar, which is itself a zip archive) "
            f"-- see docs/ELSTER_ERIC_INTEGRATION.md."
        )

    ffi = cffi.FFI()
    ffi.cdef(_CDEF)
    lib = ffi.dlopen(str(lib_path))
    return EricLibrary(ffi=ffi, lib=lib, plugin_path=str(root / plugins_rel))
