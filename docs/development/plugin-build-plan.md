# project-builder — แผนสร้างตัวปลั๊กอิน

วันที่: 7 พฤศจิกายน 2026 (Asia/Bangkok)
สถานะ: สร้าง release 0.1.0 ด้วย shared core + native host adapters; ผลทดสอบและเป้าหมายที่ยังไม่ได้รันระบุใน verification.md
Product requirements: [Product Spec](../product/project-builder-product-spec.md)

## 1. เป้าหมายและวิธีทำ

สร้าง plugin ที่ติดตั้ง ใช้งาน และพัฒนาต่อได้ สำหรับ Codex, Claude Code, Devin CLI/Desktop บน Windows/macOS ตามความสามารถจริงของ host ใช้แกนกลางร่วมและ adapters

ใช้ **Native development** ได้: ผู้สร้างลงมือเอง ตรวจด้วย tests และ review ที่จำเป็น ไม่ต้องใช้บทบาทครบทั้งองค์กร และไม่ต้องบังคับ fresh implementer/reviewer ทุก task ความสามารถจัดทีมของปลั๊กอินเป็นสิ่งที่จะเขียนให้มัน ไม่ใช่ข้อบังคับว่าต้องใช้ปลั๊กอินจำลองทีมนั้นเพื่อสร้างตัวเอง

ลำดับด้านล่างเป็น work packages ทางวิศวกรรม ไม่มี PoC/MVP/Beta/Final หรือ customer Stage gate ของการสร้างตัวปลั๊กอิน

## 2. ขอบเขตงานสร้าง

| งาน | ผลส่งมอบ | วิธีพิสูจน์ |
| --- | --- | --- |
| A. ทำ product contract ให้ชัด | ข้อกำหนด คำสั่ง สถานะ สิทธิ์ ตัวอย่าง new/takeover/new-version และความหมายของ Stage | ตรวจเทียบคำสั่งเจ้าของ แยก confirmed/proposed/unresolved |
| B. สร้าง shared core | workflow/role instructions, requirement/kickoff handling, state และ command behavior ที่จำเป็น | ทดสอบพฤติกรรมและการกลับมาทำงานต่อจากข้อมูลจริง/fixtures |
| C. สร้าง guards และ integrations | Git routes/authority, QA matrix, runtime isolation, resource ownership/cleanup, tooling และ feedback workflow | ทดสอบทั้งผ่านและปฏิเสธ ใช้ temp repos/processes ที่ควบคุมได้ |
| D. สร้าง host adapters | package/config/entry instructions สำหรับทั้งสาม host และวิธีเรียกที่รองรับ | schema/conformance tests และ smoke ตามเครื่องมือที่มีจริง |
| E. ทดสอบการใช้ร่วมกัน | new project, takeover, new version, queued changes, cancel/resume, missing prerequisites และ failure cleanup | automated integration tests; แยก unit fixture ออกจากผล native ที่รันจริง |
| F. แพ็กและส่งมอบ | installable artifacts/source, คู่มือติดตั้ง/คำสั่ง/ถอนออก/ข้อจำกัด และตัวอย่างใช้งาน | build/install smoke, paths/versions/config ถูกต้อง และ review ผลรวม |

เลือกความซับซ้อนของ core ให้พอดีกับ requirements ใช้โค้ดที่มีอยู่ต่อเมื่อจำเป็นและถูกต้อง การมี Python/MCP/SQLite ที่เขียนไปแล้วไม่ใช่เหตุผลให้บังคับสถาปัตยกรรมนั้นทั้งหมด

## 3. ตัวอย่างการทดสอบโดยไม่สับสนระดับ

| พฤติกรรมที่ต้องสร้างในปลั๊กอิน | สิ่งที่ผู้สร้างทำเพื่อพิสูจน์ |
| --- | --- |
| เลือก Stage ให้น้อยตาม requirement | ป้อนตัวอย่างหลายสภาพความพร้อม แล้วตรวจ Stage path |
| feature แตกจาก Stage และรวมกลับตามกฎ | ใช้ repo ชั่วคราวตรวจ refs/commit graph และกรณีถูกห้าม |
| QA >95% และ High บล็อก | ตรวจ 95%, มากกว่า 95%, High, stale/duplicate/missing results |
| รอ feedback จากคนจริงใน managed project | ทดสอบ workflow เมื่อมี/ไม่มี/ผลไม่ครบ และปฏิเสธผลที่อ้างเป็นคนจริงโดยไม่มีที่มา |
| ทุก Stage มี local guide | ตรวจตัวสร้าง/ตัวตรวจ guide กับ build ของ managed-project fixture |
| แยก environment/เก็บกวาด workload | ใช้ environment และโปรเซสทดลองที่เป็นของชุดทดสอบ ตรวจของที่ต้องรักษาและ cleanup |
| ใช้ host adapters ร่วมกับ core | ตรวจ manifest/invocation/protocol และบันทึก native checks ที่รันจริง |

ตารางนี้ไม่ใช่การอ้างว่าผู้ทดลองใน fixture เป็นคนจริง หรือว่า native test ที่ยังไม่รันผ่านแล้ว

## 4. เกณฑ์เสร็จของงานสร้างปลั๊กอิน

- ความสามารถใน Product Spec ถูก implement หรือมี gap ที่ระบุชัด ไม่ใช้ stub สำเร็จแทนงานที่ยังไม่มี
- ชุดทดสอบที่จำเป็นต่อโค้ด/การเชื่อมต่อผ่าน และข้อผิดพลาดสำคัญที่ตรวจพบได้รับการแก้
- package references/paths/runtime/config ใช้ได้ตามวิธีติดตั้ง ไม่ฝัง path ส่วนตัวของผู้สร้าง
- มีคู่มือติดตั้ง เรียกใช้ รันตัวอย่าง หยุด/cleanup และถอนออกสำหรับผู้ใช้ปลั๊กอิน
- รายงาน compatibility แยก tested / not run / unsupported ตามหลักฐาน ไม่เอาเป้าหมายมานับเป็นผลผ่าน
- ไม่มี workload ชั่วคราวของการสร้างค้างอยู่ ไม่มีการเปลี่ยน global environment ที่ไม่ได้รับอนุญาต
- ส่งมอบ artifacts และคำอธิบายข้อจำกัด; การ publish, push หรือ PR จริงเป็นขอบเขตแยกตามคำสั่งเจ้าของ

ไม่ใช้เกณฑ์ “จบ PoC/MVP/Beta/Final ของตัวปลั๊กอิน”, การหาผู้ทดลอง 2–3 คนต่อช่วงสร้าง หรือการมี Stage branch เป็นเงื่อนไขจบงานสร้าง

## 5. Git และสถานะงานที่ทำไปแล้ว

ใช้ development branch/workspace ตามปกติเพื่อรักษางานเดิม ไม่ยก branch policy หรือเพดาน PR เข้า staging ของ managed projects มาบังคับ repo นี้ เจ้าของอนุญาตให้ push งานสร้างปลั๊กอินเมื่อเสร็จและตรวจผ่านแล้ว

สถานะ ณ ตอนแก้แผนครั้งแรก (ประวัติ ไม่ใช่งานค้างปัจจุบัน):
- contracts/CLI, SQLite state และ policy/inspector มี commits กับผลทดสอบ/รีวิว
- resource supervision เป็นงานค้างที่ยังไม่ commit/รีวิวครบ ไม่ถือว่าเสร็จ
- branch/worktree ที่มีคำว่า poc เป็นร่องรอยของแผนที่ตีความผิด ไม่ใช่ข้อบังคับของแผนแก้
- ก่อนเขียนต่อ ต้องประเมินความจำเป็นของโค้ดเดิมกับ Product Spec ฉบับที่แยกขอบเขตแล้ว

เอกสารแผน 19 งานเดิมถูกระบุ superseded เพื่อไม่ให้การ resume หลังย่อ context กลับไปทำตามแผนผิดอีก

## Native execution map

- A: ตรวจและใช้ foundations เดิมต่อเมื่อเกี่ยวข้อง; contracts/state/policy/resource helpers ผ่าน baseline
- B: application/rules.py, persistence.py, builds.py, workspace.py — managed-project lifecycle, scope freeze, digest-bound user reviews, quality/feedback gates
- C: application/environment.py, git_service.py, execution.py — isolated runtimes, allowed Git routes, owned workloads, evidence producers
- D: transport/server.py + adapters/* + skills/* — common command protocol and host-specific packages
- E: tests/application/, tests/integration/, tests/transport/ — behavior and cross-component failures
- F: packaging/build.py + scripts/ + README + docs/installation/ — installable packages, local example and verified compatibility report

Interfaces ที่ใช้ร่วม: Workspace.status/init/start/submit/continue_run/change/pause/cancel; review_packet/record_review ผ่าน injected user channel; rules.evaluate_quality/select_stages/plan_team; Supervisor/ResourceLedger ที่มีอยู่แล้ว
การตรวจพบว่า MCP elicitation อาจถูก client ที่เป็น agent ตอบเองได้ ต้องไม่ถือว่าการมี elicitation capability เท่ากับพิสูจน์ว่าเป็นคนตอบ; ใช้ trusted host integration ที่ยืนยันได้หรือ fallback การ review ผ่าน local interactive CLI และเปิดเผยข้อจำกัด

## Local release และงานที่ยังไม่รับรอง

Windows host ZIP ทั้งสามพร้อม runtime สร้างและตรวจ schema/checksum; ชุดทดสอบล่าสุด 289 ผ่าน 2 ข้าม และตรวจ executable เชื่อมต่อ MCP จริง ดู docs/installation/verification.md และ docs/development/review-and-decisions.md

งานพัฒนาและทดสอบของ managed project ใช้เครื่องมือ native ของ host ตาม kickoff, resource budget และหลักฐาน lifecycle ไม่ต้องสร้าง runner/sandbox ของปลั๊กอินเองเป็นเงื่อนไขเพิ่ม การอ้างว่าต้องมี standalone driver ก่อนรัน test ใด ๆ เป็นการเพิ่ม scope ของผู้สร้างและถูกแก้แล้ว

ตัวช่วย standalone execute ยัง ISOLATION_REQUIRED และ remote writes ใน runtime ยัง LOCAL_ONLY ส่วน supervisor เป็น lifecycle library ไม่ใช่ sandbox Native macOS/host activation ยัง NOT_RUN ไม่อ้างผลที่ยังไม่ได้ตรวจ การตรวจแพลตฟอร์มเหล่านั้นไม่ใช่ Stage หรือการหาผู้ทดลองสำหรับการสร้างปลั๊กอิน และข้อจำกัด remote ของ managed workflow ไม่ได้ห้าม push development branch ของปลั๊กอินนี้ตามคำสั่งเจ้าของ
