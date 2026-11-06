"""Exercise a real source/frozen stdio process in a disposable owned workspace."""
import argparse
import asyncio
import json
from pathlib import Path
import tempfile
from mcp.client import ClientSession
from mcp.client.stdio import StdioServerParameters,stdio_client

async def smoke(executable,project):
    async with stdio_client(StdioServerParameters(command=str(executable),args=["mcp"])) as streams:
        async with ClientSession(*streams,read_timeout_seconds=15) as client:
            await client.initialize()
            tools=await client.list_tools()
            assert any(t.name=="project_builder" for t in tools.tools)
            async def call(intent,payload=None,revision=None):
                result=await client.call_tool("project_builder",{"project_root":str(project),"intent":intent,"payload":payload or {},
                    "request_id":"smoke-"+intent,"expected_revision":revision})
                assert not result.is_error
                return json.loads(result.content[0].text)
            assert (await call("status"))["status"]=="NOT_INITIALIZED"
            assert not list(project.iterdir())
            state=await call("init",{"kind":"new"})
            state=await call("start",{"description":"Disposable MCP integration fixture"},state["revision"])
            assert state["status"]=="DISCOVERY"
            denied=await call("_record_review",{"approved":True},state["revision"])
            assert denied["status"]=="REJECTED"
            refused=await call("execute",{"recipe_id":"unisolated"},state["revision"])
            assert refused["status"]=="ISOLATION_REQUIRED"
            native=await call("native-plan",{"capabilities":{}},state["revision"])
            assert native["status"]=="NOT_AUTHORIZED"  # No manufactured human kickoff in a release smoke.
            print(json.dumps({"status":"PASS","transport":"stdio","tools":[t.name for t in tools.tools],"observed_state":state["status"],"model_approval":"REJECTED","public_execution":"ISOLATION_REQUIRED","native_route_without_kickoff":"NOT_AUTHORIZED"}))

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("executable",type=Path);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="project-builder-mcp-") as folder:
        asyncio.run(smoke(args.executable.resolve(),Path(folder)))
