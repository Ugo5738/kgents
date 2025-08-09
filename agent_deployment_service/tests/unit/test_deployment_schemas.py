from uuid import uuid4

from agent_deployment_service.schemas.deployment_schemas import DeploymentCreate


def test_deploy_real_agent_defaults_true():
    data = DeploymentCreate(agent_id=uuid4(), agent_version_id=uuid4())
    assert data.deploy_real_agent is True


def test_deploy_real_agent_false_when_provided():
    data = DeploymentCreate(
        agent_id=uuid4(), agent_version_id=uuid4(), deploy_real_agent=False
    )
    assert data.deploy_real_agent is False
