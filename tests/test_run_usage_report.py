from scripts.run_usage_report import summarize


def test_unknown_usage_and_searches_are_not_zero():
    report = summarize({'id':'r', 'question':'q', 'current_state':'END', 'agent_calls':[{'agent':'judge'}]})
    assert report['usage']['total_tokens']['known_subtotal'] is None
    assert report['usage']['total_tokens']['missing_or_invalid_calls'] == 1
    assert report['recorded_logical_searches'] is None
    assert report['cost']['estimated_total'] is None


def test_zero_partial_failed_response_and_independent_token_counts():
    report = summarize({'id':'r', 'question':'q', 'current_state':'END', 'agent_calls':[
        {'agent':'judge', 'model':'mesh/model', 'total_tokens':0, 'prompt_tokens':0, 'success':False},
        {'agent':'judge', 'model':'mesh/model', 'prompt_tokens':10, 'completion_tokens':5, 'total_tokens':15},
        {'agent':'planner', 'total_tokens':None},
        {'agent':'planner', 'total_tokens':-1},
    ], 'retrieval_audit':[{'searches':[{'result_urls':['https://example.org']},{'result_urls':[]}]}]})
    assert report['usage']['total_tokens'] == {'known_subtotal':15, 'recorded_calls':2, 'missing_or_invalid_calls':2}
    assert report['usage']['prompt_tokens']['known_subtotal'] == 10
    assert report['usage']['completion_tokens']['known_subtotal'] == 5
    assert report['recorded_unsuccessful_responses'] == 1
    assert report['recorded_logical_searches'] == 2
    assert report['billable_search_requests'] is None
