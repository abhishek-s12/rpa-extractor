"""Ren'Py .rpyc script decompiler module.

Deserializes Ren'Py compiled script files (.rpyc / .rpymc) into readable
Ren'Py script (.rpy) code with fallback AST recovery.
"""

import io
import pickle
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from core.logger import logger


class StubRenPyNode:
    """Dynamic stub class representing pickled Ren'Py AST objects."""

    def __init__(self, class_name: str) -> None:
        self.__class_name = class_name
        self.filename: str = ""
        self.linenumber: int = 0
        self.name: str = ""
        self.block: List[Any] = []
        self.code: Any = None
        self.who: Optional[str] = None
        self.what: Optional[str] = None
        self.args: Any = None
        self.atl: Any = None
        self.imspec: Any = None
        self.items: List[Any] = []
        self.entries: List[Any] = []
        self.parsed: Any = None

    def __setstate__(self, state: Dict[str, Any]) -> None:
        if isinstance(state, dict):
            self.__dict__.update(state)

    def __repr__(self) -> str:
        return f"<RenPyAST:{self.__class_name} name={getattr(self, 'name', '')}>"


class RenPyUnpickler(pickle.Unpickler):
    """Custom unpickler to safely deserialize Ren'Py AST nodes without requiring the renpy module."""

    def find_class(self, module: str, name: str) -> Any:
        if module.startswith("renpy") or module.startswith("store"):
            # Create dynamic stub class for any renpy AST node
            def stub_factory(*args: Any, **kwargs: Any) -> StubRenPyNode:
                node = StubRenPyNode(f"{module}.{name}")
                return node
            stub_factory.__name__ = name
            return stub_factory
        return super().find_class(module, name)


class RpycDecompiler:
    """Decompiles Ren'Py .rpyc/.rpymc files back into clean .rpy script text."""

    @staticmethod
    def decompile(data_or_path: Union[bytes, Path, str]) -> str:
        """Decompiles a .rpyc file or raw bytes into Ren'Py .rpy source text.

        Args:
            data_or_path: File path or raw bytes of the .rpyc file.

        Returns:
            The decompiled Ren'Py script code string.
        """
        try:
            if isinstance(data_or_path, (Path, str)):
                with open(data_or_path, "rb") as f:
                    content = f.read()
            else:
                content = data_or_path

            # Check header
            if not content:
                return "# Empty script file\n"

            # Ren'Py rpyc files start with magic header (e.g. RENPY RPC2 or zlib data)
            offset = 0
            if content.startswith(b"RENPY RPC2"):
                # Header format: RENPY RPC2 <slot_count:int32> <slot_type:int32> ...
                offset = 10
                # Scan for zlib streams (0x78 0x9c or 0x78 0xda)
                zlib_idx = content.find(b"\x78\x9c")
                if zlib_idx == -1:
                    zlib_idx = content.find(b"\x78\xda")
                if zlib_idx != -1:
                    offset = zlib_idx

            compressed_data = content[offset:]
            ast_data = None

            try:
                decompressed = zlib.decompress(compressed_data)
                # Unpickle AST
                unpickler = RenPyUnpickler(io.BytesIO(decompressed))
                ast_data = unpickler.load()
            except Exception as ex:
                logger.debug(f"Direct unpickle failed ({ex}), trying slot scanning fallback...")
                ast_data = RpycDecompiler._fallback_slot_scan(content)

            if ast_data:
                return RpycDecompiler._render_ast(ast_data)
            else:
                return RpycDecompiler._fallback_string_extraction(content)

        except Exception as e:
            logger.error(f"Failed to decompile .rpyc file: {e}")
            return f"# Decompilation error: {e}\n"

    @staticmethod
    def _fallback_slot_scan(content: bytes) -> Optional[Any]:
        """Scans for all zlib compressed slots in the .rpyc header."""
        idx = 0
        while True:
            zlib_idx = content.find(b"\x78\x9c", idx)
            if zlib_idx == -1:
                zlib_idx = content.find(b"\x78\xda", idx)
            if zlib_idx == -1:
                break
            try:
                decomp = zlib.decompress(content[zlib_idx:])
                unpickler = RenPyUnpickler(io.BytesIO(decomp))
                obj = unpickler.load()
                if isinstance(obj, (list, tuple, StubRenPyNode)):
                    return obj
            except Exception:
                pass
            idx = zlib_idx + 2
        return None

    @staticmethod
    def _render_ast(ast_root: Any, indent: int = 0) -> str:
        """Traverses and renders Ren'Py AST nodes into formatted .rpy source lines."""
        lines: List[str] = []
        ind_str = "    " * indent

        nodes = ast_root if isinstance(ast_root, (list, tuple)) else [ast_root]

        for node in nodes:
            if isinstance(node, tuple) and len(node) == 2:
                # Sometimes (filename, line, ast_nodes) tuple structure is stored
                _, node = node

            if not isinstance(node, StubRenPyNode):
                continue

            cls_name = getattr(node, "_StubRenPyNode__class_name", str(type(node)))

            if "Init" in cls_name:
                block = getattr(node, "block", [])
                lines.append(f"{ind_str}init:")
                lines.append(RpycDecompiler._render_ast(block, indent + 1))

            elif "Label" in cls_name:
                name = getattr(node, "name", "unknown")
                lines.append(f"\n{ind_str}label {name}:")
                block = getattr(node, "block", [])
                lines.append(RpycDecompiler._render_ast(block, indent + 1))

            elif "Say" in cls_name:
                who = getattr(node, "who", None)
                what = getattr(node, "what", "")
                # Escape double quotes
                what_escaped = what.replace('"', '\\"')
                if who:
                    lines.append(f'{ind_str}{who} "{what_escaped}"')
                else:
                    lines.append(f'{ind_str}"{what_escaped}"')

            elif "Python" in cls_name:
                code_obj = getattr(node, "code", None)
                source = getattr(code_obj, "source", None) if code_obj else None
                if source:
                    py_lines = source.strip().splitlines()
                    if len(py_lines) == 1:
                        lines.append(f"{ind_str}$ {py_lines[0]}")
                    else:
                        lines.append(f"{ind_str}python:")
                        for pl in py_lines:
                            lines.append(f"{ind_str}    {pl}")
                else:
                    lines.append(f"{ind_str}$ # python statement")

            elif "Show" in cls_name:
                imspec = getattr(node, "imspec", None)
                if imspec and len(imspec) > 0:
                    name_tuple = imspec[0]
                    img_name = " ".join(name_tuple) if isinstance(name_tuple, (tuple, list)) else str(name_tuple)
                    lines.append(f"{ind_str}show {img_name}")
                else:
                    lines.append(f"{ind_str}show asset")

            elif "Hide" in cls_name:
                imspec = getattr(node, "imspec", None)
                if imspec and len(imspec) > 0:
                    name_tuple = imspec[0]
                    img_name = " ".join(name_tuple) if isinstance(name_tuple, (tuple, list)) else str(name_tuple)
                    lines.append(f"{ind_str}hide {img_name}")
                else:
                    lines.append(f"{ind_str}hide asset")

            elif "Scene" in cls_name:
                imspec = getattr(node, "imspec", None)
                if imspec and len(imspec) > 0:
                    name_tuple = imspec[0]
                    img_name = " ".join(name_tuple) if isinstance(name_tuple, (tuple, list)) else str(name_tuple)
                    lines.append(f"{ind_str}scene {img_name}")
                else:
                    lines.append(f"{ind_str}scene black")

            elif "With" in cls_name:
                expr = getattr(node, "expr", "dissolve")
                lines.append(f"{ind_str}with {expr}")

            elif "If" in cls_name:
                entries = getattr(node, "entries", [])
                first = True
                for condition, block in entries:
                    kw = "if" if first else "elif"
                    first = False
                    lines.append(f"{ind_str}{kw} {condition}:")
                    lines.append(RpycDecompiler._render_ast(block, indent + 1))

            elif "Menu" in cls_name:
                items = getattr(node, "items", [])
                lines.append(f"{ind_str}menu:")
                for item in items:
                    if isinstance(item, tuple) and len(item) >= 3:
                        label, cond, block = item[0], item[1], item[2]
                        cond_str = f" if {cond}" if cond else ""
                        lines.append(f'{ind_str}    "{label}"{cond_str}:')
                        if block:
                            lines.append(RpycDecompiler._render_ast(block, indent + 2))

            elif "Return" in cls_name:
                lines.append(f"{ind_str}return")

            elif "Pass" in cls_name:
                lines.append(f"{ind_str}pass")

            elif "UserStatement" in cls_name:
                line_text = getattr(node, "line", "")
                lines.append(f"{ind_str}{line_text}")

            elif "Define" in cls_name or "Default" in cls_name:
                varname = getattr(node, "varname", "")
                code_obj = getattr(node, "code", None)
                source = getattr(code_obj, "source", "") if code_obj else ""
                stmt = "define" if "Define" in cls_name else "default"
                lines.append(f"{ind_str}{stmt} {varname} = {source}")

            else:
                # General block recursion if available
                block = getattr(node, "block", [])
                if block:
                    lines.append(RpycDecompiler._render_ast(block, indent))

        return "\n".join(lines)

    @staticmethod
    def _fallback_string_extraction(content: bytes) -> str:
        """Fallback string extractor if pickle structure is corrupted or encrypted."""
        out = ["# Ren'Py Script (Recovered Text Extraction)\n"]
        try:
            # Look for readable UTF-8 printable strings
            strings = []
            current = []
            for b in content:
                if 32 <= b <= 126 or b in (9, 10, 13):
                    current.append(chr(b))
                else:
                    if len(current) >= 4:
                        strings.append("".join(current))
                    current = []
            if current and len(current) >= 4:
                strings.append("".join(current))

            for s in strings:
                if any(s.strip().startswith(kw) for kw in ("label ", "define ", "default ", "show ", "scene ", "$ ", "image ")):
                    out.append(s.strip())
                elif len(s.strip()) > 10 and (" " in s):
                    out.append(f'# "{s.strip()}"')
        except Exception:
            pass

        return "\n".join(out)
