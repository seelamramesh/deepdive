"""Conservative evaluation-only request reservations; not a billing ledger."""
import json
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone


class EvaluationBudget:
    def __init__(self, path, cap=None):
        self.path = Path(path)
        saved = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.cap = Decimal(cap if cap is not None else saved.get("cap_usd", "2.50"))
        if not self.cap.is_finite() or self.cap <= 0 or self.cap > Decimal("4"):
            raise ValueError("Evaluation reservation cap must be positive and at most $4")
        if saved and Decimal(saved["cap_usd"]) != self.cap:
            raise ValueError("Existing ledger has a different cap")
        self.entries = saved.get("reservations", [])
        self.metadata = {k:v for k,v in saved.items() if k not in {"reservations","reserved_usd","cap_usd"}}

    def _write(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({**self.metadata,"cap_usd":str(self.cap),
            "reserved_usd":str(self.reserved),"reservations":self.entries,
            "billing_verified":False},indent=2),encoding="utf-8")
        temporary.replace(self.path)

    def increase_cap(self, new_cap, authorized_total):
        """Call only after explicit human authorization, while holding the process lock."""
        new_cap, total = Decimal(new_cap), Decimal(authorized_total)
        if (not new_cap.is_finite() or not total.is_finite() or
                total > Decimal("4") or new_cap > total or new_cap <= self.cap):
            raise ValueError("Invalid authorized cap increase")
        self.metadata.setdefault("cap_changes",[]).append({"old_cap_usd":str(self.cap),
            "new_cap_usd":str(new_cap),"authorized_total_usd":str(total),
            "timestamp":datetime.now(timezone.utc).isoformat(),"reason":"explicit_user_approval"})
        self.metadata["authorized_total_usd"] = str(total)
        self.cap = new_cap
        self._write()

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
        self._write()

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
