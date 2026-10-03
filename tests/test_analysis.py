import json
import pandas as pd
from benchmark.analysis import build_analysis
from benchmark.metrics import compute
from benchmark.summary import make_verdict


def comparison_rows():
    rows = []
    for method in ['jev_direct', 'direct_llm_small', 'rules_baseline', 'jev_composite_fanout']:
        for i in range(2 if 'composite' in method else 10):
            abstain = method == 'rules_baseline' and i < 2
            correct = not abstain and (method != 'jev_direct' or i >= 2)
            rows.append(dict(record_id=str(i), method=method, model=method, context_regime='with_context',
                             profile='full', repeat_index=0, shuffled=False, reference='a',
                             prediction='ABSTAIN' if abstain else 'a' if correct else 'b', correct=correct,
                             failed=False, confidence=.9 if correct else .1, probability_of_prediction=.9 if correct else .1,
                             cost_usd=.1 if method == 'jev_direct' else .4, known_cost_usd=.1 if method == 'jev_direct' else .4,
                             latency_ms=100, input_tokens=10, output_tokens=1, request_count=1, usage_complete=True,
                             source_json=json.dumps({'cik': str(i)}), groups_json='{}', diagnostics_json='{}'))
    return pd.DataFrame(rows)


def analyze(rows):
    config = {'case': 'toy', 'seed': 1, 'bootstrap_samples': 20, 'profiles': {'full': {'repeat_count': 2}}}
    metrics = compute(rows, config)
    metrics['run'] = {'complete': True, 'mode': 'benchmark'}
    verdict = make_verdict(rows, metrics, metrics['run'])
    return build_analysis(rows, metrics, config, verdict)


def test_shared_comparison_can_reverse_the_aggregate_result():
    rows = comparison_rows()
    rows.loc[rows.method == 'jev_direct', 'request_count'] = 99
    rows.loc[(rows.method == 'jev_direct') & (rows.record_id == '0'), 'request_count'] = 4
    rows.loc[(rows.method == 'jev_direct') & (rows.record_id == '1'), 'request_count'] = 6
    analysis = analyze(rows)
    direct = next(r for r in analysis['direct_results'] if r['method'] == 'jev_direct')
    shared = next(r for r in analysis['shared_results'] if r['method'] == 'jev_direct')
    assert (direct['correct'], direct['records']) == (8, 10)
    assert (shared['correct'], shared['records']) == (0, 2)
    assert direct['calls_per_record'] == [4, 99]
    assert shared['calls_per_record'] == [4, 6]
    assert shared['requests'] == 10
    assert 'extra scoring brought no accuracy gain' not in analysis['composition_conclusion']
    assert 'tradeoffs rather than a clear recommendation' in analysis['recommendation']


def test_rules_abstentions_and_confidence_deferrals_keep_denominators():
    analysis = analyze(comparison_rows())
    rules = next(r for r in analysis['direct_results'] if r['method'] == 'rules_baseline')
    assert (rules['correct'], rules['answered'], rules['abstained']) == (8, 8, 2)
    assert rules['accuracy'] == .8 and rules['answered_accuracy'] == 1
    confidence = next(r for r in analysis['confidence_deferral'] if r['method'] == 'jev_direct')
    assert (confidence['retained'], confidence['deferred'], confidence['errors']) == (8, 2, 0)


def test_unknown_cost_cannot_produce_lower_cost_recommendation():
    rows = comparison_rows()
    rows.loc[rows.method == 'jev_direct', 'correct'] = True
    rows.loc[0, 'usage_complete'] = False
    rows.loc[0, 'cost_usd'] = None
    analysis = analyze(rows)
    direct = next(r for r in analysis['direct_results'] if r['method'] == 'jev_direct')
    assert direct['cost_per_1000_usd'] is None
    assert not analysis['recommendation'].startswith('Prefer')
