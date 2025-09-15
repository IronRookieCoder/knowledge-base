"""
API主应用测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from packages.knowledge_api.main import create_app


@pytest.fixture
def test_app():
    """创建测试应用"""
    with patch('packages.knowledge_api.main.db_manager.create_tables', new_callable=AsyncMock):
        app = create_app()
        return app


@pytest.fixture
def client(test_app):
    """创建测试客户端"""
    return TestClient(test_app)


class TestAPIMain:
    """API主应用测试"""

    def test_health_check(self, client):
        """测试健康检查接口"""
        with patch('packages.knowledge_api.routers.health.db_manager.get_session') as mock_session:
            mock_session.return_value.__aenter__.return_value.execute = AsyncMock()

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "services" in data

    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Knowledge Base API"
        assert data["version"] == "1.0.0"

    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options("/api/documents/")

        assert response.status_code == 200
        # 验证CORS相关头存在
        assert "access-control-allow-origin" in response.headers

    def test_error_handling(self, client):
        """测试错误处理"""
        # 测试不存在的端点
        response = client.get("/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_api_documentation(self, client):
        """测试API文档"""
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200

        response = client.get("/openapi.json")
        assert response.status_code == 200