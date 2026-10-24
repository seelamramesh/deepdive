"""Read-only usage export. Never starts research or calls an AI/search provider."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import urlopen


def summarize(run: dict) -> dict:
    calls = run.get('agent_calls', [])
    fields = ('prompt_tokens', 'completion_tokens', 'total_tokens', 'cached_prompt_tokens')

    def usage(items):
        result = {}
        for field in fields:
            values = [item.get(field) for item in items]
            valid = [v for v in values if isinstance(v, int) and not isinstance(v, bool) and v >= 0]
            result[field] = {'known_subtotal': sum(valid) if valid else None,
                             'recorded_calls': len(valid), 'missing_or_invalid_calls': len(values)-len(valid)}
        return result

    grouped = defaultdict(list)
    for call in calls:
        grouped[(call.get('agent', 'unknown'), call.get('model', 'unknown'))].append(call)
    events = run.get('retrieval_audit', [])
    searches = [search for event in events for search in event.get('searches', [])]
    last = (run.get('state_transitions') or [{}])[-1]
    elapsed = None
    try:
        elapsed = max(0, (datetime.fromisoformat(last['timestamp']) - datetime.fromisoformat(run['created_at'])).total_seconds())
    except (KeyError, TypeError, ValueError):
        pass
    return {
        'run_id': run['id'], 'question': run['question'], 'state': run['current_state'],
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'recorded_response_attempts': len(calls),
        'local_exact_cache_hits': sum(call.get('cache_hit') is True for call in calls),
        'confirmed_sent_requests': sum(call.get('request_sent') is True for call in calls),
        'request_sent_unknown': sum(call.get('request_sent') is None for call in calls),
        'recorded_unsuccessful_responses': sum(call.get('success') is False for call in calls),
        'usage': usage(calls),
        'by_agent_model': [{'agent': agent, 'model': model, 'recorded_response_attempts': len(items),
                            'usage': usage(items)} for (agent, model), items in sorted(grouped.items())],
        'sum_recorded_call_duration_ms': sum(call.get('duration_ms', 0) for call in calls),
        'elapsed_to_last_checkpoint_seconds': elapsed,
        'recorded_logical_searches': len(searches) if events else None,
        'searches_returning_urls': sum(bool(search.get('result_urls')) for search in searches) if events else None,
        'billable_search_requests': None,
        'source_count': len(run.get('sources', [])), 'evidence_count': len(run.get('evidence', [])),
        'claim_count': len(run.get('claims', [])), 'accepted_claim_count': len(run.get('accepted_claim_ids', [])),
        'warnings': run.get('warnings', []), 'error': run.get('error'),
        'cost': {'estimated_total': None, 'confirmed_billed_total': None, 'currency': None,
                 'status': 'unknown', 'reason': 'No verified Mesh/Brave billing rates or provider charge records supplied.'},
        'limitations': [
            'Recorded responses are not a complete billing ledger: transport failures and SDK-internal retries may be absent.',
            'Unknown usage remains null; token categories are independent subtotals, never added together.',
            'Historical missing traces cannot establish zero calls or zero search usage.',
            'Logical search count is not confirmed HTTP attempt count or billable usage.',
            'Active runs may not have persisted all agent calls yet.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://deepdive.srv1493167.hstgr.cloud')
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--run-id')
    choice.add_argument('--all', action='store_true')
    choice.add_argument('--workspace', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    parsed = urlparse(base)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
        parser.error('Use an HTTP(S) base URL without embedded credentials.')

    def get(path):
        with urlopen(base + path, timeout=30) as response:
            return json.load(response)

    if args.workspace:
        reports = [summarize(json.loads(args.workspace.read_text(encoding='utf-8')))]
        failures = []
    else:
        ids = [args.run_id] if args.run_id else [run['id'] for run in get('/runs')]
        reports, failures = [], []
        for run_id in ids:
            try:
                reports.append(summarize(get(f'/runs/{quote(run_id, safe="")}/workspace')))
            except Exception as error:
                failures.append({'run_id': run_id, 'error_type': type(error).__name__})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'runs': reports, 'read_failures': failures}, indent=2), encoding='utf-8')
    print(f'Exported {len(reports)} runs; {len(failures)} read failures. Cost remains unknown.')
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
