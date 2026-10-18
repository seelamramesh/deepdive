"""Centralized Mesh API gateway. ALL LLM calls route through here."""

from __future__ import annotations

import json
import time
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.schemas import AgentCall, _hash


class MeshGateway:
    """Single gateway for all LLM inference via Mesh API."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._calls: list[AgentCall] = []

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not settings.mesh_api_key:
                raise RuntimeError(
                    "MESH_API_KEY not set. All LLM calls require Mesh API."
                )
            self._client = AsyncOpenAI(
                base_url=settings.mesh_base_url,
                api_key=settings.mesh_api_key,
            )
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(settings.mesh_api_key)

    async def complete(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0,
        response_format: dict[str, str] | None = None,
        prompt_version: str = "v1",
    ) -> dict[str, Any]:
        """Send a chat completion through Mesh API and return parsed JSON."""
        model = model or settings.mesh_model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        start = time.monotonic()
        response = await self.client.chat.completions.create(**kwargs)
        duration_ms = int((time.monotonic() - start) * 1000)

        content = response.choices[0].message.content or ""

        call = AgentCall(
            agent=agent_name,
            model=model,
            prompt_version=prompt_version,
            input_hash=_hash(system_prompt + user_prompt),
            output_hash=_hash(content),
            duration_ms=duration_ms,
        )
        self._calls.append(call)

        # Parse JSON from response
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                parsed = json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                parsed = json.loads(json_str)
            else:
                raise ValueError(
                    f"Agent {agent_name} returned non-JSON: {content[:200]}"
                )

        return parsed

    def drain_calls(self) -> list[AgentCall]:
        """Return and clear recorded agent calls."""
        calls = self._calls.copy()
        self._calls.clear()
        return calls

    async def health_check(self) -> bool:
        """Quick connectivity check against Mesh API."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False


# Module-level singleton
mesh = MeshGateway()
