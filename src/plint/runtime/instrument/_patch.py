"""Stub patch entry points; real instrumenters wired in below."""

from __future__ import annotations

_PATCHED: list[tuple[object, str, object]] = []
_PROVIDERS_INITIALIZED = False


def instrument() -> bool:
    """Monkey-patch installed provider SDKs to route through plint's tracer.

    Returns True if at least one provider was successfully patched.
    Safe to call multiple times — subsequent calls are no-ops while already instrumented.
    """

    global _PROVIDERS_INITIALIZED
    if _PROVIDERS_INITIALIZED:
        return True

    any_ok = False
    try:
        from plint.runtime.instrument.anthropic import patch_anthropic

        if patch_anthropic(_PATCHED):
            any_ok = True
    except Exception:
        pass
    try:
        from plint.runtime.instrument.openai import patch_openai

        if patch_openai(_PATCHED):
            any_ok = True
    except Exception:
        pass
    _PROVIDERS_INITIALIZED = any_ok
    return any_ok


def uninstrument() -> None:
    """Restore the original SDK methods. Safe to call when not instrumented."""

    global _PROVIDERS_INITIALIZED
    while _PATCHED:
        owner, attr, original = _PATCHED.pop()
        try:
            setattr(owner, attr, original)
        except Exception:
            pass
    _PROVIDERS_INITIALIZED = False
