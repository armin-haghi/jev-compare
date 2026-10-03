"""Concise factsheets rendered from saved evidence, without provider calls."""
from benchmark.analysis import is_direct, model_name


def percent(value):
    return f'{value:.2%}' if value is not None else 'Not measured'


def money(value):
    return f'${value:.4f}' if value is not None else 'Unknown'


def duration(value):
    return f'{value:.3f}s'


def calls(row):
    low, high = row['calls_per_record']
    return str(low) if low == high else f'{low}–{high}'


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] + [
        '| ' + ' | '.join(str(value).replace('|', '\\|').replace('\n', ' ') for value in row) + ' |' for row in rows] + ['']


def category(value):
    return {'sga': 'Selling, general and administrative expenses',
            'other_operating': 'Other operating income/expense',
            'other_nonoperating': 'Other non-operating income/expense',
            'total_nonoperating': 'Total non-operating income/expense'}.get(value, value.replace('_', ' ').capitalize())


def render_report(summary, analysis, config):
    dataset, verdict, status = summary['tested_dataset'], summary['verdict'], summary['run']
    context = analysis['preferred_context']
    sec = analysis['case_id'] == 'sec_lines'
    primary = [r for r in analysis['direct_results'] if r['context_regime'] == context]
    models = sorted((r for r in primary if is_direct(r['method'])), key=lambda r: (r['method'] != 'jev_direct', r['model']))
    names = {r['method']: model_name(r['model']) for r in models}
    lines = [f"# {verdict['headline']}", '']
    if analysis['recommendation'].startswith('Prefer'):
        task = 'financial-statement mapping' if sec else 'this task'
        lines += [f'**Recommendation:** Start with Jev, TypeSafe’s fixed-choice decision model, for {task}. Ask for the final category in one call. It cost less without reducing observed overall accuracy.', '']
    else:
        lines += [analysis['recommendation'], '']
    total = money(status.get('known_list_price_cost_usd'))
    split = '; '.join(f"{r['name']} {money(r['known_cost_usd'])}" for r in analysis['model_costs'])
    cost_label = 'Known run cost' if analysis['unknown_usage_outputs'] else 'Total run cost'
    unknown = f" Usage is unknown for {analysis['unknown_usage_outputs']:,} outputs; total cost is incomplete." if analysis['unknown_usage_outputs'] else ''
    lines += [f"**{cost_label}: {total}** ({split}). Uncached list-price estimate in US dollars, covering all variants and checks; not an invoice.{unknown}", '',
              f"## The test covers {dataset['selected_records']:,} mappings" if sec else f"## The test covers {dataset['selected_records']:,} records", '']
    if sec:
        rivals = ', '.join(model_name(r['model']) for r in models if r['method'] != 'jev_direct') or 'the configured alternatives'
        lines += [f'The test compares Jev with {rivals} and programmed rules on accuracy, cost, speed and confidence for routing uncertain mappings to review.', '']
    else:
        lines += [summary['case'], '']
    low, high = dataset['records_per_category']
    balance = str(low) if low == high else f'{low}–{high}'
    properties = [['Sample', f"{dataset['observed_records']:,} observed records; {dataset['categories']} categories, {balance} each"]]
    if dataset['filers'] is not None:
        properties.append(['Companies and period', f"{dataset['filers']:,} filers; fiscal years {', '.join(dataset['fiscal_years'])}"])
    if dataset['statements']:
        labels = {'BS': 'balance-sheet', 'IS': 'income-statement'}
        properties.append(['Statement mix', '; '.join(f'{n:,} {labels.get(k, k)} lines' for k, n in sorted(dataset['statements'].items()))])
        properties.append(['Ambiguous wording', f"{dataset['filer_split_records']:,} records have wording mapped differently across companies"])
    properties.append(['Additional checks', f"{dataset['composite_records']:,} records for extra scoring; {dataset['repeat_records']:,} repeated; {dataset['shuffle_records']:,} with reordered options"])
    lines += table(['Dataset property', 'Tested value'], properties)
    if sec:
        lines += ['Source: public United States Securities and Exchange Commission filings. Filed tags supply the answer key and are hidden from model input. Category balancing differs from a production workload.', '']
    bounds = verdict.get('direct_comparison', {}).get('filer_cluster_bootstrap_95')
    headline = 'Accuracy differences remain uncertain' if bounds is not None and bounds[0] <= 0 <= bounds[1] else 'Direct results quantify the tradeoff'
    lines += [f'## {headline}', '',
              f"Each model chose one category from the same options, {'with nearby lines and financial context' if context == 'with_context' else 'using labels without nearby context'}.", '']
    lines += table(['Model', 'Correct / tested', 'Accuracy', 'Cost / 1,000', 'Median response'], [
        [model_name(r['model']), f"{r['correct']:,}/{r['records']:,}", percent(r['accuracy']), money(r['cost_per_1000_usd']), duration(r['median_seconds'])] for r in models])
    lines += [verdict['caveat'], '']
    rules = next((r for r in primary if r['method'] == 'rules_baseline'), None)
    if rules:
        lines += [f"**Rules:** {rules['answered']:,}/{rules['records']:,} answered at {percent(rules['answered_accuracy'])} accuracy; {rules['abstained']:,} unresolved. Model-service cost: $0.", '']
    retained = analysis['confidence_deferral']
    if retained and len({(r['retained'], r['deferred']) for r in retained}) == 1:
        kept, deferred = retained[0]['retained'], retained[0]['deferred']
        lines += [f"**Review tradeoff:** retaining each model’s most confident 80% ({kept:,} answers) leaves " + '; '.join(
            f"{names[r['method']]}: {r['errors']} errors" for r in retained) + f". Each defers {deferred:,} records; selected records differ. Human-review results remain unmeasured.", '']
    examples = analysis.get('illustrative_examples', [])
    if examples:
        headline = ('Identical labels produce different outcomes' if len(examples) > 1 and len({e['input']['label'] for e in examples}) == 1
                    else 'Examples expose successes and failures')
        lines += [f'## {headline}', '',
                  'Illustrations: one Jev success, one comparator success and one shared failure where available, selected for ambiguous, short labels. Excerpts show the nearest lines around the **target**; examples do not represent outcome frequencies.', '']
        def excerpt(example):
            payload, source = example['input'], example['source']
            above, below = payload.get('lines_above', []), payload.get('lines_below', [])
            parts = ([above[-1]] if above else []) + [f"**{payload['label']}**"] + ([below[0]] if below else [])
            owner = f"{source.get('name', example['record_id'][:10])}, {source.get('fy', '')}"
            return owner + ': ' + ' → '.join(parts)
        lines += table(['Statement excerpt', 'Filed-tag answer', 'Jev answer', f"{model_name(examples[0]['comparator_model'])} answer"], [
            [excerpt(e), category(e['reference']), category(e['jev_prediction']), category(e['comparator_prediction'])] for e in examples])
    shared = [r for r in analysis['shared_results'] if r['context_regime'] == context and r['method'] != 'rules_baseline']
    if shared:
        dominates = analysis['composition_conclusion'].startswith('The extra scoring brought no accuracy gain')
        heading = 'Extra scoring added cost' if dominates else 'Extra scoring changes the tradeoff'
        lines += [f'## {heading}', '',
                  f"On the same {shared[0]['records']:,} records, we tested whether scoring each candidate’s wording and context separately helped. Code combined the scores to choose a category.", '']
        lines += table(['Model', 'Task', 'Calls / record', 'Correct / tested', 'Cost / 1,000'], [
            [model_name(r['model']), r['task'], calls(r), f"{r['correct']}/{r['records']}", money(r['cost_per_1000_usd'])]
            for r in sorted(shared, key=lambda r: (r['method'] != 'jev_direct' and not r['method'].startswith('jev_'), r['task']))])
        lines += [analysis['composition_conclusion'], '']
        for r in shared:
            if r['method'].startswith('decomposed_llm_parallel') and r['ties'] > r['records'] / 2:
                lines += [f"{model_name(r['model'])} gave tied top scores on {r['ties']}/{r['records']} records in separate calls; fixed category order broke those ties. This configuration performed poorly.", '']
    categories = analysis['lowest_jev_categories']
    counterexamples = [(r['accuracy']-j['accuracy'], j, r) for j in categories if j['method'] == 'jev_direct'
                       for r in categories if r['value'] == j['value'] and r['method'] != 'jev_direct' and r['accuracy'] > j['accuracy']]
    if counterexamples:
        _, j, rival = max(counterexamples, key=lambda item: item[0])
        lines += [f"**Counterevidence:** for {category(j['value']).lower()}, Jev matched {j['correct']}/{j['records']} tags versus {names[rival['method']]}'s {rival['correct']}/{rival['records']}.", '']
    lines += ['Filed tags are a proxy for accounting correctness. Other finance tasks, models, integration costs and review costs remain unmeasured.' if sec else 'Other tasks, models, integration costs and review costs remain unmeasured.', '',
              f"Run `{status['run_id']}`: {analysis['output_rows']:,} outputs, {analysis['provider_requests']:,} requests, {analysis['failed_outputs']:,} failed outputs, {analysis['unknown_usage_outputs']:,} outputs with unknown usage.", '',
              'Sources: [run evidence](evidence.json) includes metrics, example inputs and filed tags, configuration, historical criteria and source hashes. [Shared methodology](methodology.md) defines the comparisons; its preserved run version is embedded in the evidence.']
    return '\n'.join(lines) + '\n'
