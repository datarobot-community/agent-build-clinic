# MCP — DataRobot Global MCP

This application uses the **DataRobot Global MCP** for predictive-AI tools (deployment
predictions, etc.). There is no local `mcp_server/` component and no standalone MCP deployment
from this template.

## Configuration

Set these in `.env` (replace `{DATAROBOT_URL}` and `<DATAROBOT_API_TOKEN>`):

```shell
EXTERNAL_MCP_URL=https://{DATAROBOT_URL}/api/v2/genai/globalmcp/mcp
EXTERNAL_MCP_HEADERS={"Authorization": "Bearer <DATAROBOT_API_TOKEN>"}
EXTERNAL_MCP_TRANSPORT=streamable-http
```

- Do **not** set `MCP_DEPLOYMENT_ID` (that targets a separately deployed MCP server).
- The agent composes Global MCP tools with local LangChain tools in `agent/agent/myagent.py`.

See [Connect agentic coding environments to MCP servers](https://docs.datarobot.com/en/docs/agentic-ai/agentic-mcp/agentic-mcp-clients.html)
and [Integrate tools using an MCP server](https://docs.datarobot.com/en/docs/agentic-ai/agentic-mcp/index.html).
