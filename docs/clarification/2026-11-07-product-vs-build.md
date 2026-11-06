# Clarification — ผลิตภัณฑ์กับงานสร้าง project-builder

วันที่: 7 พฤศจิกายน 2026
สถานะ: ข้อตกลงแยกขอบเขตที่ใช้กับ implementation; ข้อความสถานะในเหตุการณ์เดิมเก็บไว้เป็นประวัติ

เจ้าของกำหนดพฤติกรรมของ plugin สำหรับงานที่ plugin จะรับทำ ผู้สร้างนำพฤติกรรมนั้นมาใช้กับการสร้าง plugin เองผิดระดับ และครั้งแรกแก้เพียงเรื่องผู้ทดลอง/Mac แต่ยังเก็บ Stage และ branch workflow ของงานสร้างไว้ จึงยังแก้ไม่ครบ

## ขอบเขตที่ใช้ต่อจากนี้

| เรื่อง | เป็นของอะไร |
| --- | --- |
| ชื่อ project-builder, ใช้เอง/กับเพื่อน, shared core + adapters | ตัวผลิตภัณฑ์ที่ต้องสร้าง |
| Codex/Claude Code/Devin CLI/Desktop Windows/macOS | เป้าหมาย compatibility ของตัวปลั๊กอิน; ไม่ใช่ทุก managed project ต้องรองรับทุกคู่ |
| BA/PM/SA/DL/BE/FE/Data/AI/QA/UX/UI/DevSecOps และการเลือกทีมตาม scope | ความสามารถภายในปลั๊กอิน |
| Agile/Scrum, PoC/MVP/Beta/Final, min of max | กระบวนการที่ปลั๊กอินใช้กับโปรเจ็กต์/ฟีเจอร์ที่รับทำ |
| main/staging/develop และ develop→Stage→feature | Git workflow ที่ปลั๊กอินต้องจัดการให้ managed project |
| เพดานอำนาจสูงสุด PR เข้า staging | hard policy ภายในปลั๊กอินสำหรับ managed projects; ไม่ห้าม push repo ของปลั๊กอินตามที่เจ้าของอนุญาต |
| test matrix >95%, ไม่มี High+ | กฎ QA ที่ปลั๊กอินต้องใช้และผู้สร้างต้องทดสอบว่าใช้ถูก |
| คนจริง 2–3 คน: baseline งานต่อและหลัง Stage | workflow ของ managed project; ไม่ใช่การหาคนมารองรับการเขียนปลั๊กอินทุกช่วง |
| คู่มือรัน local ทุก Stage | ผลส่งมอบของ managed project; ตัวปลั๊กอินมีคู่มือติดตั้ง/ใช้งานของมันเอง |
| environment isolation, Playwright/add-ons, resource cleanup | ความสามารถผลิตภัณฑ์; ผู้สร้างก็ต้องดูแลเครื่องระหว่างทำงานตามปกติ |
| EGM context-rich coordinator/fresh reviewer | แนวทางที่ปลั๊กอินปรับใช้ ไม่ใช่บังคับวิธีสร้างตัวเอง |
| backlog จนจบ Stage | managed-project workflow; ไม่ใช่เหตุผลให้รอแก้ความเข้าใจผิดของผู้สร้าง |
| Native/Subagent-driven, code modules, unit/integration tests, packaging | วิธีสร้างตัวปลั๊กอิน แยกจากวิธีที่ปลั๊กอินจัดทีมให้ลูกค้า |

## หลักฐานว่าผู้สร้างปะปนขอบเขต

อ้างอิงไฟล์ใน worktree ที่กำลังทำงาน; line numbers ตรวจจากไฟล์หลังเพิ่มป้าย superseded:
- แผนเก่า line 76 เลือก “PoC → MVP → Final” สำหรับ repo ของ plugin และบังคับ guide/human feedback ต่อ Stage ของงานสร้าง
- line 84 ให้เจ้าของจัดหาผู้ทดลองจริง 2–3 คนต่อ Stage ของการสร้าง
- line 106 เป็นต้นไป บังคับให้ผู้สร้างใช้ develop → Stage → feature และ Stage exit gate
- แม้คำชี้แจงครั้งแรกที่ line 60 เป็นต้นไปตัด human/hardware blocker ออก ก็ยังเรียก PoC/MVP/Final ว่าจุด implementation และเก็บ **Stage:** ในทุก task อยู่

ไฟล์อ้างอิง: C:/Users/bakao/.codex/worktrees/project-builder-poc/project-builder/docs/superpowers/plans/2026-11-07-project-builder-implementation.md:76, :84, :106 และ :60
นี่เป็นความผิดของการตีความและการวางแผนของผู้สร้าง ไม่ใช่ความกำกวมที่ให้เจ้าของรับผิดชอบ หรือหลักฐานว่าสกิลใดผิด

## เอกสารที่ใช้แทน

- [Product Spec](../product/project-builder-product-spec.md): สิ่งที่ plugin ต้องทำ
- [Build Plan](../development/plugin-build-plan.md): วิธีสร้าง plugin แบบงานวิศวกรรม/Native โดยไม่มี customer Stage บังคับ
- แผนเก่าและ design เดิมเก็บไว้เป็นประวัติ พร้อมป้ายที่ห้ามใช้เป็น execution authority ปัจจุบัน

สถานะ ณ การแก้ความเข้าใจครั้งแรก: ไม่มี subagent กำลังพัฒนาต่อ ไม่ได้รัน tests เพิ่มหรือทำ Git mutation โค้ดและ commits เดิมได้รับการรักษาไว้ ต่อมางานสร้างดำเนินตาม Build Plan ฉบับแก้ไข

คำแก้ไขเพิ่มเติมของเจ้าของ: เพดานสิทธิ์ PR เข้า staging เป็นพฤติกรรมภายใน project-builder ไม่ใช่ข้อจำกัดของงานสร้างปลั๊กอิน เจ้าของอนุญาตให้ push เมื่อเสร็จและตรวจผ่านแล้ว การพัฒนาใช้ shared core + เครื่องมือ native ของ host ไม่ต้องสร้าง executor/sandbox ใหม่เป็นเงื่อนไขที่เจ้าของไม่ได้ขอ
