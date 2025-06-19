"""
End-to-End tests for the complete user journey through the Kgents platform.
Tests the integration between auth_service and agent_management_service.
"""
import pytest
import asyncio
import uuid
import time
from httpx import AsyncClient
from fastapi import status


@pytest.mark.e2e
class TestUserAgentJourney:
    """
    End-to-end tests for the complete user journey:
    - Registration
    - Login
    - Agent Creation
    - Agent Deployment
    - Agent Execution
    """
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self, e2e_auth_client, e2e_agent_client):
        """
        Test the complete user journey from registration to agent execution.
        This represents a typical user flow through the Kgents platform.
        """
        # Generate unique identifiers for this test run
        test_id = uuid.uuid4().hex[:8]
        email = f"e2e_test_{test_id}@example.com"
        username = f"e2e_user_{test_id}"
        agent_name = f"Test Agent {test_id}"
        
        # 1. User Registration
        print("Step 1: User Registration")
        register_data = {
            "email": email,
            "password": "SecureP@ssword123",
            "username": username,
            "first_name": "E2E",
            "last_name": "Test"
        }
        
        register_response = await e2e_auth_client.post(
            "/api/v1/auth/users/register",
            json=register_data
        )
        
        assert register_response.status_code == status.HTTP_201_CREATED, \
            f"Registration failed with status {register_response.status_code}: {register_response.text}"
            
        reg_data = register_response.json()
        print(f"Registration successful: {reg_data['message']}")
        
        # 2. User Login
        print("Step 2: User Login")
        login_data = {
            "username": email,
            "password": "SecureP@ssword123"
        }
        
        login_response = await e2e_auth_client.post(
            "/api/v1/auth/users/login",
            data=login_data
        )
        
        assert login_response.status_code == status.HTTP_200_OK, \
            f"Login failed with status {login_response.status_code}: {login_response.text}"
            
        token_data = login_response.json()
        access_token = token_data["access_token"]
        print(f"Login successful, received token: {access_token[:10]}...")
        
        # Auth header for subsequent requests
        auth_header = {"Authorization": f"Bearer {access_token}"}
        
        # 3. Create Agent
        print("Step 3: Create Agent")
        agent_data = {
            "name": agent_name,
            "description": "An agent created in E2E testing",
            "langflow_flow_json": {
                "nodes": [
                    {
                        "id": "node1",
                        "type": "ChatPromptNode",
                        "position": {"x": 100, "y": 100},
                        "data": {
                            "text": "You are a helpful AI assistant created for testing purposes."
                        }
                    },
                    {
                        "id": "node2",
                        "type": "ChatModelNode",
                        "position": {"x": 400, "y": 100},
                        "data": {
                            "model": "gpt-3.5-turbo"
                        }
                    }
                ],
                "edges": [
                    {
                        "source": "node1",
                        "sourceHandle": "output",
                        "target": "node2",
                        "targetHandle": "input"
                    }
                ]
            },
            "is_public": False
        }
        
        create_agent_response = await e2e_agent_client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=auth_header
        )
        
        assert create_agent_response.status_code == status.HTTP_201_CREATED, \
            f"Agent creation failed with status {create_agent_response.status_code}: {create_agent_response.text}"
            
        agent_id = create_agent_response.json()["id"]
        print(f"Agent created successfully with ID: {agent_id}")
        
        # 4. Deploy Agent
        print("Step 4: Deploy Agent")
        deploy_response = await e2e_agent_client.post(
            f"/api/v1/agents/{agent_id}/deploy",
            headers=auth_header
        )
        
        assert deploy_response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED], \
            f"Agent deployment failed with status {deploy_response.status_code}: {deploy_response.text}"
        
        deployment_id = deploy_response.json().get("deployment_id")
        print(f"Agent deployment initiated with ID: {deployment_id}")
        
        # 5. Check Deployment Status (poll until complete)
        print("Step 5: Check Deployment Status")
        deployed = False
        max_retries = 10
        
        for i in range(max_retries):
            print(f"Checking deployment status (attempt {i+1}/{max_retries})...")
            status_response = await e2e_agent_client.get(
                f"/api/v1/agents/{agent_id}/status",
                headers=auth_header
            )
            
            assert status_response.status_code == status.HTTP_200_OK, \
                f"Status check failed with status {status_response.status_code}: {status_response.text}"
            
            deployment_status = status_response.json().get("status")
            print(f"Deployment status: {deployment_status}")
            
            if deployment_status == "deployed":
                deployed = True
                break
            elif deployment_status == "failed":
                pytest.fail("Agent deployment failed")
            
            # Wait before checking again
            await asyncio.sleep(5)
        
        assert deployed, "Agent deployment did not complete within the expected time"
        
        # 6. Send a query to the agent
        print("Step 6: Query Agent")
        query_data = {
            "input": "What's your purpose?"
        }
        
        query_response = await e2e_agent_client.post(
            f"/api/v1/agents/{agent_id}/query",
            json=query_data,
            headers=auth_header
        )
        
        assert query_response.status_code == status.HTTP_200_OK, \
            f"Agent query failed with status {query_response.status_code}: {query_response.text}"
        
        query_result = query_response.json()
        print(f"Agent response: {query_result.get('response')}")
        
        # 7. Verify User Profile Access
        print("Step 7: Verify User Profile")
        profile_response = await e2e_auth_client.get(
            "/api/v1/auth/users/me",
            headers=auth_header
        )
        
        assert profile_response.status_code == status.HTTP_200_OK, \
            f"Profile retrieval failed with status {profile_response.status_code}: {profile_response.text}"
        
        profile_data = profile_response.json()
        assert profile_data["email"] == email
        assert profile_data["username"] == username
        print("User profile verification successful")
        
        # 8. List User's Agents
        print("Step 8: List User's Agents")
        list_response = await e2e_agent_client.get(
            "/api/v1/agents",
            headers=auth_header
        )
        
        assert list_response.status_code == status.HTTP_200_OK, \
            f"Agent listing failed with status {list_response.status_code}: {list_response.text}"
        
        agents = list_response.json()
        assert any(agent["id"] == agent_id for agent in agents), "Created agent not found in user's agents"
        print(f"Found created agent in user's agents list. Total agents: {len(agents)}")
        
        # 9. Delete Agent
        print("Step 9: Delete Agent")
        delete_response = await e2e_agent_client.delete(
            f"/api/v1/agents/{agent_id}",
            headers=auth_header
        )
        
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT, \
            f"Agent deletion failed with status {delete_response.status_code}: {delete_response.text}"
        
        print("Agent successfully deleted")
        
        # 10. Verify Agent Deletion
        print("Step 10: Verify Agent Deletion")
        verify_delete_response = await e2e_agent_client.get(
            f"/api/v1/agents/{agent_id}",
            headers=auth_header
        )
        
        assert verify_delete_response.status_code == status.HTTP_404_NOT_FOUND, \
            "Agent still exists after deletion"
        
        print("E2E test complete: Full user journey verified successfully!")
