# project-builder

ปลั๊กอินทีม AI สำหรับ Codex, Claude Code และ Devin บน CLI/Desktop ใช้แกนกลางร่วมกันและ adapter ของแต่ละ host เพื่อรับงานใหม่ งานไม่เสร็จ และเวอร์ชันใหม่

เลือกบทบาทและจำนวน Stage ตามขนาดงาน เก็บ state เพื่อ resume, freeze kickoff จาก business ถึง technical, เก็บไอเดียเพิ่มเป็น backlog จนจบ Stage, ตรวจ QA matrix >95% โดยไม่มี High ขึ้นไป และเตรียม guide/feedback ของผู้ใช้จริง แยก environment และ cleanup resource ที่เป็นของงานเท่านั้น

**PoC/MVP/Beta/Final เป็น Stage ของโปรเจ็กต์ที่ปลั๊กอินรับทำ** แผนสร้างปลั๊กอินใช้ Native development ตาม [Build plan](docs/development/plugin-build-plan.md)

- [ติดตั้งและเริ่มใช้งาน](docs/installation/README.md)
- [Artifacts และ API](docs/installation/artifacts-and-api.md)
- [Product specification](docs/product/project-builder-product-spec.md)
- [Shared coordinator instructions](plugin/references/workflow.md)
- [Compatibility / verification](docs/installation/verification.md)

เริ่มจาก source: `uv sync --locked --group dev` แล้วใช้ `.venv/Scripts/python -m project_builder help` บน Windows หรือ `.venv/bin/python -m project_builder help` บน macOS Runtime ที่ bundle มาจะใช้ interpreter ของปลั๊กอินเอง ไม่บังคับ Python version ของโปรเจ็กต์ลูกค้า

สร้าง native runtime บน OS เป้าหมายด้วย `python scripts/build_runtime.py` แล้วแพ็กด้วย `python scripts/build_packages.py --runtime build/runtime/project-builder --output dist/release --platform windows-x64` (เลือก macos-arm64/macos-x64 ตามเครื่องจริง) อ่านรายละเอียดในคู่มือติดตั้งก่อนรัน

Public recipe execution ยังปิดไว้จนมี driver ที่แยก Git/credential/filesystem/network ได้จริง ตัว supervisor จัดการ lifecycle เป็น library ที่ทดสอบแล้วและไม่ถือว่าเป็น sandbox

เพดานที่ออกแบบไว้สูงสุดคือการเปิด PR เข้า staging ตัว runtime ไม่รองรับ merge staging, protected push, PR main หรือ deploy prod รุ่นนี้ปิด remote writes เมื่อยังพิสูจน์ credential/workflow containment ไม่ได้ และส่ง PR draft ให้เจ้าของดำเนินการเอง ไม่อ้างว่า skill สามารถ sandbox เครื่องมืออื่นของ host ที่มีสิทธิ์นอก runtime ได้
