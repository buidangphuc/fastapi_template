"""Legacy DGL-compatible API surface.

Preserves the exact endpoints and response envelope of ``bds-genai-dgl`` so
existing callers (now fronted by the BFF) keep working unchanged while the
internals run on the new platform. See docs/adr/0001 (D1).

Phase 0 ships only the response envelope; routers are wired in later phases.
"""
