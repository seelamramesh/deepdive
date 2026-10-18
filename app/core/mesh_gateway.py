"""Centralized Mesh API gateway. ALL LLM calls route through here."""

from __future__ import annotations

import json
import re
import time
from contextvars import ContextVar
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.schemas import AgentCall, _hash


def _parse_json_object(content: str, agent_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", content, re.IGNORECASE)
        candidate = code_block.group(1).strip() if code_block else content.strip()
        starts = [index for index in (candidate.find("{"), candidate.find("[")) if index >= 0]
        if not starts:
            raise ValueError(f"Agent {agent_name} returned non-JSON: {content[:200]}")
        try:
            parsed, _ = json.JSONDecoder().raw_decode(candidate[min(starts):])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Agent {agent_name} returned invalid JSON: {content[:200]}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"Agent {agent_name} returned JSON {type(parsed).__name__}, expected object")
    return parsed


class MeshGateway:
    """Single gateway for all LLM inference via Mesh API."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._calls: ContextVar[tuple[AgentCall, ...]] = ContextVar("mesh_calls", default=())

    def _record_call(self, call: AgentCall) -> None:
        self._calls.set(self._calls.get() + (call,))

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

        kwargs["max_tokens"] = settings.mesh_max_output_tokens
        last_error: ValueError | None = None
        for _ in range(max(settings.mesh_json_attempts, 1)):
            start = time.monotonic()
            response = await self.client.chat.completions.create(**kwargs)
            duration_ms = int((time.monotonic() - start) * 1000)
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason or ""
            try:
                parsed = _parse_json_object(content, agent_name)
            except ValueError as exc:
                last_error = exc
                self._record_call(AgentCall(
                    agent=agent_name,
                    model=model,
                    prompt_version=prompt_version,
                    input_hash=_hash(system_prompt + user_prompt),
                    output_hash=_hash(content),
                    duration_ms=duration_ms,
                    success=False,
                    finish_reason=finish_reason,
                    error=str(exc),
                    response_preview=content[:300],
                ))
                continue
            self._record_call(AgentCall(
                agent=agent_name,
                model=model,
                prompt_version=prompt_version,
                input_hash=_hash(system_prompt + user_prompt),
                output_hash=_hash(content),
                duration_ms=duration_ms,
                finish_reason=finish_reason,
                response_preview=content[:300],
            ))
            return parsed

        raise ValueError(
            f"Agent {agent_name} failed JSON after {max(settings.mesh_json_attempts, 1)} attempts; "
            f"last error: {last_error}"
        ) from last_error

    def drain_calls(self) -> list[AgentCall]:
        """Return and clear recorded agent calls."""
        calls = list(self._calls.get())
        self._calls.set(())
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
