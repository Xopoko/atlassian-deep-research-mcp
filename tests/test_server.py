import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("ATLASSIAN_SITE_URL", "https://example.atlassian.net")
os.environ.setdefault("ATLASSIAN_EMAIL", "test@example.com")
os.environ.setdefault("ATLASSIAN_API_TOKEN", "token")
import pytest
import httpx
import atlassian_mcp

@pytest.mark.asyncio
async def test_search_combines_jira_and_confluence(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/content/search"):
            return httpx.Response(200, json={"results": [{"id": "2", "title": "Page", "excerpt": "text"}]})
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"issues": [{"id": "1", "fields": {"summary": "Issue", "description": "desc"}}]})
        raise AssertionError("unexpected url " + request.url.path)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(atlassian_mcp, 'client', httpx.AsyncClient(transport=transport))
    results = await atlassian_mcp.jira_search('foo')
    results += await atlassian_mcp.confluence_search('foo')
    assert len(results) == 2

@pytest.mark.asyncio
async def test_fetch_issue(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/issue/1'):
            return httpx.Response(200, json={"key": "TEST-1", "fields": {"summary": "Issue", "description": "desc", "status": {"name": "Open"}, "project": {"key": "TEST"}}})
        raise AssertionError('unexpected url')

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(atlassian_mcp, 'client', httpx.AsyncClient(transport=transport))
    result = await atlassian_mcp.jira_fetch('1')
    assert result.title == 'Issue'
