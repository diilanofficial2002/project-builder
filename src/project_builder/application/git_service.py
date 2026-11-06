"""Allowlisted LOCAL Git mutations. No push, remote creation, protected merge or shell."""
import os
from pathlib import Path
import re
import shutil
import subprocess
from .builds import git_read


class LocalGit:
    def __init__(self, root):
        self.root = Path(root).resolve()
        top = git_read(self.root, ["rev-parse", "--show-toplevel"])
        if not top or Path(top.decode().strip()).resolve() != self.root:
            raise ValueError("select the repository root; initialize Git and an initial commit first")

    def _run(self, *args):
        env = {k:v for k,v in os.environ.items() if not k.startswith("GIT_")}
        result = subprocess.run([shutil.which("git"), "-c", "core.hooksPath="+os.devnull,
            "-c", "core.fsmonitor=false", "-c", "commit.gpgSign=false", "-c", "submodule.recurse=false",
            "-C", str(self.root), *args], env=env, capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        if result.returncode:
            raise ValueError("Git operation stopped; inspect repository status: "+result.stderr.decode(errors="replace")[:1500])
        return result.stdout.decode().strip()

    def _clean(self):
        raw = self._run("status", "--porcelain", "--untracked-files=normal", "--", ".", ":(exclude).project-builder")
        if raw:
            raise ValueError("commit or preserve existing changes before switching/integrating branches")

    def _exists(self, name):
        return git_read(self.root,["show-ref","--verify","refs/heads/"+name]) is not None

    @staticmethod
    def _slug(name):
        if not isinstance(name,str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}",name):
            raise ValueError("use a short lowercase slug with letters, numbers and hyphens")
        return name

    def bootstrap(self):
        self._clean()
        if not git_read(self.root,["rev-parse","--verify","HEAD"]):
            raise ValueError("an initial commit is required; no automatic empty commit")
        for name, base in (("main","HEAD"),("staging","main"),("develop","main")):
            if not self._exists(name):
                self._run("branch",name,base)
        return {"status":"READY","branches":["main","staging","develop"],"remote_writes":"DISABLED"}

    def stage(self, name):
        self._clean(); name="stage/"+self._slug(name)
        if not self._exists("develop"):
            raise ValueError("bootstrap main/staging/develop first")
        if self._exists(name):
            raise ValueError("stage already exists; resume it instead")
        self._run("switch","-c",name,"develop")
        return name

    def feature(self, stage, name):
        self._clean()
        if not isinstance(stage,str) or not stage.startswith("stage/") or not self._exists(stage):
            raise ValueError("feature base must be an existing stage branch")
        slug=self._slug(stage.removeprefix("stage/"))
        name="feature/"+slug+"/"+self._slug(name)
        self._run("switch","-c",name,stage)
        return name

    def _route(self, source, target):
        if target=="develop" and source.startswith("stage/"):
            self._slug(source.removeprefix("stage/")); return
        if target.startswith("stage/") and source.startswith("feature/"+target.removeprefix("stage/")+"/"):
            self._slug(target.removeprefix("stage/")); self._slug(source.rsplit("/",1)[1]); return
        raise ValueError("immutable ceiling/route: only feature→its stage or stage→develop")

    def integrate(self, source, target):
        self._route(source,target); self._clean()
        if not self._exists(source) or not self._exists(target):
            raise ValueError("both branches must already exist")
        self._run("switch",target)
        self._run("merge","--no-edit","--no-ff",source)
        return {"status":"MERGED_LOCAL","source":source,"target":target}

    def delete_feature(self, source, stage):
        self._route(source,stage); self._clean()
        if not source.startswith("feature/"):
            raise ValueError("only disposable feature branches can be deleted")
        if git_read(self.root,["merge-base","--is-ancestor",source,stage]) is None:
            raise ValueError("feature is not fully merged into its stage")
        self._run("switch",stage); self._run("branch","-d",source)
        return {"status":"DELETED_LOCAL","branch":source}
