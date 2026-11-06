# ติดตั้งและใช้ project-builder

ปลั๊กอินใช้ AI และเครื่องมือของ Codex, Claude Code หรือ Devin ที่คุณมีอยู่แล้ว แกนกลางเดียวจัดการ requirement, state, Stage ของโปรเจ็กต์, QA, backlog และ resource ไม่มีค่า API เพิ่มจากบริการ LLM ของปลั๊กอินเอง

## Windows: แพ็กเกจพร้อม runtime

1. เลือก ZIP ของ host ที่ใช้ ตรวจ SHA256 กับ SHA256SUMS.txt แล้วแตกไฟล์ เก็บโฟลเดอร์ `project-builder` ทั้งโฟลเดอร์ไว้ในตำแหน่งถาวร ไม่มีการแก้ Python/PATH ของเครื่อง
2. ทดสอบใน PowerShell (เปลี่ยน path เป็นตำแหน่งจริง):

   ```powershell
   & 'C:\Plugins\project-builder\runtime\project-builder.exe' help
   & 'C:\Plugins\project-builder\runtime\project-builder.exe' doctor --project 'C:\Projects\my-app' --json
   ```

3. ติดตั้งโฟลเดอร์ปลั๊กอินผ่านระบบของ host ตามด้านล่าง แล้วเปิด session ใหม่ ตรวจว่ามี skills และ MCP tool `project_builder`
4. เริ่มด้วย init → start คำสั่งของ host จะรับภาษาธรรมชาติและใช้แกนกลางเดียวกัน

Windows executable ยังไม่ได้เซ็นใบรับรองดิจิทัล ตรวจสอบแหล่งที่มาและ checksum ตามวิธีปกติของเครื่องคุณ คู่มือนี้ไม่สั่งปิดระบบป้องกันของ OS

## Host adapters

| Host | วิธีโหลด | การเรียกใช้ |
| --- | --- | --- |
| Codex CLI/Desktop | เพิ่มผ่าน local marketplace ของ Codex หรือ directory UI ของ Desktop โดยใช้โฟลเดอร์แพ็กเกจ Codex | เลือก skill init/start/continue/status ของ Project Builder จาก skill picker; ใช้ชื่อ mention ที่ host แสดง |
| Claude Code | CLI ทดลองด้วย `claude --plugin-dir /absolute/path/project-builder`; แจกใช้ถาวรผ่าน local/private marketplace ตามระบบของ Claude | `/project-builder:init`, `/project-builder:start`, `/project-builder:continue`, `/project-builder:status` |
| Devin CLI/Desktop | ติดตั้ง local folder ด้วยระบบ plugins ของ Devin; ดู `devin plugins --help` ของรุ่นที่ติดตั้ง | `/project-builder:init`, `/project-builder:start`, `/project-builder:continue`, `/project-builder:status` |

Codex รุ่นที่ตรวจในเครื่องนี้มี `codex plugin marketplace add PATH` และ `codex plugin add project-builder@MARKETPLACE` ดูตัวอย่าง marketplace.json ในไฟล์ examples แล้วแก้ source.path ให้ชี้โฟลเดอร์ plugin เทียบกับ marketplace root ก่อนลงทะเบียน ไม่แก้ config ของ host อัตโนมัติ

ชื่อคำสั่ง namespace เป็นสัญญาของผู้ใช้; syntax ของ Codex ใช้ picker/mention ตาม host ไม่สมมติว่ารองรับทุก slash command เหมือน Claude/Devin หน้า Desktop ใช้ plugin loader ของ host เอง ไม่มีแอป Desktop ใหม่ในแพ็กเกจนี้

## macOS และการรันจาก source

ยังไม่มีการรัน native macOS บนเครื่องนี้ สร้าง runtime บน Mac ตามขั้นตอนต่อไป ห้ามนำ Windows executable ไปเปลี่ยนชื่อเป็น Mac binary

1. ตรวจ source และ runtime pin ใน pyproject.toml (ตอนนี้ Python 3.14.4 สำหรับ **ตัวปลั๊กอิน**) ใช้ interpreter ที่ตรงอยู่แล้ว หรือกำหนด pyenv แบบ project-local ตามเอกสารทางการ ไม่แทนที่ system Python
2. สร้าง environment ของปลั๊กอิน: `python -m venv .venv` ใช้ `.venv/bin/python` บน Mac หรือ `.venv\Scripts\python.exe` บน Windows
3. หากมี uv ใช้ `uv sync --locked --group dev` ใน repo นี้ มันติดตั้ง dependencies ใน environment ของ repo; ตรวจ lockfile ก่อนรัน ไม่มีการติดตั้ง package แบบ global โดยสคริปต์ของเรา
4. รัน `.venv/bin/python -m project_builder help` และ `.venv/bin/python -m pytest -q -W error`
5. สร้าง runtime ด้วย `.venv/bin/python scripts/build_runtime.py` จากนั้นใช้ `scripts/build_packages.py --runtime build/runtime/project-builder --output dist/macos-release --platform macos-arm64` (หรือ macos-x64 ตามเครื่องจริง)
6. หลังแตก ZIP บน Mac อาจต้องคืน executable bit ให้ `runtime/project-builder` ด้วย `chmod +x` ตรวจ signature/quarantine ตามนโยบายเครื่องก่อนรัน

macOS recipe driver รองรับเฉพาะ cooperative process group ที่ผู้ใช้รีวิวแล้ว งานที่ daemonize/detach ไม่ได้รับอนุญาต อย่ารายงานว่าทดสอบ native หรือรับประกัน containment แบบ Windows จนมีหลักฐานจริง

## เริ่มโปรเจ็กต์ที่ปลั๊กอินรับทำ

```powershell
$pb = 'C:\Plugins\project-builder\runtime\project-builder.exe'
& $pb init --project 'C:\Projects\my-app' --kind takeover --json
& $pb start 'พัฒนาแอปเดิมต่อ' --project 'C:\Projects\my-app' --json
& $pb discovery --project 'C:\Projects\my-app' --json
& $pb status --project 'C:\Projects\my-app' --json
```

ใช้ `new` สำหรับเริ่มจากศูนย์, `takeover` สำหรับงานไม่เสร็จ, `new-version` สำหรับเวอร์ชันใหม่ บน takeover/new-version ทีมจะเตรียม baseline ของผู้ใช้จริงก่อน kickoff ห้ามนำเงื่อนไขนี้มาบังคับกระบวนการสร้างปลั๊กอินเอง

AI host จะถาม requirement จาก business ถึง technical, เสนอทีมและจำนวน Stage ที่จำเป็น และจัดเตรียม kickoff packet เมื่อข้อมูลครบ ผู้ใช้รีวิวครั้งนี้กับขอบเขตและสิทธิ์ที่จะให้ทีมทำต่อ ไม่ต้องตอบคำถามตามทุก task ใช้เอกสาร [Artifacts และ API](artifacts-and-api.md) สำหรับไฟล์ตัวอย่างและข้อกำหนด

## การรีวิวของผู้ใช้และทีม

ทีมแสดง packet/digest ที่ตรวจได้ เช่น `review-packet kickoff --project PATH --json` จากนั้น **คุณเอง** เปิด terminal แบบ interactive รัน `review kickoff --digest DIGEST --project PATH` อ่าน packet แล้วพิมพ์ digest เพื่อยืนยัน ปฏิเสธได้ด้วย Enter ไม่มี --yes และไม่รับ approved=true จาก MCP ใช้วิธีเดียวกันสำหรับ baseline, feedback และ handoff

QA ใช้ `qa-review matrix|quality|guide --digest DIGEST --notes 'ผู้ตรวจ/หลักฐาน/ผลการตรวจ'` การตรวจเหล่านี้เป็นงานของทีมในสิทธิ์ที่ตกลงไว้ ไม่ขอผู้ใช้อนุมัติทุกผลเทส

การพิสูจน์ว่าเป็นมนุษย์เป็นขอบเขตความเชื่อถือของช่องทาง terminal นี้ ไม่ใช่ระบบยืนยันตัวบุคคลทางไกล MCP elicitation ทั่วไปอาจมี AI ตอบ จึงไม่ถือว่าเป็นหลักฐานคนตอบ

## ขอบเขตสิทธิ์และการหยุด

runtime รองรับ local Git ตามเส้นทาง feature → Stage → develop และปฏิเสธการ merge/push เข้า protected branch ที่มีอยู่ ปัจจุบัน remote writes ทั้งหมดปิดไว้ เมื่อผู้ให้บริการ/credential containment ยังพิสูจน์ไม่ได้ ทีมทำ PR draft ให้เจ้าของเผยแพร่เอง เพดานที่ออกแบบไว้สูงสุดคือเปิด PR เข้า staging และไม่เปิดทาง merge staging/PR เข้า main/deploy prod

ปลั๊กอินไม่ใช่ OS sandbox สำหรับเครื่องมืออื่นที่ host มีสิทธิ์อยู่แล้ว อย่าอ้างว่าสามารถห้ามคำสั่งที่รันนอก runtime ได้ทั้งหมด และห้ามให้ coordinator ใช้ shell/connector/agent อื่นเลี่ยงข้อจำกัด

`pause`/`stop` และ `cancel` checkpoint ทันทีและขอ cleanup เฉพาะของ project นี้ `cleanup` ไม่ลบ code, guide, test evidence หรือ environment ที่ใช้ซ้ำได้ อย่าลบ .project-builder ระหว่างมีงานค้าง `operations` แสดงงานที่ผลยัง UNKNOWN; ตรวจ Git/ผลข้างเคียงจริงและ cleanup ก่อนรีวิว `recovery` เพื่อยอมรับว่าการทำงานเดิมยัง NOT_VERIFIED แล้วทดสอบใหม่ วิธีนี้ไม่ประกาศผลสำเร็จที่ไม่มีหลักฐานและไม่ replay mutation เดิมอัตโนมัติ

ถอนการติดตั้งด้วยระบบ host ปิด session เพื่อหยุด MCP process แล้วลบโฟลเดอร์แพ็กเกจเมื่อไม่ใช้ เก็บ .project-builder ของโปรเจ็กต์ไว้หากต้อง resume และอย่าลบ resource ledger ส่วนกลางขณะมี lease ค้าง

## แหล่งอ้างอิงสำหรับผู้ดูแล

[OpenAI plugins](https://developers.openai.com/plugins/build/plugins), [Claude plugin reference](https://code.claude.com/docs/en/plugins-reference), [Devin plugins](https://docs.devin.ai/cli/extensibility/plugins/overview), [pyenv](https://github.com/pyenv/pyenv), [pyenv-win](https://github.com/pyenv-win/pyenv-win), [Playwright](https://playwright.dev/docs/intro), [PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html)
