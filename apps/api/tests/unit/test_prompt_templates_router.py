"""
Unit tests for prompt templates router (api/routers/prompt_templates.py).

Tests cover:
- List prompt templates endpoint
- Apply prompt template endpoint
- Error handling (not found, invalid variables)
"""

from unittest.mock import patch

import pytest
from fastapi import status

from api.routers.prompt_templates import router as prompt_templates_router


class MockPromptTemplate:
    """Mock prompt template for testing."""

    def __init__(
        self,
        tmpl_id="test-1",
        title="Test Template",
        category="test",
        description="A test template",
        template_text="Hello {{name}}",
        variables=None,
    ):
        self.id = tmpl_id
        self.title = title
        self.category = category
        self.description = description
        self.template_text = template_text
        self.variables = variables or []


class MockTemplateVariable:
    """Mock template variable for testing."""

    def __init__(
        self, name="test_var", description="A test variable", required=True, example="example"
    ):
        self.name = name
        self.description = description
        self.required = required
        self.example = example


class TestListPromptTemplates:
    """Test list prompt templates endpoint."""

    @pytest.mark.asyncio
    @patch("api.routers.prompt_templates.get_prompt_templates")
    async def test_list_templates_returns_empty_list(self, mock_get_templates):
        """Test that list templates returns empty list when no templates exist."""
        mock_get_templates.return_value = []

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(prompt_templates_router)

        client = TestClient(test_app)
        response = client.get("/prompt-templates")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    @patch("api.routers.prompt_templates.get_prompt_templates")
    async def test_list_templates_returns_templates(self, mock_get_templates):
        """Test that list templates returns templates with correct structure."""
        # Create mock templates
        tmpl1 = MockPromptTemplate(
            tmpl_id="test-1",
            title="Template 1",
            category="search",
            description="First template",
            template_text="Test",
            variables=[MockTemplateVariable()],
        )
        tmpl2 = MockPromptTemplate(
            tmpl_id="test-2",
            title="Template 2",
            category="analysis",
            description="Second template",
            template_text="Test 2",
        )
        mock_get_templates.return_value = [tmpl1, tmpl2]

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(prompt_templates_router)

        client = TestClient(test_app)
        response = client.get("/prompt-templates")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["id"] == "test-1"
        assert data[0]["title"] == "Template 1"
        assert data[0]["category"] == "search"
        assert "variables" in data[0]
        assert len(data[1]["variables"]) == 0


class TestApplyPromptTemplate:
    """Test apply prompt template endpoint."""

    @pytest.mark.asyncio
    @patch("api.routers.prompt_templates.get_prompt_template_by_id")
    @patch("api.routers.prompt_templates.render_prompt_template")
    async def test_apply_template_success(self, mock_render, mock_get_template):
        """Test that apply template returns rendered text."""
        # Setup mock template
        mock_template = MockPromptTemplate(
            tmpl_id="test-1",
            title="Test",
            category="test",
            description="Test template",
            template_text="Hello {{name}}",
            variables=[MockTemplateVariable()],
        )
        mock_get_template.return_value = mock_template
        mock_render.return_value = "Hello World"

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(prompt_templates_router)

        client = TestClient(test_app)
        request_body = {
            "template_id": "test-1",
            "variables": {"name": "World"},
        }
        response = client.post("/prompt-templates/apply", json=request_body)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["template_id"] == "test-1"
        assert data["rendered_text"] == "Hello World"

    @pytest.mark.asyncio
    @patch("api.routers.prompt_templates.get_prompt_template_by_id")
    async def test_apply_template_not_found(self, mock_get_template):
        """Test that apply template returns 404 for invalid template."""
        mock_get_template.return_value = None

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(prompt_templates_router)

        client = TestClient(test_app)
        request_body = {
            "template_id": "nonexistent",
            "variables": {},
        }
        response = client.post("/prompt-templates/apply", json=request_body)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    @patch("api.routers.prompt_templates.get_prompt_template_by_id")
    @patch("api.routers.prompt_templates.render_prompt_template")
    async def test_apply_template_invalid_variables(self, mock_render, mock_get_template):
        """Test that apply template returns 400 for invalid variables."""
        mock_template = MockPromptTemplate(
            tmpl_id="test-1",
            title="Test",
            category="test",
            description="Test template",
            template_text="Hello {{name}}",
        )
        mock_get_template.return_value = mock_template
        mock_render.side_effect = ValueError("Invalid variable")

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(prompt_templates_router)

        client = TestClient(test_app)
        request_body = {
            "template_id": "test-1",
            "variables": {"invalid": "value"},
        }
        response = client.post("/prompt-templates/apply", json=request_body)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    @patch("api.routers.prompt_templates.get_prompt_template_by_id")
    @patch("api.routers.prompt_templates.render_prompt_template")
    async def test_apply_template_rendering_error(self, mock_render, mock_get_template):
        """Test that apply template returns 500 for rendering errors."""
        mock_template = MockPromptTemplate(
            tmpl_id="test-1",
            title="Test",
            category="test",
            description="Test template",
            template_text="Hello {{name}}",
        )
        mock_get_template.return_value = mock_template
        mock_render.side_effect = Exception("Rendering failed")

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        test_app = FastAPI()
        test_app.include_router(prompt_templates_router)

        client = TestClient(test_app)
        request_body = {
            "template_id": "test-1",
            "variables": {"name": "World"},
        }
        response = client.post("/prompt-templates/apply", json=request_body)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data


class TestPromptTemplatesRouterConstants:
    """Test prompt templates router configuration."""

    def test_router_tag(self):
        """Test that router has correct tag."""
        assert prompt_templates_router.tags == ["Prompt Templates"]

    def test_router_prefix(self):
        """Test that router endpoints are configured."""
        # Router should have endpoints registered
        assert len(prompt_templates_router.routes) >= 2
