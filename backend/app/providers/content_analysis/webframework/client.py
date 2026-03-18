# backend/app/providers/content_analysis/webframework/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_webframework.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

_FRAMEWORKS = [
    ("React", re.compile(r"react(?:\.min)?\.js|__REACT_DEVTOOLS|react-dom", re.I)),
    ("Vue.js", re.compile(r"vue(?:\.min)?\.js|new Vue\s*\(|createApp\s*\(", re.I)),
    (
        "Angular",
        re.compile(r"angular(?:\.min)?\.js|ng-app=|ng-controller=|@angular/core", re.I),
    ),
    ("jQuery", re.compile(r"jquery(?:\.min)?\.js|\$\.ajax\s*\(|jQuery\.fn\.", re.I)),
    (
        "Bootstrap",
        re.compile(
            r"bootstrap(?:\.min)?\.(?:css|js)|class=[\"'][^\"']*(?:container|navbar|btn-)",
            re.I,
        ),
    ),
    (
        "Backbone.js",
        re.compile(r"backbone(?:\.min)?\.js|Backbone\.Model\.extend", re.I),
    ),
    ("Ember.js", re.compile(r"ember(?:\.min)?\.js|App\.ApplicationRoute", re.I)),
    ("Next.js", re.compile(r"__NEXT_DATA__|_next/static", re.I)),
    ("Nuxt.js", re.compile(r"__NUXT__|_nuxt/", re.I)),
    ("Django", re.compile(r"csrfmiddlewaretoken|__django_session", re.I)),
    (
        "Rails",
        re.compile(r"authenticity_token.*rails|csrf-param.*authenticity_token", re.I),
    ),
    ("Laravel", re.compile(r"laravel_session|csrf-token.*[A-Za-z0-9+/=]{40}", re.I)),
    ("WordPress", re.compile(r"wp-content/|wp-includes/|/wp-json/", re.I)),
    ("Drupal", re.compile(r"Drupal\.settings|sites/default/files", re.I)),
    ("Joomla", re.compile(r"/components/com_|/modules/mod_", re.I)),
]


from backend.app.providers.base.client import BaseProviderClient


class WebframeworkProvider(BaseProviderClient):
    name = "webframework"

    async def detect_framework(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        if not content:
            return findings
        for label, pattern in _FRAMEWORKS:
            if label in seen:
                continue
            if pattern.search(content):
                seen.add(label)
                findings.append(
                    dict(
                        provider=self.name,
                        category="technology_fingerprint",
                        title=f"Web framework detected: {label}",
                        description=f"{label} framework signature found in page content",
                        entity_type="web_content",
                        entity_value=label,
                        confidence=0.75,
                        tags=[
                            "content_analysis",
                            "webframework",
                            "fingerprint",
                            "passive",
                        ],
                    )
                )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Web frameworks identified in content",
                    raw={"frameworks": list(seen)},
                    confidence=0.75,
                )
            )

        return findings
