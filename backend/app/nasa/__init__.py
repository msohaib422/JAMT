"""Live official NASA data integration for JAMT (Phase 2).

Two public sources, no API keys required:

* ``ntrs`` — NASA Technical Reports Server (ntrs.nasa.gov)
* ``pds``  — NASA Planetary Data System (pds.nasa.gov)

All endpoints degrade honestly: a source that cannot be reached returns
``available: false`` with a message, never fabricated data. Cached copies are
always labelled (``cached`` / ``stale`` / ``fetched_at``).
"""

from .ntrs import search_documents
from .pds import destination_datasets

__all__ = ["search_documents", "destination_datasets"]
