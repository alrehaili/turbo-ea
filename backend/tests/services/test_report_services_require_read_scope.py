"""Guard: every report service that reads cards *requires* a read scope.

Security remediation SEC-2 (findings S-01..S-22) made ``read_scope`` a
required keyword-only parameter of each shared report helper, so a new call
site cannot forget it — it would fail with a ``TypeError`` on its first call.
This pins that shape: giving the parameter a default (``read_scope=None``) would
silently reopen the disclosure for every caller that omits it.
"""

from __future__ import annotations

import inspect

import pytest

from app.services import (
    data_flow_service,
    freshness_service,
    impact_service,
    integration_status_service,
    nora_landscape,
    reference_models,
    resilience_service,
    strategy_map_service,
    tech_standards_scan,
)
from app.services.card_read_scope import CardReadScope

SCOPED = [
    impact_service.gather_impact,
    strategy_map_service.gather_strategy_map,
    freshness_service.gather_freshness,
    resilience_service.gather_resilience,
    data_flow_service.gather_data_flow,
    integration_status_service.gather_integration_status,
    tech_standards_scan.scan_standard_compliance,
    reference_models.scan_domain_card_codes,
    reference_models.explicit_mappings_for_model,
    nora_landscape.resolve_segment,
    nora_landscape.plateau_landscape,
]


@pytest.mark.parametrize("fn", SCOPED, ids=lambda f: f"{f.__module__}.{f.__name__}")
def test_read_scope_is_a_required_keyword(fn):
    param = inspect.signature(fn).parameters.get("read_scope")
    assert param is not None, f"{fn.__name__} takes no read_scope"
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is inspect.Parameter.empty, f"{fn.__name__}: read_scope has a default"
    assert param.annotation in (CardReadScope, "CardReadScope")
