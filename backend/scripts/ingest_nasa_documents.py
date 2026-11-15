#!/usr/bin/env python3
"""Fetch the official NASA publications listed in the manifest and rebuild
the JAMT knowledge base (``app/ai/data/nasa_knowledge.json``).

Usage:

    python scripts/ingest_nasa_documents.py            # uses cached downloads
    python scripts/ingest_nasa_documents.py --force    # re-download everything
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.nasa_corpus import build_dataset, write_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download every document, ignoring the cache")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--output", default=None, help="write the dataset to this path instead of the default")
    args = parser.parse_args()

    result = build_dataset(timeout=args.timeout, force=args.force)
    for item in result["documents"]:
        print(
            f"[ok] {item['key']:14s} {item['ntrs_id']} "
            f"({'cache' if item['source'] == 'cache' else 'network'}, {item['bytes']:>8} bytes) "
            f"-> {item['extracted_chunks']} chunks"
        )
    for failure in result["failures"]:
        print(f"[   ] {failure['key']:14s} FAILED: {failure['error']}")

    if result["failures"]:
        print(f"\n{len(result['failures'])} document(s) failed to download. The dataset will be written without them.")

    if args.output:
        from pathlib import Path
        target = Path(args.output)
        write_dataset(result["chunks"], target)
    else:
        write_dataset(result["chunks"])

    print(
        f"\nDocuments indexed: {len(result['documents'])}/{result['manifest_size']}  |  "
        f"chunks: {result['total_chunks']}  |  retrieved: {result['retrieved']}"
    )


if __name__ == "__main__":
    main()
