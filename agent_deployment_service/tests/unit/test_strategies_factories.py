import pytest

from agent_deployment_service.services.strategies import (
    get_build_strategy,
    get_deployment_strategy,
    CloudRunStrategy,
    CloudBuildStrategy,
    GitHubActionsStrategy,
)


def test_get_build_strategy_github_actions():
    strat = get_build_strategy("github_actions")
    assert isinstance(strat, GitHubActionsStrategy)


def test_get_build_strategy_cloud_build():
    strat = get_build_strategy("cloud_build")
    assert isinstance(strat, CloudBuildStrategy)


def test_get_deployment_strategy_cloud_run():
    strat = get_deployment_strategy("cloud_run")
    assert isinstance(strat, CloudRunStrategy)


@pytest.mark.skip(reason="Kubernetes client may not be installed in test env")
def test_get_deployment_strategy_kubernetes():
    strat = get_deployment_strategy("kubernetes")
    # If it doesn't raise, ensure correct type
    from agent_deployment_service.services.strategies import KubernetesStrategy

    assert isinstance(strat, KubernetesStrategy)
