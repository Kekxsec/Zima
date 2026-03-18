# backend/app/providers/content_analysis/bitcoin_finder/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_bitcoin.py (MIT licensed)
# Copyright (c) Steve Micallef.
import codecs
import re
from hashlib import sha256
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class BitcoinFinderProvider(BaseProviderClient):
    name = "bitcoin_finder"
    _pattern = re.compile(
        r"[\s:=\>](bc(0([ac-hj-np-z02-9]{39}|[ac-hj-np-z02-9]{59})|1[ac-hj-np-z02-9]{8,87})|[13][a-km-zA-HJ-NP-Z1-9]{25,35})"
    )

    async def find_bitcoin_addresses(
        self, *, address: str | None = None, content: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if address is not None:
            _inputs.append(("address", address))
        if content is not None:
            _inputs.append(("content", content))
        for _entity_type, _value in _inputs:
            if _entity_type != "web_content":
                continue
            content = _value
            if not content:
                continue
            matches = self._pattern.findall(content)
            addresses = []
            for match in matches:
                address = match[0]
                if address.startswith(("1", "3")):
                    if self._check_base58(address):
                        addresses.append(address)
                else:
                    addresses.append(address)

            uniq = sorted(set(addresses))
            for address in uniq:
                if address in seen:
                    continue
                seen.add(address)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="Bitcoin address found in content",
                        description="Potential Bitcoin wallet address identified in provided web content",
                        entity_type="bitcoin_address",
                        entity_value=address,
                        confidence=0.7,
                        tags=["content_analysis", "bitcoin", "passive"],
                    )
                )
            if uniq:
                evidence.append(
                    dict(
                        source=self.name,
                        description="Bitcoin wallet extraction from web content",
                        raw={"address_count": len(uniq)},
                        confidence=0.7,
                    )
                )

        return findings

    def _decode_base58(self, value: str, length: int) -> bytes:
        digits58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        n = 0
        for ch in value:
            n = n * 58 + digits58.index(ch)
        h = f"{n:x}"
        return codecs.decode(("0" * (len(h) % 2) + h).zfill(length * 2), "hex")

    def _check_base58(self, address: str) -> bool:
        try:
            bcbytes = self._decode_base58(address, 25)
        except Exception:
            return False
        return bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]
