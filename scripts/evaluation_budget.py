"""Conservative evaluation-only request reservations; not a billing ledger."""
import json
from decimal import Decimal
from pathlib import Path


class EvaluationBudget:
    def __init__(self, path, cap="2.50"):
        self.path = Path(path)
        self.cap = Decimal(cap)
        if not self.cap.is_finite() or self.cap <= 0 or self.cap > Decimal("3"):
            raise ValueError("Evaluation cap must be positive and at most $3")
        self.entries = []
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if saved["cap_usd"] != str(self.cap):
                raise ValueError("Existing ledger has a different cap")
            self.entries = saved["reservations"]

    @property
    def reserved(self):
        return sum((Decimal(e["reserved_usd"]) for e in self.entries), Decimal("0"))

    def reserve(self, kind, amount):
        amount = Decimal(amount)
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Reservation must be finite and positive")
        if self.reserved + amount > self.cap:
            raise RuntimeError("Evaluation budget exhausted before sending request")
        self.entries.append({"kind": kind, "reserved_usd": str(amount)})
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"cap_usd": str(self.cap),
            "reserved_usd": str(self.reserved), "reservations": self.entries,
            "billing_verified": False}, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def reserve_mesh(self, kwargs):
        if kwargs.get("model") != "anthropic/claude-haiku-5.5":
            raise ValueError("Unpriced evaluation model")
        output = kwargs.get("max_tokens")
        if type(output) is not int or not 0 < output <= 4096:
            raise ValueError("Unbounded evaluation output")
        # UTF-8 bytes plus an 8,192-token overhead allowance. Twice the catalog's
        # long-context rates ($0.50 input/$2.50 output per million), no refunds.
        prompt_bound = len(json.dumps(kwargs["messages"], ensure_ascii=False).encode("utf-8")) + 8192
        self.reserve("mesh", (Decimal(prompt_bound) + Decimal(output)*5) / 1000000)

    def reserve_search(self):
        # Twice Brave's public $0.005/request rate; no free-credit assumption.
        self.reserve("brave", "0.01")
