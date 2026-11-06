"""Local stdio MCP; no network listener and no model-accessible user approval."""
from mcp.server import MCPServer
from .api import invoke

server=MCPServer("project-builder")

@server.tool(description="Manage a local project. Read status/help first. Mutations require a unique request_id and the latest expected_revision; use run_id to bind workers. submit proposes artifacts, qa-review attests QA only. Human reviews use the separate interactive CLI. No shell, remote write or user approval tool.")
def project_builder(project_root:str,intent:str,payload:dict|None=None,request_id:str|None=None,
                    expected_revision:int|None=None,run_id:str|None=None)->dict:
    try:
        return invoke(project_root,intent,payload,request_id=request_id,expected_revision=expected_revision,run_id=run_id)
    except (ValueError,OSError,KeyError,TypeError) as error:
        return {"status":"REJECTED","reason":str(error)}

def main():
    server.run(transport="stdio")
