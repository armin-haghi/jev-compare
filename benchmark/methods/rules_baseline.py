from benchmark.config import load_case


def predict(payload, candidates, case_config, method_config):
    return load_case(method_config["case"]).rules(payload, candidates, case_config)
