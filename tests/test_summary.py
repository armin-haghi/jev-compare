from copy import deepcopy
import pandas as pd
from benchmark.summary import make_verdict


def test_verdict_uses_matched_records_and_known_costs():
    rows = []
    for method, ids in [('jev_direct', ['a', 'b', 'c']), ('direct_llm_small', ['b', 'c'])]:
        for record_id in ids:
            rows.append(dict(method=method, record_id=record_id, context_regime='with_context', repeat_index=0,
                             shuffled=False, correct=record_id != 'a', usage_complete=True, cost_usd=0.1 if method == 'jev_direct' else 0.4,
                             model='jev' if method == 'jev_direct' else 'mini'))
    frame = pd.DataFrame(rows)
    metrics = {'methods': [], 'pass_rule': {}}
    status = {'mode': 'smoke', 'complete': True}
    verdict = make_verdict(frame, metrics, status)
    assert verdict['direct_comparison']['records'] == 2
    assert verdict['direct_comparison']['cost_ratio'] == .25
    assert '4.0× cheaper' in verdict['result']
    assert 'at list prices' in verdict['result']
    assert 'do not establish a winner' in verdict['caveat']
    frame.loc[0, 'cost_usd'] = 999  # Unmatched costs cannot change the comparison.
    assert make_verdict(frame, metrics, status) == verdict
    frame.loc[1, 'usage_complete'] = False
    assert make_verdict(frame, metrics, status)['direct_comparison']['cost_ratio'] is None


def test_incomplete_and_fixture_cannot_claim_study_pass():
    for mode, complete, expected in [('fixture', True, 'The fixture verifies execution'),
                                      ('benchmark', False, 'The run remains incomplete')]:
        assert make_verdict(pd.DataFrame(), {'pass_rule': {'with_context': {'outcome': 'pass'}}},
                            {'mode': mode, 'complete': complete})['headline'] == expected


def test_study_verdict_explains_the_smaller_shared_sample():
    rows = pd.DataFrame([
        dict(method=method, record_id=str(i), context_regime='with_context', repeat_index=0,
             shuffled=False, correct=True, usage_complete=True, cost_usd=.1 if method == 'jev_direct' else .4,
             model='jev' if method == 'jev_direct' else 'mini')
        for method in ['jev_direct', 'direct_llm_small'] for i in range(10)])
    metrics = {'methods': [], 'pass_rule': {'with_context': {
        'outcome': 'fail', 'records': 2, 'noninferior': False, 'cost_ratio': .25,
        'higher_accuracy_at_80_coverage': True,
        'comparison': {'filer_cluster_bootstrap_95': [-.5, .5]}}},
        'pairwise': [{'left': 'jev_direct', 'right': 'direct_llm_small', 'context_regime': 'with_context',
                      'records': 10, 'filer_cluster_bootstrap_95': [-.01, .01]}]}
    original = deepcopy(metrics)
    verdict = make_verdict(rows, metrics, {'mode': 'benchmark', 'complete': True})
    assert '(10 records)' in verdict['result']
    assert '4.0× cheaper' in verdict['result']
    assert '95% interval -1.00 to +1.00' in verdict['caveat']
    assert 'An accuracy advantage is not established' in verdict['caveat']
    assert verdict['headline'] == 'Jev cuts direct costs 75%'
    audit = verdict['criterion_audit']
    assert audit['outcomes'] == metrics['pass_rule']
    assert audit['outcomes']['with_context']['comparison']['filer_cluster_bootstrap_95'] == [-.5, .5]
    assert 'individual author is not recorded' in audit['origin']
    assert 'cost ratio <= 20% OR higher accuracy' in audit['rule']
    assert metrics == original  # Interpretations cannot change the original criterion.


def test_cheaper_method_with_lower_accuracy_reports_tradeoff():
    rows = pd.DataFrame([
        dict(method=method, record_id=str(i), context_regime='with_context', repeat_index=0,
             shuffled=False, correct=method != 'jev_direct' or i > 1, usage_complete=True,
             cost_usd=.1 if method == 'jev_direct' else .4, model=method)
        for method in ['jev_direct', 'direct_llm_small'] for i in range(10)])
    pair = {'left': 'jev_direct', 'right': 'direct_llm_small', 'context_regime': 'with_context',
            'records': 10, 'filer_cluster_bootstrap_95': [-.4, -.1]}
    verdict = make_verdict(rows, {'pairwise': [pair]}, {'mode': 'benchmark', 'complete': True})
    assert verdict['headline'] == 'Direct results show a tradeoff'
    assert 'supports lower accuracy' in verdict['caveat']
    assert 'favors Jev on accuracy' not in verdict['result']
    pair['records'] = 2  # An interval from a different sample cannot describe all 10 records.
    verdict = make_verdict(rows, {'pairwise': [pair]}, {'mode': 'benchmark', 'complete': True})
    assert verdict['direct_comparison']['filer_cluster_bootstrap_95'] is None
    assert 'uncertainty was not estimated' in verdict['caveat']
