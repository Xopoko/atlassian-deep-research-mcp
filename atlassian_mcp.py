from fastmcp.server import FastMCP
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import httpx

class Settings(BaseSettings):
    ATLASSIAN_SITE_URL: str
    ATLASSIAN_EMAIL: str
    ATLASSIAN_API_TOKEN: str

settings = Settings()

client = httpx.AsyncClient(auth=(settings.ATLASSIAN_EMAIL, settings.ATLASSIAN_API_TOKEN))

class SearchResult(BaseModel):
    id: str
    title: str
    text: str

class SearchResultPage(BaseModel):
    results: list[SearchResult]

class FetchResult(BaseModel):
    id: str
    title: str
    text: str
    url: str | None = None
    metadata: dict[str, str] | None = None

def _jira_base_url() -> str:
    return f"{settings.ATLASSIAN_SITE_URL}/rest/api/3"

def _confluence_base_url() -> str:
    return f"{settings.ATLASSIAN_SITE_URL}/wiki/rest/api"

async def _jira_search(query: str) -> list[SearchResult]:
    url = f"{_jira_base_url()}/search"
    params = {"jql": f'text ~ "{query}"', "maxResults": 10}
    r = await client.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    results = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        if isinstance(description, dict):
            description = description.get("content", "")
        results.append(
            SearchResult(
                id=f"jira:{issue['id']}",
                title=summary,
                text=str(description)[:200],
            )
        )
    return results

async def _jira_search_by_jql(jql: str) -> list[SearchResult]:
    url = f"{_jira_base_url()}/search"
    params = {"jql": jql, "maxResults": 10}
    r = await client.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    results = []
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        if isinstance(description, dict):
            description = description.get("content", "")
        results.append(
            SearchResult(
                id=f"jira:{issue['id']}",
                title=summary,
                text=str(description)[:200],
            )
        )
    return results

async def _confluence_search(query: str) -> list[SearchResult]:
    url = f"{_confluence_base_url()}/content/search"
    params = {"cql": f'type=page AND text~"{query}"', "limit": 10, "expand": "excerpt"}
    r = await client.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    results = []
    for page in data.get("results", []):
        title = page.get("title", "")
        excerpt = page.get("excerpt", "")
        results.append(
            SearchResult(
                id=f"confluence:{page['id']}",
                title=title,
                text=excerpt,
            )
        )
    return results

jira_search = _jira_search
confluence_search = _confluence_search

async def jira_fetch(issue_id: str) -> FetchResult:
    url = f"{_jira_base_url()}/issue/{issue_id}"
    r = await client.get(url)
    r.raise_for_status()
    data = r.json()
    fields = data.get("fields", {})
    text = fields.get("description", "")
    if isinstance(text, dict):
        text = text.get("content", "")
    url_web = f"{settings.ATLASSIAN_SITE_URL}/browse/{data['key']}"
    metadata = {
        "status": fields.get("status", {}).get("name", ""),
        "project": fields.get("project", {}).get("key", ""),
    }
    return FetchResult(
        id=f"jira:{issue_id}",
        title=fields.get("summary", ""),
        text=str(text),
        url=url_web,
        metadata=metadata,
    )

async def confluence_fetch(page_id: str) -> FetchResult:
    url = f"{_confluence_base_url()}/content/{page_id}"
    params = {"expand": "body.storage"}
    r = await client.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    body = data.get("body", {}).get("storage", {}).get("value", "")
    url_web = f"{settings.ATLASSIAN_SITE_URL}/wiki{data.get('_links', {}).get('webui', '')}"
    return FetchResult(
        id=f"confluence:{page_id}",
        title=data.get("title", ""),
        text=body,
        url=url_web,
    )

def create_server() -> FastMCP:
    mcp = FastMCP(name="Atlassian Deep Research MCP", instructions="Search Jira issues and Confluence pages")

    @mcp.tool()
    async def search(query: str) -> SearchResultPage:
        ql = query.lower()
        keywords = ["assigned to me", "назначенные на меня", "открытые задачи"]
        if any(k in ql for k in keywords):
            jira_results = await _jira_search_by_jql(
                "assignee = currentUser() AND statusCategory != Done ORDER BY created DESC"
            )
            return SearchResultPage(results=jira_results)
        jira_results = await _jira_search(query)
        conf_results = await _confluence_search(query)
        return SearchResultPage(results=jira_results + conf_results)

    @mcp.tool()
    async def fetch(id: str) -> FetchResult:
        if id.startswith("jira:"):
            return await jira_fetch(id.split(":", 1)[1])
        if id.startswith("confluence:"):
            return await confluence_fetch(id.split(":", 1)[1])
        raise ValueError("unknown id")

    return mcp

if __name__ == "__main__":
    create_server().run(
        transport="sse",
        host="127.0.0.1",
        port=8000,
        path="/sse",
        message_path="/sse",
    )
