"""Short, evidence-derived dataset descriptions and conclusions."""
import json
from collections import Counter


def dataset_summary(rows, manifest, sample):
    records = rows.drop_duplicates('record_id')
    sources = [json.loads(value) for value in records.source_json]
    groups = [json.loads(value) for value in records.groups_json]
    counts = records.reference.value_counts()
    filers = {str(source['cik']) for source in sources if source.get('cik')}
    years = sorted({str(group['fiscal_year']) for group in groups if group.get('fiscal_year')})
    statements = Counter(group['statement'] for group in groups if group.get('statement'))
    filters = manifest.get('filters', {})
    return {
        'selected_records': len(sample['main']), 'observed_records': len(records),
        'eligible_records': manifest.get('records'), 'categories': len(counts),
        'category_counts': {str(key): int(value) for key, value in counts.sort_index().items()},
        'records_per_category': [int(counts.min()), int(counts.max())] if len(counts) else [0, 0],
        'filers': len(filers) if filers else None, 'fiscal_years': years,
        'statements': dict(statements),
        'filer_split_records': sum(group.get('filer_split') == 'true' for group in groups),
        'label_differs_records': sum(group.get('label_differs') == 'true' for group in groups),
        'composite_records': len(sample['composite']), 'repeat_records': len(sample['repeat']),
        'shuffle_records': len(sample['shuffle']),
        'quarter_start': filters.get('quarter_start'), 'quarter_end': filters.get('quarter_end'),
    }


def dataset_lines(dataset, description, manifest):
    low, high = dataset['records_per_category']
    balance = str(low) if low == high else f'{low}–{high}'
    lines = [f"# The sample contains {dataset['selected_records']:,} records", '', description, '',
             '| Property | Tested sample |', '| --- | --- |',
             f"| Records | {dataset['observed_records']:,} observed of {dataset['selected_records']:,} selected; {dataset['eligible_records']:,} eligible in the source corpus |" if dataset['eligible_records'] is not None else f"| Records | {dataset['observed_records']:,} observed of {dataset['selected_records']:,} selected |",
             f"| Categories | {dataset['categories']}; {balance} records per category |"]
    if dataset['filers'] is not None:
        lines.append(f"| Companies | {dataset['filers']:,} distinct filers |")
    if dataset['fiscal_years']:
        lines.append(f"| Fiscal years | {', '.join(dataset['fiscal_years'])} |")
    if dataset['statements']:
        names = {'BS': 'Balance sheet', 'IS': 'Income statement'}
        lines.append('| Statements | ' + '; '.join(f'{names.get(key, key)}: {count:,}' for key, count in sorted(dataset['statements'].items())) + ' |')
        lines.append(f"| Label properties | {dataset['filer_split_records']:,} have wording mapped differently across filers; {dataset['label_differs_records']:,} differ from the standard label |")
    lines.append(f"| Subsets | Composite: {dataset['composite_records']:,}; repeat: {dataset['repeat_records']:,}; option shuffle: {dataset['shuffle_records']:,} |")
    if dataset['quarter_start']:
        lines.append(f"| Filing archives | {dataset['quarter_start']}–{dataset['quarter_end']} |")
    lines += ['', 'Sampling balances answer categories; aggregate accuracy does not estimate the natural filing mix.',
              'Source: [dataset manifest](dataset_manifest.json), [selected record IDs](sample_manifest.json), [record-level evidence](predictions.parquet).', '']
    lines += [f'- {limit}' for limit in manifest.get('limitations', [])]
    return lines + ['']


def make_verdict(rows, metrics, status):
    if not status['complete']:
        return {'headline': 'The run remains incomplete', 'result': 'Saved results cover a partial run.',
                'caveat': 'The study threshold is not evaluated.', 'next_step': 'Resolve the recorded stop before comparing models.'}
    if status['mode'] == 'fixture':
        return {'headline': 'The fixture verifies execution', 'result': 'Synthetic responses exercise the test pipeline.',
                'caveat': 'These results do not measure model quality.', 'next_step': 'Use a live sample for model comparison.'}
    base = rows[(rows.repeat_index == 0) & ~rows.shuffled]
    regimes = sorted(base.context_regime.unique(), key=lambda value: (value != 'with_context', value))
    comparison = None
    for regime in regimes:
        group = base[base.context_regime == regime]
        jev = group[group.method == 'jev_direct']
        names = sorted(name for name in group.method.unique() if name.startswith('direct_llm'))
        common = set(jev.record_id)
        for name in names:
            common &= set(group[group.method == name].record_id)
        if not names or not common:
            continue
        matched = group[group.record_id.isin(common)]
        name = max(names, key=lambda value: matched[matched.method == value].correct.mean())
        left, right = matched[matched.method == 'jev_direct'], matched[matched.method == name]
        comparison = (regime, left, right)
        break
    if comparison is None:
        return {'headline': 'The comparison remains unavailable', 'result': 'Matched Jev and language-model direct results are required.',
                'caveat': 'Recorded method metrics remain available below.', 'next_step': 'Complete both direct methods on the same records.'}
    regime, left, right = comparison
    count, jev_correct, llm_correct = len(left), int(left.correct.sum()), int(right.correct.sum())
    cost_known = left.usage_complete.all() and right.usage_complete.all() and left.cost_usd.notna().all() and right.cost_usd.notna().all()
    ratio = float(left.cost_usd.sum() / right.cost_usd.sum()) if cost_known and right.cost_usd.sum() > 0 else None
    price = 'cost comparison unavailable'
    if ratio is not None and ratio > 0:
        price = f'{1 / ratio:.1f}× cheaper' if ratio < 1 else f'{ratio:.1f}× the cost'
    context = regime.replace('_', ' ')
    result = f"Direct {context} ({count:,} records): Jev {jev_correct/count:.1%} vs {right.iloc[0].model} {llm_correct/count:.1%}; {price} at list prices."
    if status['mode'] == 'smoke':
        headline = 'Jev warrants a larger test' if jev_correct >= llm_correct and ratio is not None and ratio < 1 else 'The smoke warrants further evaluation'
        caveat = f'{count} records do not establish a winner.'
        if ratio is not None and ratio > .2:
            caveat += ' The 5× cost target was not met.'
    else:
        rules = metrics['pass_rule']
        outcomes = {rule['outcome'] for rule in rules.values()}
        headline = ('Jev meets the study thresholds' if outcomes == {'pass'} else
                    'Jev misses the study thresholds' if outcomes == {'fail'} else
                    'Context changes the study outcome' if outcomes == {'pass', 'fail'} else
                    'The study remains inconclusive')
        caveat = 'Study rule: ' + '; '.join(f"{key.replace('_', ' ')} {rule['outcome']} (n={rule.get('records', 0)})" for key, rule in rules.items()) + '.'
        if any(rule.get('noninferior') is False for rule in rules.values()):
            caveat += ' The shared sample cannot rule out an accuracy loss above 2 percentage points.'
    tied_scoring = any(m['method'].startswith('decomposed_llm') and (m.get('tie_rate') or 0) > 0 for m in metrics['methods'])
    next_step = 'Review tied composite scoring before choosing a method.' if tied_scoring else 'Review category errors before choosing a model.'
    return {'headline': headline, 'result': result, 'caveat': caveat, 'next_step': next_step,
            'direct_comparison': {'context_regime': regime, 'records': count, 'jev_correct': jev_correct,
                                  'llm_correct': llm_correct, 'llm_model': right.iloc[0].model, 'cost_ratio': ratio}}


def verdict_lines(verdict):
    return [f"## {verdict['headline']}", '', verdict['result'], '', verdict['caveat'] + ' ' + verdict['next_step'], '',
            'Source: [computed metrics](metrics.json).', '', '## Methods produce these results', '']


def print_summary(folder):
    summary = json.loads((folder / 'management_summary.json').read_text())
    dataset, verdict = summary['tested_dataset'], summary['verdict']
    print(f"Dataset: {dataset['observed_records']:,}/{dataset['selected_records']:,} records, {dataset['categories']} categories, {dataset['composite_records']} composite records.")
    print(verdict['headline'] + '.')
    print(verdict['result'])
    print(verdict['caveat'] + ' ' + verdict['next_step'])
    print(f"Known list-price cost: ${summary['run'].get('known_list_price_cost_usd', 0):.4f}")
    print(f"Report: {folder / 'report.md'}")
