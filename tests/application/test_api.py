import json
import pytest


def test_cli_init_start_change_continue_survive_separate_invocations(tmp_path,capsys):
    from project_builder.cli import main
    def call(*args):
        assert main([*args,"--project",str(tmp_path),"--json"]) == 0
        return json.loads(capsys.readouterr().out)
    assert call("init")["status"] == "INITIALIZED"
    run=call("start","Build a tool")["data"]["run_id"]
    assert call("change","Add export")["status"] == "QUEUED"
    assert call("continue")["data"]["run_id"] == run
    assert call("backlog")["data"]["items"][0]["text"] == "Add export"


def test_wire_mutations_need_fresh_revision_and_cannot_forge_review(tmp_path):
    from project_builder.transport.api import invoke
    assert invoke(tmp_path,"init",{"kind":"new"})["status"] == "INITIALIZED"
    with pytest.raises(ValueError):
        invoke(tmp_path,"start",{"description":"Build"},request_id="r1")
    first=invoke(tmp_path,"start",{"description":"Build"},request_id="r1",expected_revision=1)
    assert invoke(tmp_path,"start",{"description":"Build"},request_id="r1",expected_revision=1)==first
    with pytest.raises(ValueError):
        invoke(tmp_path,"_record_review",{"approved":True},request_id="r2",expected_revision=2)
    with pytest.raises(ValueError):
        invoke(tmp_path,"pause",{"approved":True},request_id="r2",expected_revision=2)


def test_mcp_tool_returns_real_state_and_no_user_approval_tool(tmp_path):
    import asyncio
    from project_builder.transport.server import server
    async def scenario():
        result=await server.call_tool("project_builder",{"project_root":str(tmp_path),"intent":"status","payload":{}})
        assert not result.is_error
        assert "NOT_INITIALIZED" in result.content[0].text
        tools=await server.list_tools()
        assert all(t.name!="approve" for t in tools)
    asyncio.run(scenario())
