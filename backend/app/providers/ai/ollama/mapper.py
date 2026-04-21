# backend/app/providers/ai/ollama/mapper.py
from backend.app.providers.ai.ollama.schemas import OllamaAccountInterpretation
from backend.app.providers.base.models import ProviderFinding


def to_provider_finding(result: OllamaAccountInterpretation) -> ProviderFinding:
    finding: ProviderFinding = {
        "title": result["display_name"],
        "tags": ["ai:account_interpretation"],
        "raw": {
            "service_name": result["service_name"],
            "confidence": result["confidence"],
        },
    }
    reason = result.get("reason")
    if reason:
        finding["description"] = reason
    return finding
