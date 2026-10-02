from pathlib import Path
import pandas as pd
from benchmark.config import load_case, read_yaml
from cases.sec_lines.dataset import records_from_tables, finalise, quarters
from cases.sec_lines.template import mapping, template


def tables():
    sub = pd.DataFrame([dict(adsh="a", cik="1", name="Example", sic="3576", fy="2024",
                             period="20241231", form="10-K", fp="FY")])
    pre = pd.DataFrame([
        dict(adsh="a", report="1", line="1", stmt="IS", plabel="Sales", tag="Revenues", version="us-gaap/2024", negating="0"),
        dict(adsh="a", report="1", line="2", stmt="IS", plabel="Costs", tag="CostOfRevenue", version="us-gaap/2024", negating="1"),
        dict(adsh="a", report="1", line="3", stmt="IS", plabel="Total non-operating", tag="NonoperatingIncomeExpense", version="us-gaap/2024", negating="0"),
    ])
    num = pd.DataFrame([dict(adsh="a", tag=t, version="us-gaap/2024", value=v,
                             ddate="20241231", qtrs="4", coreg="", segments="", uom="USD")
                        for t, v in [("Revenues", "100"), ("CostOfRevenue", "60"), ("NonoperatingIncomeExpense", "-3")]])
    tag = pd.DataFrame([dict(tag=t, version="us-gaap/2024", tlabel=t + " standard", custom="0") for t in pre.tag])
    return sub, pre, num, tag


def test_template_and_contract():
    assert len(template()["lines"]) == 29
    assert mapping()["NonoperatingIncomeExpense"] == "total_nonoperating"
    assert mapping()["OtherNonoperatingIncomeExpense"] == "other_nonoperating"
    load_case("sec_lines")
    assert len(quarters("2021q1", "2026q1")) == 21


def test_numeric_context_and_exclusions():
    sub, pre, num, tag = tables()
    # A dimensional duplicate must not change the consolidated value.
    extra = num.iloc[[1]].copy()
    extra["value"], extra["segments"] = "999", "business=other"
    records, excluded, _ = records_from_tables(sub, pre, pd.concat([num, extra]), tag, {"fiscal_years": [2024]})
    assert not excluded
    cost = records[1]
    assert cost.input["sign"] == "negative"
    assert cost.input["scale_ratio"] == .6
    assert cost.input["lines_above"] == ["Sales"]
    assert cost.input["lines_below"] == ["Total non-operating"]
    extra["segments"] = ""
    records, excluded, _ = records_from_tables(sub, pre, pd.concat([num, extra]), tag, {"fiscal_years": [2024]})
    assert len(records) == 2
    assert excluded[0]["exclusion_reason"] == "ambiguous_value"


def test_custom_namespace_is_not_ground_truth():
    sub, pre, num, tag = tables()
    pre.loc[0, "version"] = "a"
    records, excluded, _ = records_from_tables(sub, pre, num, tag, {"fiscal_years": [2024]})
    assert excluded[0]["exclusion_reason"] == "nonstandard_tag"


def test_latest_filer_label_wins():
    records, _, _ = records_from_tables(*tables(), {"fiscal_years": [2024]})
    old = records[0].model_copy(deep=True)
    old.record_id = "older"
    old.source["fy"] = "2021"
    excluded = []
    kept, _ = finalise(records + [old], excluded)
    assert len(kept) == 3
    assert excluded[0]["record_id"] == "older"
