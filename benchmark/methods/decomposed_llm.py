from concurrent.futures import ThreadPoolExecutor
from pydantic import Field, create_model
from benchmark.config import load_case
from .common import combine, state


def predict(payload, candidates, case_config, method_config):
    runtime, prompts = method_config["_runtime"], method_config["prompts"]
    score = create_model("IntegerScore", __config__={"extra": "forbid"},
                         score=(int, Field(ge=0, le=4, strict=True)))
    if method_config["strategy"] == "matrix":
        dimensions = create_model("Dimensions", __config__={"extra": "forbid"},
                                  wording=(int, Field(ge=0, le=4, strict=True)),
                                  position=(int, Field(ge=0, le=4, strict=True)))
        matrix = create_model("CandidateScores", __config__={"extra": "forbid"},
                              **{c["id"]: (dimensions, ...) for c in candidates})
        result = runtime.llm(prompts["decomposed_llm"]["system"],
                             state(payload, candidates) | {"rubric": prompts["score_levels"]}, matrix)
        wording = {c["id"]: getattr(result, c["id"]).wording for c in candidates}
        position = {c["id"]: getattr(result, c["id"]).position for c in candidates}
    else:
        def question(task):
            candidate, dimension = task
            text = prompts["jev_composite"][dimension].format(candidate_id=candidate["id"])
            result = runtime.llm(prompts["decomposed_llm"]["system"],
                                 state(payload, candidates) | {"question": text, "rubric": prompts["score_levels"]}, score)
            return candidate["id"], dimension, result.score
        with ThreadPoolExecutor(max_workers=method_config["question_concurrency"]) as pool:
            values = list(pool.map(question, [(c, d) for c in candidates for d in ("wording", "position")]))
        wording = {key: value for key, dim, value in values if dim == "wording"}
        position = {key: value for key, dim, value in values if dim == "position"}
    metadata = load_case(method_config["case"]).metadata_scores(payload, candidates, case_config)
    return combine(candidates, wording, position, metadata)
