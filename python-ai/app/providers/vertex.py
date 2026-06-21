"""Google Vertex AI provider (Gemini) — cost-optimized bulk classification path."""
from __future__ import annotations
import logging, os
logger = logging.getLogger(__name__)


class VertexProvider:
    def __init__(self) -> None:
        self._project = os.getenv("GCP_PROJECT")
        self._location = os.getenv("GCP_LOCATION", "us-central1")

    def is_available(self) -> bool:
        return bool(self._project)

    async def complete(self, prompt: str, system: str | None, model: str, max_tokens: int) -> dict:
        if not self.is_available():
            return {"text": "[stub] Gemini bulk classification: integration-service.",
                    "usage": {"input_tokens": 380, "output_tokens": 40},
                    "cost_usd": 0.0006, "provider": "vertex-stub", "model": model}
        # Real call path: vertexai.generative_models.GenerativeModel(...).generate_content(...)
        import vertexai
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=self._project, location=self._location)
        gm = GenerativeModel(model, system_instruction=system) if system else GenerativeModel(model)
        resp = gm.generate_content(prompt, generation_config={"max_output_tokens": max_tokens})
        meta = resp.usage_metadata
        return {"text": resp.text,
                "usage": {"input_tokens": meta.prompt_token_count,
                          "output_tokens": meta.candidates_token_count},
                "cost_usd": round(meta.prompt_token_count/1000*0.00015 +
                                  meta.candidates_token_count/1000*0.0006, 6),
                "provider": "vertex", "model": model}
