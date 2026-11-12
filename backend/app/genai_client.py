"""One place that decides how the backend reaches Gemini.

- Production (Cloud Run): Vertex AI with the service account's identity.
  No secret exists anywhere.
- Local development before GCP is set up: the Gemini Developer API with a
  key in GEMINI_API_KEY (backend env only, never the app bundle). Same model
  family and embedding model, so retrieval results carry over.
"""

import os

from google import genai

# Gemma on Vertex is a MaaS endpoint ("-maas"); the Developer API names it
# without the suffix.
_DEV_API_ALIASES = {"gemma-4-26b-a4b-it-maas": "gemma-4-26b-a4b-it"}


def backend_name() -> str:
    return "developer-api" if os.environ.get("GEMINI_API_KEY") else "vertex"


def make_client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return genai.Client(api_key=key)
    return genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
    )


def wire_model_id(model_id: str) -> str:
    """The model name to send for the active backend."""
    if backend_name() == "developer-api":
        return _DEV_API_ALIASES.get(model_id, model_id)
    return model_id
