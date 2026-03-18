#!/usr/bin/env python3
"""
Phase 2 Provider Migration: Remove ProviderInput/EntityType references.
Replaces with plain typed Python parameters.
"""

from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = REPO / "backend" / "app" / "providers"
BASE_DIR = PROVIDERS_DIR / "base"

# EntityType enum name → (param_name, string_literal)
ENTITY_MAP: dict[str, tuple[str, str]] = {
    "EMAIL": ("email", "email"),
    "DOMAIN": ("domain", "domain"),
    "HOSTNAME": ("domain", "hostname"),
    "IP_ADDRESS": ("ip_address", "ip_address"),
    "NETBLOCK": ("ip_address", "netblock"),
    "USERNAME": ("username", "username"),
    "PHONE": ("phone_number", "phone"),
    "URL": ("url", "url"),
    "HASH": ("hash_value", "hash"),
    "HUMAN_NAME": ("name", "human_name"),
    "WEB_CONTENT": ("content", "web_content"),
    "BINARY_CONTENT": ("content", "binary_content"),
    "BITCOIN_ADDRESS": ("address", "bitcoin_address"),
    "ETHEREUM_ADDRESS": ("address", "ethereum_address"),
    "PHYSICAL_ADDRESS": ("address", "physical_address"),
    "BGP_ASN": ("asn", "bgp_asn"),
    "BSSID": ("bssid", "bssid"),
    "SSID": ("ssid", "ssid"),
    "WIFI_NETWORK": ("wifi_network", "wifi_network"),
}


def get_entity_types(content: str) -> list[str]:
    return sorted(set(re.findall(r"EntityType\.(\w+)\.value", content)))


def get_params(entity_types: list[str]) -> OrderedDict[str, list[str]]:
    params: OrderedDict[str, list[str]] = OrderedDict()
    for et in entity_types:
        if et in ENTITY_MAP:
            pname, _ = ENTITY_MAP[et]
            params.setdefault(pname, []).append(et)
    return params


def replace_entity_type_values(content: str) -> str:
    def _repl(m: re.Match[str]) -> str:
        et = m.group(1)
        if et in ENTITY_MAP:
            _, sv = ENTITY_MAP[et]
            return f'"{sv}"'
        return m.group(0)

    return re.sub(r"EntityType\.(\w+)\.value", _repl, content)


def replace_options(content: str) -> str:
    content = re.sub(
        r"(?:provider_input|p)\.options\.get\(\s*[\"'][^\"']+[\"']\s*,\s*([^)]+?)\s*\)",
        r"\1",
        content,
    )
    return content


def remove_supports_method(lines: list[str]) -> list[str]:
    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if re.match(r"\s+def supports\(self", line):
            method_indent = indent
            i += 1
            while i < len(lines):
                nl = lines[i]
                ns = nl.lstrip()
                ni = len(nl) - len(ns)
                if not ns:
                    i += 1
                    continue
                if ni <= method_indent:
                    break
                i += 1
            continue
        new_lines.append(line)
        i += 1
    return new_lines


def fix_execute_signature(content: str, params: OrderedDict[str, list[str]]) -> str:
    if not params:
        new_sig = "async def execute(self) -> list[dict[str, Any]]:"
    elif len(params) == 1:
        pname = list(params.keys())[0]
        new_sig = f"async def execute(self, {pname}: str) -> list[dict[str, Any]]:"
    else:
        parts = [f"{pname}: str | None = None" for pname in params]
        new_sig = (
            f"async def execute(self, *, {', '.join(parts)}) -> list[dict[str, Any]]:"
        )
    content = re.sub(
        r"async def execute\(self\s*,\s*(?:provider_input|p)\s*:\s*ProviderInput\)\s*->\s*list\[dict\[str,\s*Any\]\]\s*:",
        new_sig,
        content,
    )
    return content


def process_entity_loop_single(
    lines: list[str], param_name: str, entity_types: list[str]
) -> list[str]:
    """Single-param: remove entity loop, dedent body, replace entity refs."""
    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Detect entity loop
        if re.match(
            r"\s+for\s+(?:entity|e)\s+in\s+(?:provider_input|p)\.entities\s*:", line
        ):
            loop_indent = indent
            body_indent = loop_indent + 4
            body: list[str] = []
            j = i + 1
            while j < len(lines):
                nl = lines[j]
                ns = nl.lstrip()
                ni = len(nl) - len(ns)
                if ns and ni <= loop_indent:
                    break
                body.append(nl)
                j += 1

            # Find type guard at start
            guard_end = 0
            for k, bl in enumerate(body):
                bs = bl.lstrip()
                if not bs or bs.startswith("#"):
                    guard_end = k + 1
                    continue
                if re.match(r"if\s+(?:entity|e)\.entity_type\s*(?:!=|not in)\s*", bs):
                    for kk in range(k + 1, min(k + 4, len(body))):
                        if body[kk].lstrip() == "continue":
                            guard_end = kk + 1
                            break
                    break
                break

            remaining = body[guard_end:]
            for bl in remaining:
                if bl.strip():
                    if bl.startswith(" " * body_indent):
                        bl = " " * loop_indent + bl[body_indent:]
                bl = re.sub(r"\b(?:entity|e)\.value\b", param_name, bl)
                if entity_types and entity_types[0] in ENTITY_MAP:
                    _, sv = ENTITY_MAP[entity_types[0]]
                    bl = re.sub(r"\b(?:entity|e)\.entity_type\b", f'"{sv}"', bl)
                new_lines.append(bl)
            i = j
            continue

        new_lines.append(line)
        i += 1
    return new_lines


def process_entity_loop_multi(
    lines: list[str], params: OrderedDict[str, list[str]]
) -> list[str]:
    """Multi-param: convert entity loop to _inputs iteration."""
    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        if re.match(
            r"\s+for\s+(?:entity|e)\s+in\s+(?:provider_input|p)\.entities\s*:", line
        ):
            indent = len(line) - len(stripped)
            s = " " * indent
            new_lines.append(f"{s}_inputs: list[tuple[str, str]] = []")
            for pname in params:
                new_lines.append(f"{s}if {pname} is not None:")
                new_lines.append(f'{s}    _inputs.append(("{pname}", {pname}))')
            new_lines.append(f"{s}for _entity_type, _value in _inputs:")
            i += 1
            continue

        line = re.sub(r"\b(?:entity|e)\.value\b", "_value", line)
        line = re.sub(r"\b(?:entity|e)\.entity_type\b", "_entity_type", line)
        new_lines.append(line)
        i += 1
    return new_lines


def fix_helper_signatures(content: str) -> str:
    content = re.sub(r",\s*provider_input\s*:\s*ProviderInput", "", content)
    content = re.sub(r",\s*p\s*:\s*ProviderInput", "", content)
    content = re.sub(r",\s*provider_input\b(?!\s*[.\[])", "", content)
    return content


def fix_leftover_types(content: str) -> str:
    content = re.sub(r":\s*List\[FindingRecord\]", ": list[dict[str, Any]]", content)
    content = re.sub(r":\s*List\[EvidenceRecord\]", ": list[dict[str, Any]]", content)
    return content


def clean_blanks(content: str) -> str:
    return re.sub(r"\n{4,}", "\n\n\n", content)


def migrate_file(filepath: Path) -> tuple[str, list[str]]:
    content = filepath.read_text()
    warnings: list[str] = []
    entity_types = get_entity_types(content)

    if not entity_types:
        if "ProviderInput" in content:
            warnings.append(
                f"{filepath.relative_to(REPO)}: ProviderInput but no EntityType"
            )
        return content, warnings

    params = get_params(entity_types)
    unknown = [et for et in entity_types if et not in ENTITY_MAP]
    if unknown:
        warnings.append(
            f"{filepath.relative_to(REPO)}: unknown EntityType(s): {unknown}"
        )

    is_single = len(params) == 1

    # Text-level transforms
    content = replace_entity_type_values(content)
    content = replace_options(content)
    content = fix_execute_signature(content, params)
    content = fix_helper_signatures(content)
    content = fix_leftover_types(content)

    # Line-level transforms
    lines = content.split("\n")
    lines = remove_supports_method(lines)
    if is_single:
        param_name = list(params.keys())[0]
        lines = process_entity_loop_single(lines, param_name, entity_types)
    else:
        lines = process_entity_loop_multi(lines, params)

    content = "\n".join(lines)
    content = clean_blanks(content)
    return content, warnings


def main() -> None:
    if not PROVIDERS_DIR.exists():
        print(f"ERROR: {PROVIDERS_DIR} not found")
        sys.exit(1)

    client_files = sorted(
        f
        for f in PROVIDERS_DIR.rglob("*/client.py")
        if not str(f).startswith(str(BASE_DIR))
    )
    print(f"Found {len(client_files)} provider client.py files")

    all_warnings: list[str] = []
    migrated = 0
    unchanged = 0

    for fp in client_files:
        try:
            new_content, warnings = migrate_file(fp)
            all_warnings.extend(warnings)
            if new_content != fp.read_text():
                fp.write_text(new_content)
                migrated += 1
            else:
                unchanged += 1
        except Exception as exc:
            all_warnings.append(f"{fp.relative_to(REPO)}: ERROR: {exc}")

    print(f"Migrated: {migrated}")
    print(f"Unchanged: {unchanged}")
    if all_warnings:
        print(f"\nWarnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  {w}")
    else:
        print("No warnings.")


if __name__ == "__main__":
    main()
