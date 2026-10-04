import pytest
import yaml
from benchmark import datasets
from benchmark.config import read_yaml
from benchmark.runner import run
from tests.fixtures.fake_runtime import FakeRuntime
from tests.fixtures.toy_case import prepare


@pytest.fixture
def toy(tmp_path):
    """A synthetic case, an 8-record dataset drawn from it, and a function that runs models on that dataset."""
    case_config = tmp_path / "case.yaml"
    case_config.write_text(yaml.safe_dump({"processed_dir": str(tmp_path / "data"), "description": "Synthetic fixture."}))
    prepare(read_yaml(case_config))
    config = read_yaml("tests/fixtures/experiment.yaml") | {"case_config": str(case_config)}
    dataset = datasets.create(config["case"], case_config, 8, root=tmp_path / "samples")

    def start(settings=None, dataset_id=dataset, runtime=FakeRuntime, **kwargs):
        return run(settings or config, dataset_id, budget_usd=1, results_root=tmp_path / "results",
                   datasets_root=tmp_path / "samples", runtime_factory=runtime, **kwargs)
    return {"config": config, "dataset": dataset, "case_config": case_config, "root": tmp_path, "run": start}
