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
    assert '5× cost target was not met' in verdict['caveat']
    frame.loc[0, 'cost_usd'] = 999  # Unmatched costs cannot change the comparison.
    assert make_verdict(frame, metrics, status) == verdict
    frame.loc[1, 'usage_complete'] = False
    assert make_verdict(frame, metrics, status)['direct_comparison']['cost_ratio'] is None


def test_incomplete_and_fixture_cannot_claim_study_pass():
    for mode, complete, expected in [('fixture', True, 'The fixture verifies execution'),
                                      ('benchmark', False, 'The run remains incomplete')]:
        assert make_verdict(pd.DataFrame(), {'pass_rule': {'with_context': {'outcome': 'pass'}}},
                            {'mode': mode, 'complete': complete})['headline'] == expected
