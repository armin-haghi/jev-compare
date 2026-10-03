"""Decision evidence derived from saved outputs, without provider or case imports."""
import json


def model_name(model):
    names = {'openai/gpt-5-mini': 'GPT-5 mini', 'typesafe-ai/jev': 'Jev', 'jev': 'Jev', 'rules': 'Rules'}
    return names.get(model, model)


def method_name(method, model):
    if method == 'rules_baseline':
        return 'Programmed rules'
    prefix = 'Jev' if method.startswith('jev_') else model_name(model)
    suffix = ('direct' if method.startswith(('jev_direct', 'direct_llm')) else
              'combined scores, separate calls' if method.startswith(('jev_composite_concurrent', 'decomposed_llm_parallel')) else
              'combined scores, one bundled call')
    return f'{prefix} {suffix}'


def is_direct(method):
    return method == 'jev_direct' or method.startswith('direct_llm')


def describe_rows(group):
    n = len(group)
    answered = group.prediction != 'ABSTAIN'
    known = group.usage_complete.all() and group.cost_usd.notna().all()
    return {'method': group.iloc[0].method, 'model': group.iloc[0].model,
            'name': method_name(group.iloc[0].method, group.iloc[0].model),
            'context_regime': group.iloc[0].context_regime,
            'records': n, 'correct': int(group.correct.sum()), 'accuracy': float(group.correct.mean()),
            'answered': int(answered.sum()), 'abstained': int((~answered).sum()),
            'answered_accuracy': float(group.loc[answered, 'correct'].mean()) if answered.any() else None,
            'failed': int(group.failed.sum()),
            'cost_per_1000_usd': float(group.cost_usd.sum() / n * 1000) if known else None,
            'median_seconds': float(group.latency_ms.median() / 1000),
            'p95_seconds': float(group.latency_ms.quantile(.95) / 1000),
            'ties': sum(bool(json.loads(value).get('ties')) for value in group.diagnostics_json)}


def build_analysis(rows, metrics, config, verdict):
    base = rows[(rows.repeat_index == 0) & ~rows.shuffled]
    preferred_context = 'with_context' if 'with_context' in set(base.context_regime) else next(iter(sorted(base.context_regime.unique())), None)
    names = {r.method: method_name(r.method, r.model) for r in base.itertuples()}
    direct, shared, contexts, confidence, slices, categories, stability = [], [], [], [], [], [], []
    for regime, group in base.groupby('context_regime'):
        for method, evaluated in group.groupby('method'):
            if is_direct(method) or method == 'rules_baseline':
                direct.append(describe_rows(evaluated))
        common = set.intersection(*(set(g.record_id) for _, g in group.groupby('method')))
        if common and any(not is_direct(name) and name != 'rules_baseline' for name in group.method.unique()):
            for _, evaluated in group[group.record_id.isin(common)].groupby('method'):
                shared.append(describe_rows(evaluated))
    for method, group in base.groupby('method'):
        if not is_direct(method) and method != 'rules_baseline':
            continue
        paired = group[group.context_regime == 'label_only'].merge(
            group[group.context_regime == 'with_context'], on='record_id', suffixes=('_label', '_context'), validate='one_to_one')
        if len(paired):
            contexts.append({'method': method, 'name': names[method], 'records': len(paired),
                             'label_accuracy': float(paired.correct_label.mean()),
                             'context_accuracy': float(paired.correct_context.mean())})
    for method in metrics['methods']:
        if method['context_regime'] != preferred_context:
            continue
        key = method['method']
        stability.append({'method': key, 'name': names[key], 'repeatability': method['repeatability'], 'option_order': method['option_order']})
        if not is_direct(key):
            continue
        for point in method['confidence_coverage']:
            if point['target_coverage'] == .8:
                confidence.append({'method': key, 'name': names[key], 'records': method['records'],
                                   'retained': point['records'], 'deferred': method['records'] - point['records'],
                                   'accuracy': point['accuracy'], 'errors': point['records'] - round(point['accuracy'] * point['records'])})
        for item in method['by_group']:
            if item['dimension'] in ('baseline_miss', 'filer_split') and item['value'] == 'true':
                slices.append(item | {'method': key, 'name': names[key], 'correct': round(item['accuracy'] * item['records'])})
            elif item['dimension'] == 'template_line':
                categories.append(item | {'method': key, 'name': names[key], 'correct': round(item['accuracy'] * item['records'])})
    jev_categories = sorted((item for item in categories if item['method'] == 'jev_direct'), key=lambda item: (item['accuracy'], item['value']))[:3]
    selected = {item['value'] for item in jev_categories}
    categories = [item for item in categories if item['value'] in selected]
    costs = []
    for model, group in rows.groupby('model'):
        if (group.method == 'rules_baseline').all():
            continue
        known = bool(group.usage_complete.all())
        costs.append({'model': model, 'name': model_name(model), 'requests': int(group.request_count.sum()),
                      'input_tokens': int(group.input_tokens.sum()) if known else None,
                      'output_tokens': int(group.output_tokens.sum()) if known else None,
                      'known_cost_usd': float(group.known_cost_usd.sum()), 'usage_complete': known})
    comparison = verdict.get('direct_comparison')
    live_complete = metrics['run']['mode'] == 'benchmark' and metrics['run']['complete']
    if not live_complete or comparison is None:
        recommendation = 'This run does not support a deployment recommendation. ' + verdict['caveat']
    elif comparison['cost_ratio'] is not None and comparison['cost_ratio'] < 1 and comparison['accuracy_difference'] >= 0:
        recommendation = ('Prefer Jev direct for this tested task: it costs less than the direct language-model comparator without an observed aggregate accuracy loss. '
                          'This is a recommendation about the measured tradeoff; the acceptable error rate depends on the business.')
    else:
        recommendation = ('The direct comparison presents tradeoffs rather than a clear recommendation for Jev. '
                          'Choose using the measured accuracy, cost and unresolved errors for the intended workload; the study supplies no business-specific price for an error.')
    composite = [r for r in shared if r['context_regime'] == preferred_context and r['method'].startswith('jev_composite')]
    direct_shared = next((r for r in shared if r['context_regime'] == preferred_context and r['method'] == 'jev_direct'), None)
    if direct_shared and composite:
        if all(r['accuracy'] <= direct_shared['accuracy'] and r['cost_per_1000_usd'] is not None and direct_shared['cost_per_1000_usd'] is not None
               and r['cost_per_1000_usd'] >= direct_shared['cost_per_1000_usd'] for r in composite) and any(
                   r['accuracy'] < direct_shared['accuracy'] or r['cost_per_1000_usd'] > direct_shared['cost_per_1000_usd'] for r in composite):
            composition = 'The tested Jev combinations add cost without improving accuracy over Jev direct on the same records. Prefer the direct workflow for this task on this evidence.'
            composition_headline = 'Jev direct leads its combinations'
        else:
            composition = 'The shared-record results show the accuracy and cost tradeoffs of combining judgments. They apply to these scoring protocols and model configurations.'
            composition_headline = 'Combined scores change the tradeoff'
    else:
        composition = 'No matched direct-versus-combined comparison is available in this run.'
        composition_headline = 'Combination evidence remains unavailable'
    return {'format_version': 1, 'purpose': 'Compare Jev with the tested alternatives for a repeated data-management decision, using accuracy, cost, speed, confidence and consistency.',
            'case_id': config['case'], 'preferred_context': preferred_context, 'evidence_status': metrics['run']['mode'],
            'complete': metrics['run']['complete'], 'direct_results': direct, 'context_comparisons': contexts,
            'shared_results': shared, 'confidence_deferral': confidence, 'difficulty_slices': slices,
            'lowest_jev_categories': categories, 'stability': stability, 'model_costs': costs,
            'failed_outputs': int(rows.failed.sum()), 'unknown_usage_outputs': int((~rows.usage_complete).sum()),
            'output_rows': len(rows), 'provider_requests': int(rows.request_count.sum()),
            'recommendation': recommendation, 'composition_conclusion': composition, 'composition_headline': composition_headline,
            'recommendation_headline': 'The evidence favors Jev direct' if live_complete and recommendation.startswith('Prefer') else 'The evidence bounds the choice'}
