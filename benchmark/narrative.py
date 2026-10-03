"""Reader-facing report, rendered from the same evidence for local and shared use."""
from benchmark.analysis import is_direct, method_name, model_name
from benchmark.summary import dataset_lines


def percent(value):
    return f'{value:.2%}' if value is not None else 'Not measured'


def money(value):
    return f'${value:.4f}' if value is not None else 'Unknown'


def duration(value):
    return f'{value*1000:.3f}ms' if value < .001 else f'{value:.3f}s'


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] + [
        '| ' + ' | '.join(str(value).replace('|', '\\|').replace('\n', ' ') for value in row) + ' |' for row in rows] + ['']


def source():
    return ['Source: [saved analysis](analysis.json), [computed metrics](metrics.json).', '']


def render_details(summary, analysis, config):
    dataset, verdict, status = summary['tested_dataset'], summary['verdict'], summary['run']
    context = analysis['preferred_context']
    sec = analysis['case_id'] == 'sec_lines'
    orientation = ("This study tests financial-statement line mapping: assigning a company's wording to a standard category. "
                   "It compares Jev, a model that selects predefined answers and returns probabilities, with a conventional language model and programmed rules. "
                   "The records come from public United States Securities and Exchange Commission (SEC) filings; company-filed accounting tags supply the answer key."
                   if sec else summary['case'] + ' Jev selects predefined answers and returns probabilities; the tested alternatives use a conventional language model or programmed rules.')
    if status['mode'] != 'benchmark' or not status['complete']:
        orientation += f"\n\n**{verdict['headline']}.** {verdict['result']} {verdict['caveat']} All tables below describe this evidence status."
    lines = dataset_lines(dataset, orientation, summary['dataset'])
    lines += ['## The study compares decision workflows', '',
              'The decision is whether Jev offers a useful accuracy, cost and speed tradeoff for this repeated data-management task, and whether its confidence can help route uncertain answers for review.', '']
    if sec:
        lines += ["For example, a line labelled ‘Other income, net’ must be assigned to a category such as total non-operating income or another non-operating component. These are different template answers; neighbouring lines can help distinguish them.", '',
                  f"The answer set contains {dataset['categories']} categories across two statements; each record receives the candidates belonging to its statement. Labels and statement type are supplied in both conditions. The context condition also supplies up to two neighbouring lines on each side, the amount's sign and relative size, and industry description. Filed tags and company identifiers are withheld from the model input.", '']
    lines += ['A direct call chooses the final category. A combined-score workflow asks how well each candidate fits the wording and position, scores numeric compatibility in code, and combines the three scores with equal weight. Scores use a five-level scale from 0 to 4; ties use the fixed template order. The same combination rule is used for both model families.', '']
    present = {m['method']: m for m in summary['methods']}
    descriptions = []
    for key, method in sorted(present.items()):
        name = method_name(key, method['model'])
        detail = ('Keyword and position rules; abstain when no unique category is selected.' if key == 'rules_baseline' else
                  'One call chooses a category. Jev also supplies probabilities for every option.' if key == 'jev_direct' else
                  'One call returns the category and a self-reported confidence number.' if is_direct(key) else
                  'All candidate judgments are requested in one call; code combines the scores.' if key.startswith(('jev_composite_fanout', 'decomposed_llm_matrix')) else
                  'Each candidate judgment uses a separate call; code combines the scores.')
        descriptions.append([name, detail])
    lines += table(['Tested workflow', 'What it does'], descriptions)
    lines += table(['Comparison', 'What it tries to find', 'Why it matters'], [
        ['Direct models versus rules', 'Accuracy, cost and response time on the main sample', 'A model must add value beyond deterministic matching.'],
        ['Labels versus context', 'Whether surrounding information improves mapping', 'Similar finance labels can mean different things.'],
        ['Confidence-based deferral', 'Errors remaining after doubtful answers are set aside', 'Review effort can focus on uncertain mappings.'],
        ['Direct versus combined scores', 'Whether decomposition improves the final decision', 'Extra calls and scoring logic must justify their cost.'],
        ['Repeats and reordered answers', 'Whether unchanged records receive changed decisions', 'Inconsistent mappings create reconciliation work.']])
    tested = sorted({model_name(m['model']) for m in summary['methods'] if m['method'] != 'rules_baseline'})
    lines += ['Tested models: ' + ', '.join(tested) + '. Results describe these model configurations and prompts; they do not isolate architecture from prompting or pricing. Source: [stored configuration](resolved_config.yaml), [stored prompts](prompts.yaml).', '']

    lines += [f"## {verdict['headline']}", '', verdict['result'], '', verdict['caveat'], '']
    primary = [row for row in analysis['direct_results'] if row['context_regime'] == context]
    lines += [f"The table uses {'surrounding context' if context == 'with_context' else 'labels without surrounding context'}. Accuracy is agreement with the answer key; failed calls and abstentions count as wrong in the overall score.", '']
    lines += table(['Workflow', 'Correct / records', 'Accuracy', 'Abstentions', 'Cost / 1,000', 'Median / 95th-percentile time'], [
        [r['name'], f"{r['correct']:,} / {r['records']:,}", percent(r['accuracy']), r['abstained'], money(r['cost_per_1000_usd']),
         f"{duration(r['median_seconds'])} / {duration(r['p95_seconds'])}"] for r in primary])
    lines += ['The 95th percentile is the response time within which 95% of measured decisions completed. Timing includes this run’s execution overhead and concurrent load; it is not a throughput guarantee.', '']
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
              'Confidence is the score a method attaches to its selected answer. The table keeps each direct method’s most confident 80% and defers the remaining 20%. This is an illustration from the measured curve, not an acceptance target or a recommended production setting.', '']
    lines += table(['Workflow', 'Retained', 'Deferred', 'Errors retained', 'Retained accuracy'], [
        [r['name'], f"{r['retained']:,}", f"{r['deferred']:,}", r['errors'], percent(r['accuracy'])] for r in analysis['confidence_deferral']])
    if fewer_errors:
        lines += ['At the same retained volume, Jev’s confidence ranking leaves fewer incorrect mappings in the accepted work. This supports using confidence to identify records needing review.', '']
    lines += ['Each method selects its own retained records, so these accepted subsets differ. The result measures error concentration, not the outcome of human review or a tested end-to-end review workflow. Retained errors remain errors. Confidence calibration details and additional retained shares are available in the [metrics](metrics.json).', '']
    lines += source()

    lines += [f"## {analysis['composition_headline']}", '',
              'All rows below use the same intersection of evaluated records, including the direct methods. This avoids comparing a small combined-score sample with a larger direct sample.', '']
    shared = [r for r in analysis['shared_results'] if r['context_regime'] == context]
    lines += table(['Workflow', 'Correct / shared records', 'Accuracy', 'Cost / 1,000', 'Tied top scores'], [
        [r['name'], f"{r['correct']} / {r['records']}", percent(r['accuracy']), money(r['cost_per_1000_usd']), f"{r['ties']} / {r['records']}"] for r in shared])
    lines += [analysis['composition_conclusion'], '',
              'Ties mean that the scoring protocol cannot distinguish its highest-ranked candidates, so fixed template order decides the answer. Poor combined-score results are evidence about these tested prompts and scoring rules; they do not establish a general inability of the model to decompose a task.', '']
    lines += table(['Workflow', 'Changed on repeat / checked', 'Changed after reordering / checked'], [
        [r['name'], f"{round(r['repeatability']['at_least_one_change']*r['repeatability']['records'])} / {r['repeatability']['records']}" if r['repeatability']['at_least_one_change'] is not None else 'Not measured',
         f"{round(r['option_order']['prediction_change_rate']*r['option_order']['records'])} / {r['option_order']['records']}" if r['option_order']['prediction_change_rate'] is not None else 'Not measured'] for r in analysis['stability']])
    lines += ['Repeat and order checks use small subsets; zero observed changes do not establish universal stability. Incomplete or failed comparisons are excluded from change rates and counted separately in the metrics.', '']
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
    intro = ("This study maps company financial-statement labels to standard categories using public United States Securities and Exchange Commission (SEC) filings. Company-filed tags supply the answer key. "
             if sec else summary['case'] + ' ')
    intro += 'Jev selects from predefined answers and returns probabilities. We compare it with a conventional language model and programmed rules.'
    if status['mode'] != 'benchmark' or not status['complete']:
        intro += f"\n\n**{verdict['headline']}.** {verdict['result']} {verdict['caveat']}"
    lines = dataset_lines(dataset, intro, summary['dataset'])
    tested = ', '.join(sorted({model_name(m['model']) for m in summary['methods'] if m['method'] != 'rules_baseline'}))
    lines += ['## Tests compare decision workflows', '',
              f'Tested models: {tested}. Direct workflows choose the final category in one call. Combined workflows score wording, position and numerical fit separately, then combine the scores in code. We test bundled and separate calls.', '',
              '- **Direct versus rules:** does a model improve coverage and accuracy at a useful cost and speed?',
              '- **Labels versus context:** do neighbouring lines and numerical context help resolve the mapping?',
              '- **Confidence:** can uncertain answers be deferred to concentrate review on errors?',
              '- **Combined judgments and consistency:** do extra judgments improve the answer, and does it survive repeats and reordered options?', '']
    lines += [f"## {verdict['headline']}", '', verdict['result'], '', verdict['caveat'], '']
    primary = [r for r in analysis['direct_results'] if r['context_regime'] == analysis['preferred_context']]
    conditions = {(r['method'], r['context_regime']): r for r in analysis['direct_results']}
    def accuracy_cell(method, regime):
        row = conditions.get((method, regime))
        return f"{percent(row['accuracy'])} ({row['correct']:,}/{row['records']:,})" if row else 'Not measured'
    lines += table(['Workflow', 'Labels alone', 'With context', 'Cost / 1,000', 'Median response'], [
        [r['name'], accuracy_cell(r['method'], 'label_only'), accuracy_cell(r['method'], 'with_context'),
         money(r['cost_per_1000_usd']), duration(r['median_seconds'])] for r in primary])
    lines += ['Accuracy counts abstentions and failed calls as wrong. Cost and time use the primary input condition shown above; prices are uncached estimates in United States dollars. Timing reflects this run’s concurrent load.', '']
    rules = next((r for r in primary if r['method'] == 'rules_baseline'), None)
    if rules:
        lines += [f"Rules answered {rules['answered']:,}/{rules['records']:,} records at {percent(rules['answered_accuracy'])} accuracy among answers, leaving {rules['abstained']:,} unresolved.", '']
    retained = analysis['confidence_deferral']
    if retained:
        counts = {(r['retained'], r['deferred']) for r in retained}
        if len(counts) == 1:
            kept, deferred = next(iter(counts))
            lines += [f"Keeping each method’s most confident 80% retains {kept:,} records and defers {deferred:,}: " + '; '.join(
                f"{r['name']} leaves {r['errors']} errors ({percent(r['accuracy'])} accuracy)" for r in retained) + '. Each method selects different records; human-review outcomes were not measured.', '']
        else:
            lines += table(['Workflow', 'Retained / deferred', 'Errors retained', 'Accuracy'], [
                [r['name'], f"{r['retained']} / {r['deferred']}", r['errors'], percent(r['accuracy'])] for r in retained])
    shared = [r for r in analysis['shared_results'] if r['context_regime'] == analysis['preferred_context'] and r['method'] != 'rules_baseline']
    if shared:
        lines += [f"The combined-workflow comparison uses the same {shared[0]['records']:,} records for every method:", '']
        lines += table(['Workflow', 'Correct / records', 'Cost / 1,000'], [
            [r['name'].replace('combined scores, one bundled call', 'combined, bundled').replace('combined scores, separate calls', 'combined, separate'),
             f"{r['correct']} / {r['records']}", money(r['cost_per_1000_usd'])] for r in shared])
        lines += [analysis['composition_conclusion'], '']
    direct_stability = [r for r in analysis['stability'] if is_direct(r['method'])]
    if direct_stability and all(r['repeatability']['at_least_one_change'] == 0 and r['option_order']['prediction_change_rate'] == 0 for r in direct_stability):
        lines += ['Direct decisions did not change in the repeat/order checks: ' + '; '.join(
            f"{r['name']} checked {r['repeatability']['records']} repeated and {r['option_order']['records']} reordered records" for r in direct_stability) + '. These small checks do not establish universal stability.', '']
    lines += [f"## {analysis['recommendation_headline']}", '', analysis['recommendation'], '']
    categories = analysis['lowest_jev_categories']
    counterexamples = []
    for j in (r for r in categories if r['method'] == 'jev_direct'):
        for rival in categories:
            if rival['value'] == j['value'] and rival['method'] != 'jev_direct' and rival['accuracy'] > j['accuracy']:
                counterexamples.append((rival['accuracy']-j['accuracy'], j, rival))
    if counterexamples:
        _, j, rival = max(counterexamples, key=lambda item: item[0])
        lines += [f"The aggregate hides weaknesses: for “{j['value'].replace('_', ' ')}”, Jev scored {j['correct']}/{j['records']} versus {rival['name']}'s {rival['correct']}/{rival['records']}. This is a descriptive category check, not proof of a general advantage.", '']
    lines += ['This supports a choice for this task and these configurations. Public filed tags are a proxy answer key; the category-balanced sample does not represent every production workload. Other finance tasks, untested models, integration costs and review costs remain unmeasured.' if sec else 'The findings apply to this task and these configurations. Other tasks, untested models, integration costs and review costs remain unmeasured.', '',
              f"Run {status['run_id']}: {analysis['output_rows']:,} outputs across all variants and checks, {analysis['provider_requests']:,} requests, {analysis['failed_outputs']:,} failed outputs; {money(status.get('known_list_price_cost_usd', 0))} known list-price cost. Unknown-usage outputs: {analysis['unknown_usage_outputs']:,}.", '',
              'Sources: [detailed analysis](details.md), [results and uncertainty](metrics.json), [recommendation evidence](analysis.json), [configuration](resolved_config.yaml). The [historical criterion](criterion-audit.md) is retained for audit; it does not decide the recommendation.']
    return '\n'.join(lines) + '\n'
