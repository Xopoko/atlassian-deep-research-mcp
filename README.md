# Atlassian Deep Research MCP

This project provides a minimal [FastMCP](https://github.com/AtlassianPlatform/fastmcp) server for searching and fetching data from Jira and Confluence. It can be used with ChatGPT Custom Connectors for Deep Research workflows.

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables. The server authenticates with Atlassian Cloud using an API token:

- `ATLASSIAN_SITE_URL` – base URL of your Atlassian Cloud site (e.g. `https://mycompany.atlassian.net`)
- `ATLASSIAN_EMAIL` – the user email associated with the API token
- `ATLASSIAN_API_TOKEN` – an Atlassian API token

These can be placed in a `.env` file or exported in the shell before running the server.

## Run

Start the server with SSE transport:

```bash
python atlassian_mcp.py
```

The server listens on `http://127.0.0.1:8000`.

## Usage

The server exposes two tools compatible with ChatGPT Deep Research Custom Connectors:

- `search(query: str)` – returns Jira issues and Confluence pages matching the query.
- `fetch(id: str)` – fetches the full body and metadata for the given result ID.

IDs returned from `search` are prefixed with `jira:` or `confluence:` to indicate their source.

