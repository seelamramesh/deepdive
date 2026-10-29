"""Explicit Mesh-only routing policies; labels are not quality benchmarks."""
import json
from pathlib import Path
from typing import Literal

ModelPreset = Literal["fast", "balanced", "quality", "configured"]
DEFAULT_PRESET = "balanced"
AGENT_TIER_MAP = {
    "planner": "medium", "search_strategist": "light", "researcher": "light",
    "source_critic": "light", "claim_drafter": "medium", "prosecutor": "heavy",
    "defense": "medium", "judge": "heavy", "contradiction_analyst": "light",
    "coverage_analyst": "medium", "synthesizer": "heavy", "report_verifier": "heavy",
}
MODEL_PRESETS = {
    "fast": {"label": "Fast (not benchmarked)", "description": "All roles use the lower catalog-rate model.",
             "models": {tier: "openai/gpt-4o-mini" for tier in ("heavy", "medium", "light")}},
    "balanced": {"label": "Balanced", "description": "Judge, prosecutor, synthesizer and report reviewer use the reasoning tier.",
                 "models": {"heavy": "openai/gpt-4o", "medium": "openai/gpt-4o-mini", "light": "openai/gpt-4o-mini"}},
    "quality": {"label": "Quality-oriented (not benchmarked)", "description": "All roles use the reasoning-tier model; accuracy is not guaranteed.",
                "models": {tier: "openai/gpt-4o" for tier in ("heavy", "medium", "light")}},
    "configured": {"label": "Configured model (legacy)", "description": "All roles use the deployment MESH_MODEL setting.", "models": {}},
}
CATALOG = json.loads(Path(__file__).with_name("model_catalog.json").read_text(encoding="utf-8"))


def resolve_model(preset: str | None, agent: str | None, explicit_model: str | None = None) -> str:
    from app.core.config import settings
    if preset is not None and preset not in MODEL_PRESETS:
        raise ValueError("Unknown model preset")
    if explicit_model:
        return explicit_model
    if preset is None or preset == "configured":
        return settings.mesh_model
    return MODEL_PRESETS[preset]["models"][AGENT_TIER_MAP.get(agent, "medium")]


def preset_catalog() -> dict:
    from app.core.config import settings
    rates = {m["id"]: m for m in CATALOG["models"]}
    presets = {}
    for key, config in MODEL_PRESETS.items():
        models = dict(config["models"]) if key != "configured" else {
            tier: settings.mesh_model for tier in ("heavy", "medium", "light")}
        presets[key] = {**config, "models": models,
                        "rates": {m: rates.get(m) for m in sorted(set(models.values()))},
                        "est_cost_per_run": None, "est_time": None, "quality_verified": False}
    return {"presets": presets, "default": DEFAULT_PRESET,
            "catalog_checked_at": CATALOG["checked_at"], "catalog_source": CATALOG["source"],
            "pricing_note": "Snapshot catalog USD per million tokens, not billed charges. Per-run cost and latency are not calibrated; no savings or quality guarantee."}
