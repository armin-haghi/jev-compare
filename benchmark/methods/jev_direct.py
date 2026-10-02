from typesafe_sdk import Choice
from benchmark.schemas import MethodResult
from .common import state, validate_probabilities


def predict(payload, candidates, case_config, method_config):
    questions = {"line": Choice(instructions=method_config["prompts"]["jev_direct"]["instructions"],
                               criteria={c["id"]: c["description"] for c in candidates})}
    response = method_config["_runtime"].jev(state(payload, candidates), questions)
    answer = response.choices["line"]
    validate_probabilities(answer.probabilities, [c["id"] for c in candidates])
    return MethodResult(prediction=answer.choice, confidence=answer.confidence,
                        confidence_kind="jev_choice_confidence",
                        probability_of_prediction=answer.probabilities[answer.choice],
                        diagnostics={"probabilities": answer.probabilities, "distribution": answer.probabilities})
