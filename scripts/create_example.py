"""Create unapproved input templates; no fake human participants or test outcomes."""
import argparse
import json
from pathlib import Path
from project_builder.application.rules import DISCOVERY, TEST_FAMILIES

def create(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    documents={
        "brief":{"answers":{key:"TODO" for key in DISCOVERY},"requirements":[{"id":"R1","summary":"Greeting CLI","acceptance":["--name Ada prints Hello, Ada!"]}],
            "target":"final","stage_options":{},"domains":["cli"],"complexity":"mini","risks":[],"permissions":[],"recipes":[]},
        "matrix":{"revision":1,"requirements":["R1"],"families":{name:{"applicable":False,"reason":"TODO assess applicability"} for name in TEST_FAMILIES},"cases":[]},
        "guide":{"build_sha":"TODO current build","setup_steps":[],"run_steps":[],"stop_steps":[],"cleanup_steps":[]},
        "feedback":{"build_sha":"TODO current build","participants":[],"observations":[]}}
    for name,document in documents.items(): (directory/(name+".json")).write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return directory

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("directory",type=Path);args=parser.parse_args();print(create(args.directory))
