"""Reader-facing report, rendered from the same evidence for local and shared use."""
from benchmark.analysis import is_direct, model_name
from benchmark.summary import dataset_lines


def percent(value):
    return f'{value:.2%}' if value is not None else 'Not measured'


def money(value):
    return f'${value:.4f}' if value is not None else 'Unknown'


def duration(value):
    return f'{value*1000:.3f}ms' if value < .001 else f'{value:.3f}s'


def calls(row):
    low, high = row['calls_per_record']
    return str(low) if low == high else f'{low}–{high}'


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] + [
        '| ' + ' | '.join(str(value).replace('|', '\\|').replace('\n', ' ') for value in row) + ' |' for row in rows] + ['']


def source():
    return ['Source: [saved analysis](analysis.json), [computed metrics](metrics.json).', '']


def run_intro(summary, analysis):
    task = ("This run maps company financial-statement labels using public United States Securities and Exchange Commission (SEC) filings and company-filed tags as the answer key."
            if analysis['case_id'] == 'sec_lines' else summary['case'])
    tested = ', '.join(sorted({model_name(m['model']) for m in summary['methods'] if m['method'] != 'rules_baseline'}))
    task += f" Tested models: {tested}. See the [methodology](methodology.md) for workflow definitions and scoring."
    if summary['run']['mode'] != 'benchmark' or not summary['run']['complete']:
        verdict = summary['verdict']
        task += f"\n\n**{verdict['headline']}.** {verdict['result']} {verdict['caveat']}"
    return task


def render_details(summary, analysis, config):
    dataset, verdict, status = summary['tested_dataset'], summary['verdict'], summary['run']
    context = analysis['preferred_context']
    sec = analysis['case_id'] == 'sec_lines'
    lines = dataset_lines(dataset, run_intro(summary, analysis), summary['dataset'])
    lines += [f"## {verdict['headline']}", '', verdict['result'], '', verdict['caveat'], '']
    primary = [row for row in analysis['direct_results'] if row['context_regime'] == context]
    lines += [f"The table uses {'surrounding context' if context == 'with_context' else 'labels without surrounding context'}.", '']
    lines += table(['Workflow', 'Correct / records', 'Accuracy', 'Abstentions', 'Cost / 1,000', 'Median / 95th-percentile time'], [
        [r['name'], f"{r['correct']:,} / {r['records']:,}", percent(r['accuracy']), r['abstained'], money(r['cost_per_1000_usd']),
         f"{duration(r['median_seconds'])} / {duration(r['p95_seconds'])}"] for r in primary])
    for r in primary:
        if r['method'] == 'rules_baseline':
            lines += [f"Rules answered {r['answered']:,}/{r['records']:,} records ({r['answered']/r['records']:.2%}); {percent(r['answered_accuracy'])} of those answers matched the key. Their {r['abstained']:,} abstentions are unresolved work, not incorrect emitted labels. Model-service cost is zero; implementation and maintenance costs are not measured.", '']
    comparison = verdict.get('direct_comparison', {})
    j = next((r for r in primary if r['method'] == 'jev_direct'), None)
    rival = next((r for r in primary if is_direct(r['method']) and r['method'] != 'jev_direct' and r['model'] == comparison.get('llm_model')), None)
    if j and rival and j['cost_per_1000_usd'] is not None and rival['cost_per_1000_usd'] is not None:
        saving = rival['cost_per_1000_usd'] - j['cost_per_1000_usd']
        lines += [f"The direct-call cost difference is {money(abs(saving))} per 1,000 records {'in Jev’s favor' if saving >= 0 else 'against Jev'}. These are uncached list-price estimates from measured tokens. Human review, integration and the cost of errors are not included.", '']
    if analysis['context_comparisons']:
        lines += table(['Workflow', 'Matched records', 'Labels without context', 'With context'], [
            [r['name'], f"{r['records']:,}", percent(r['label_accuracy']), percent(r['context_accuracy'])] for r in analysis['context_comparisons']])
    if analysis['difficulty_slices']:
        labels = {'baseline_miss': 'Rules were wrong or abstained', 'filer_split': 'Same wording maps differently across companies'}
        lines += table(['Difficult subset', 'Workflow', 'Correct / records', 'Accuracy'], [
            [labels[r['dimension']], r['name'], f"{r['correct']:,} / {r['records']:,}", percent(r['accuracy'])] for r in analysis['difficulty_slices']])
    if analysis['lowest_jev_categories']:
        lines += ['Aggregate accuracy hides category differences. These are the three lowest-accuracy categories for Jev direct, selected after scoring as a descriptive error review.', '']
        lines += table(['Category', 'Workflow', 'Correct / records', 'Accuracy'], [
            [r['value'].replace('_', ' '), r['name'], f"{r['correct']} / {r['records']}", percent(r['accuracy'])] for r in sorted(analysis['lowest_jev_categories'], key=lambda r: (r['value'], r['name']))])
    lines += source()

    retained = analysis['confidence_deferral']
    jev_retained = next((r for r in retained if r['method'] == 'jev_direct'), None)
    rivals_retained = [r for r in retained if r['method'] != 'jev_direct']
    fewer_errors = jev_retained and rivals_retained and all(r['retained'] == jev_retained['retained'] and r['errors'] > jev_retained['errors'] for r in rivals_retained)
    confidence_headline = 'Jev confidence leaves fewer errors' if fewer_errors else 'Confidence changes the review tradeoff'
    lines += [f'## {confidence_headline}', '',
              'The table retains each method’s most confident 80% in this run.', '']
    lines += table(['Workflow', 'Retained', 'Deferred', 'Errors retained', 'Retained accuracy'], [
        [r['name'], f"{r['retained']:,}", f"{r['deferred']:,}", r['errors'], percent(r['accuracy'])] for r in analysis['confidence_deferral']])
    if fewer_errors:
        lines += ['At the same retained volume, Jev’s confidence ranking leaves fewer incorrect mappings in the accepted work. This supports using confidence to identify records needing review.', '']
    lines += source()

    lines += [f"## {analysis['composition_headline']}", '',
              'Every row below uses the same shared records in this run.', '']
    shared = sorted([r for r in analysis['shared_results'] if r['context_regime'] == context], key=lambda r: (model_name(r['model']), r['task']))
    lines += table(['Model', 'What we asked it to do', 'Calls / record', 'Correct / shared records', 'Cost / 1,000', 'Tied top scores'], [
        [model_name(r['model']), r['task'], calls(r), f"{r['correct']} / {r['records']}", money(r['cost_per_1000_usd']), f"{r['ties']} / {r['records']}"] for r in shared])
    lines += [analysis['composition_conclusion'], '']
    lines += table(['Workflow', 'Changed on repeat / checked', 'Changed after reordering / checked'], [
        [r['name'], f"{round(r['repeatability']['at_least_one_change']*r['repeatability']['records'])} / {r['repeatability']['records']}" if r['repeatability']['at_least_one_change'] is not None else 'Not measured',
         f"{round(r['option_order']['prediction_change_rate']*r['option_order']['records'])} / {r['option_order']['records']}" if r['option_order']['prediction_change_rate'] is not None else 'Not measured'] for r in analysis['stability']])
    lines += source()

    lines += [f"## {analysis['recommendation_headline']}", '', analysis['recommendation'], '']
    if status['mode'] == 'benchmark' and status['complete']:
        if j:
            lines += [f"Jev direct disagreed with the key on {j['records']-j['correct']:,}/{j['records']:,} records in the primary condition. The error categories and retained-error counts above should determine where review remains necessary; this study assigns no monetary value to a wrong mapping.", '']
        lines += ['Programmed rules remain useful where their answered subset fits the required coverage. Routing rules’ unresolved records to a model is a plausible implementation option, but that combined workflow was not tested.', '',
                  'The conventional direct model remains an alternative, with its observed strengths and weaknesses shown by category. The tested combined-score workflows should be judged against direct calls, including their extra cost and instability, rather than treated as an inherent benefit of Jev’s approach.', '']
    lines += ['The conclusion applies to this sampled task and these configurations. It does not establish performance on other finance data-management tasks or untested models. The balanced category mix differs from a natural production workload, and the answer key is not an independent review of accounting correctness.' if sec else 'The conclusion applies to this sampled task and these configurations; other tasks and untested models remain unmeasured.', '']
    lines += source()

    lines += ['## Saved evidence supports these findings', '',
              f"Run {status['run_id']}: {analysis['output_rows']:,} saved outputs, {analysis['provider_requests']:,} provider requests, {analysis['failed_outputs']:,} failed outputs and {analysis['unknown_usage_outputs']:,} outputs with unknown usage. Total known list-price cost: {money(status.get('known_list_price_cost_usd', 0))}. All costs are in United States dollars. This total includes every input condition, workflow and repeat/order check; it is not the cost of one direct pass.", '']
    lines += table(['Model', 'Requests', 'Input tokens', 'Output tokens', 'Known list-price cost'], [
        [r['name'], f"{r['requests']:,}", f"{r['input_tokens']:,}" if r['input_tokens'] is not None else 'Unknown',
         f"{r['output_tokens']:,}" if r['output_tokens'] is not None else 'Unknown', money(r['known_cost_usd'])] for r in analysis['model_costs']])
    lines += [f"Execution used {config.get('record_concurrency', 1)} concurrent records and up to {config.get('question_concurrency', 8)} concurrent score questions per record. The saved model identifiers and prices describe the run; provider aliases need not identify immutable model weights.", '',
              'Evidence: [analysis](analysis.json), [metrics](metrics.json), [dataset manifest](dataset_manifest.json), [selected record IDs](sample_manifest.json), [configuration](resolved_config.yaml), [prompts](prompts.yaml). Raw predictions are retained beside the local report; the shareable evidence snapshot includes their hash.', '',
              'The [historical criterion audit](criterion-audit.md) preserves the original brief’s numerical targets and outcomes. It does not determine this report’s recommendation. The recommendation follows the measured task-level tradeoffs above.', '']
    for regime in sorted({m['context_regime'] for m in summary['methods']}):
        lines += [f"![Share of answers retained versus their error rate, {regime.replace('_', ' ')}](coverage-{regime}.svg)", '']
    lines += [f"- {limit}" for limit in summary['limitations']]
    return '\n'.join(lines) + '\n'


def render_report(summary, analysis, config):
    dataset, verdict, status = summary['tested_dataset'], summary['verdict'], summary['run']
    sec = analysis['case_id'] == 'sec_lines'
    lines = dataset_lines(dataset, run_intro(summary, analysis), summary['dataset'])
    lines += [f"## {verdict['headline']}", '', verdict['result'], '', verdict['caveat'], '']
    primary = [r for r in analysis['direct_results'] if r['context_regime'] == analysis['preferred_context']]
    model_labels = {r['method']: model_name(r['model']) for r in primary}
    conditions = {(r['method'], r['context_regime']): r for r in analysis['direct_results']}
    def accuracy_cell(method, regime):
        row = conditions.get((method, regime))
        return f"{percent(row['accuracy'])} ({row['correct']:,}/{row['records']:,})" if row else 'Not measured'
    lines += table(['Workflow', 'Labels alone', 'With context', 'Cost / 1,000', 'Median response'], [
        [r['name'], accuracy_cell(r['method'], 'label_only'), accuracy_cell(r['method'], 'with_context'),
         money(r['cost_per_1000_usd']), duration(r['median_seconds'])] for r in primary])
    lines += [f"Cost and timing use {analysis['preferred_context'].replace('_', ' ')}; costs are estimated United States dollars.", '']
    rules = next((r for r in primary if r['method'] == 'rules_baseline'), None)
    if rules:
        lines += [f"Rules answered {rules['answered']:,}/{rules['records']:,} records at {percent(rules['answered_accuracy'])} accuracy among answers, leaving {rules['abstained']:,} unresolved.", '']
    retained = analysis['confidence_deferral']
    if retained:
        counts = {(r['retained'], r['deferred']) for r in retained}
        if len(counts) == 1:
            kept, deferred = next(iter(counts))
            lines += [f"Keeping each method’s most confident 80% retains {kept:,} records and defers {deferred:,}: " + '; '.join(
                f"{model_labels[r['method']]} leaves {r['errors']} errors ({percent(r['accuracy'])} accuracy)" for r in retained) + '. Each method selects different records; human-review outcomes were not measured.', '']
        else:
            lines += table(['Workflow', 'Retained / deferred', 'Errors retained', 'Accuracy'], [
                [r['name'], f"{r['retained']} / {r['deferred']}", r['errors'], percent(r['accuracy'])] for r in retained])
    shared = sorted([r for r in analysis['shared_results'] if r['context_regime'] == analysis['preferred_context'] and r['method'] != 'rules_baseline'], key=lambda r: (model_name(r['model']), r['task']))
    if shared:
        lines += [f"On the same {shared[0]['records']:,} records, we tested whether smaller questions helped either model. Each candidate category received two scores: wording fit and fit with surrounding lines. We asked for these scores together or in separate calls:", '']
        lines += table(['Model', 'What we asked it to do', 'Calls / record', 'Correct / records', 'Cost / 1,000'], [
            [model_name(r['model']), r['task'], calls(r), f"{r['correct']} / {r['records']}", money(r['cost_per_1000_usd'])] for r in shared])
        lines += [analysis['composition_conclusion'], '']
    direct_stability = [r for r in analysis['stability'] if is_direct(r['method'])]
    if direct_stability and all(r['repeatability']['at_least_one_change'] == 0 and r['option_order']['prediction_change_rate'] == 0 for r in direct_stability):
        lines += ['Category choices did not change in these checks: ' + '; '.join(
            f"{model_labels[r['method']]}: {r['repeatability']['records']} repeated and {r['option_order']['records']} reordered records" for r in direct_stability) + '. These small checks do not establish universal stability.', '']
    lines += [f"## {analysis['recommendation_headline']}", '', analysis['recommendation'], '']
    categories = analysis['lowest_jev_categories']
    counterexamples = []
    for j in (r for r in categories if r['method'] == 'jev_direct'):
        for rival in categories:
            if rival['value'] == j['value'] and rival['method'] != 'jev_direct' and rival['accuracy'] > j['accuracy']:
                counterexamples.append((rival['accuracy']-j['accuracy'], j, rival))
    if counterexamples:
        _, j, rival = max(counterexamples, key=lambda item: item[0])
        rival_model = next(row['model'] for row in primary if row['method'] == rival['method'])
        lines += [f"The aggregate hides weaknesses: for “{j['value'].replace('_', ' ')}”, Jev scored {j['correct']}/{j['records']} versus {model_name(rival_model)}'s {rival['correct']}/{rival['records']}. This is a descriptive category check, not proof of a general advantage.", '']
    lines += ['This supports a choice for this task and these configurations. Public filed tags are a proxy answer key; the category-balanced sample does not represent every production workload. Other finance tasks, untested models, integration costs and review costs remain unmeasured.' if sec else 'The findings apply to this task and these configurations. Other tasks, untested models, integration costs and review costs remain unmeasured.', '',
              f"Run {status['run_id']}: {analysis['output_rows']:,} outputs across all variants and checks, {analysis['provider_requests']:,} requests, {analysis['failed_outputs']:,} failed outputs; {money(status.get('known_list_price_cost_usd', 0))} known list-price cost. Unknown-usage outputs: {analysis['unknown_usage_outputs']:,}.", '',
              'Sources: [methodology](methodology.md), [detailed analysis](details.md), [results and uncertainty](metrics.json), [recommendation evidence](analysis.json), [configuration](resolved_config.yaml). The [historical criterion](criterion-audit.md) is retained for audit; it does not decide the recommendation.']
    return '\n'.join(lines) + '\n'
