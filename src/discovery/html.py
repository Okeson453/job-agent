"""HTML parsing helpers.

selectolax 1.0 removed the ``selectolax.parser`` (Modest) backend and raises
ImportError on import. The project requires ``selectolax>=0.3.27``, so any
newer release resolves to 1.x in a fresh environment. Importing the lexbor
backend here keeps every discovery adapter on one supported parser.
"""

from __future__ import annotations

from selectolax.lexbor import LexborHTMLParser as HTMLParser

__all__ = ["HTMLParser"]
