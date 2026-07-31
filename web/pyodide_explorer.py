"""Pyodide WASM Asset Explorer Bridge.

Provides pure Python routines compatible with Pyodide / WebAssembly environment
for browser-based RPA archive header reading and search preset sync.
"""

import json
from typing import Any, Dict, List


def parse_rpa_header_wasm(header_bytes: bytes) -> Dict[str, Any]:
    """Parses RPA header bytes in Pyodide WASM context."""
    if not header_bytes:
        return {"valid": False, "version": "Unknown", "error": "Empty header"}

    try:
        header_str = header_bytes[:32].decode("utf-8", errors="ignore")
        if header_str.startswith("RPA-3.0"):
            parts = header_str.strip().split()
            return {
                "valid": True,
                "version": "RPA-3.0",
                "offset": parts[1] if len(parts) > 1 else "0",
                "key": parts[2] if len(parts) > 2 else "0",
            }
        elif header_str.startswith("RPA-2.0"):
            parts = header_str.strip().split()
            return {
                "valid": True,
                "version": "RPA-2.0",
                "offset": parts[1] if len(parts) > 1 else "0",
                "key": "None",
            }
        else:
            return {"valid": False, "version": "Unknown", "error": "Unsupported header signature"}
    except Exception as e:
        return {"valid": False, "version": "Unknown", "error": str(e)}


def filter_catalog_wasm(catalog_json: str, query: str) -> str:
    """Evaluates smart filter query against catalog in WASM context."""
    from core.smart_filter import SmartFilterEngine

    try:
        catalog = json.loads(catalog_json)
        asset_list = []
        for rel_path, data in catalog.items():
            item = dict(data)
            item["rel_path"] = rel_path
            item["name"] = rel_path.split("/")[-1]
            asset_list.append(item)

        filtered = SmartFilterEngine.filter_assets(asset_list, query)
        return json.dumps(filtered)
    except Exception as e:
        return json.dumps({"error": str(e)})
