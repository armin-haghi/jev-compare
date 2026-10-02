from concurrent.futures import ThreadPoolExecutor
from typesafe_sdk import Score
from benchmark.config import load_case
from .common import combine, state, validate_probabilities


def predict(payload, candidates, case_config, method_config):
    runtime, prompts = method_config["_runtime"], method_config["prompts"]
    questions = {f"{c['id']}__{dimension}": Score(
        instructions=prompts["jev_composite"][dimension].format(candidate_id=c["id"]),
        criteria=prompts["score_levels"])
        for c in candidates for dimension in ("wording", "position")}
    shared_state = state(payload, candidates)
    if method_config["strategy"] == "fanout":
        answers = runtime.jev(shared_state, questions).scores
    else:
        def ask(item):
            key, question = item
            return key, runtime.jev(shared_state, {key: question}).scores[key]
        with ThreadPoolExecutor(max_workers=method_config["question_concurrency"]) as pool:
            answers = dict(pool.map(ask, questions.items()))
    if set(answers) != set(questions):
        raise ValueError("Incomplete Jev score response")
    primary, expected = {}, {}
    for key, answer in answers.items():
        validate_probabilities(answer.probabilities, range(5))
        primary[key] = min(answer.probabilities, key=lambda k: (-answer.probabilities[k], k))
        expected[key] = answer.score
    metadata = load_case(method_config["case"]).metadata_scores(payload, candidates, case_config)
    def components(values, dimension):
        return {c["id"]: values[f"{c['id']}__{dimension}"] for c in candidates}
    secondary = combine(candidates, components(expected, "wording"), components(expected, "position"), metadata)
    return combine(candidates, components(primary, "wording"), components(primary, "position"), metadata,
                   {"expected_variant": secondary.model_dump(), "expected_scores": expected})
