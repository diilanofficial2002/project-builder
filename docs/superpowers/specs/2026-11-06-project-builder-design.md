# project-builder — เอกสารออกแบบ v0.4

วันที่: 6 พฤศจิกายน 2026 (Asia/Bangkok)  
ปรับปรุงล่าสุด: 7 พฤศจิกายน 2026 (Asia/Bangkok)  
สถานะ: Approved design v0.4 — เจ้าของตอบ “โอเค” ยืนยันแบบวันที่ 7 พฤศจิกายน 2026; ยืนยันแผนสร้างแล้ว เริ่ม execution แบบ Subagent-driven  
ขอบเขตเอกสาร: Product/workflow/architecture design ไม่ใช่ตัวปลั๊กอินที่ติดตั้งใช้งานได้  
สถาปัตยกรรมที่ผู้ใช้เลือก: แกนกลางเดียว พร้อมตัวเชื่อมต่อ Codex, Claude Code และ Devin


คำชี้แจงเจ้าของระหว่างเริ่มสร้าง: ข้อกำหนดทดลองคนจริงเป็นหน้าที่ของ project-builder ต่อโปรเจ็กต์ที่รับทำ การสร้างตัวปลั๊กอินในแชตนี้ไม่บังคับให้เจ้าของเตรียมผู้ทดลองหรือเครื่อง Mac ก่อนทำโค้ดให้เสร็จ ผู้สร้างต้อง implement/test พฤติกรรมนั้นและรายงาน native compatibility ตามหลักฐานจริง รายละเอียด execution นี้อยู่ในแผนสร้าง

## 1. เป้าหมายและเหตุผล

สร้างปลั๊กอินสำหรับเจ้าของและเพื่อน ให้ AI agents ทำงานเสมือนทีมส่งมอบซอฟต์แวร์ที่มีความรับผิดชอบตั้งแต่ธุรกิจจนถึงงานเทคนิค รับได้ทั้งโปรเจ็กต์ใหม่ งานค้าง และเวอร์ชันใหม่ของระบบเดิม ผู้ใช้ตกลงขอบเขตก่อนเริ่มแต่ละ Stage แล้วทีมทำงานต่อเนื่องจนมีผลงานที่ตรวจรับได้

ความสำเร็จคือส่งงานตรง requirement มีหลักฐานคุณภาพ มีคู่มือรัน local ทุก Stage รับช่วงงานต่อได้ และควบคุมอำนาจกับทรัพยากรเครื่องได้จริง ทีมและกระบวนการต้องพอดีกับขนาดและความเสี่ยงของงาน เช่น มินิโปรเจ็กต์มหาวิทยาลัยไม่ต้องใช้ทุกบทบาทหรือกระบวนการระดับองค์กรใหญ่

## 2. แหล่งที่มาของการตัดสินใจ

คำว่า **ยืนยันแล้ว** หมายถึงข้อกำหนดจากผู้ใช้ คำว่า **ข้อเสนอ** หมายถึงการตัดสินใจของผู้ออกแบบที่รอรีวิวเอกสาร ห้ามนำข้อเสนอไปอ้างว่าได้รับการยืนยันแล้ว

| ID | ข้อกำหนดที่ยืนยันแล้ว |
| --- | --- |
| C01 | ชื่อ project-builder สำหรับเจ้าของและเพื่อน |
| C02 | รองรับ Codex, Claude Code, Devin เฉพาะ CLI/Desktop บน Windows และ macOS ในรุ่นแรก |
| C03 | ใช้แกนกลางเดียว พร้อมตัวเชื่อมต่อแต่ละแพลตฟอร์ม |
| C04 | มี BA, PM, SA, DL (Development Lead), BE, FE, Data Engineer, AI Engineer, QA(SIT/UAT), UX/UI Designer, DevSecOps |
| C05 | แยก agent เฉพาะเมื่อจำเป็น จัดและบริหารทีมตาม scope และทรัพยากร |
| C06 | รองรับงานเริ่มจากศูนย์ รับงานไม่เสร็จ และพัฒนาเวอร์ชันใหม่ |
| C07 | ใช้ Agile/Scrum และแบ่งการทำงานเป็น Stage ของโปรเจ็กต์หรือฟีเจอร์ |
| C08 | ประเมิน PoC/MVP/Beta/Final ทุกครั้ง ใช้ Stage น้อยที่สุดตามฟีเจอร์ที่ใช้งานจริงเทียบกับ requirement |
| C09 | ตรวจหรือสร้าง main, staging, develop ก่อนเริ่มพัฒนา |
| C10 | เส้นทางแตก branch คือ develop → Stage branch → feature branch; รวมกลับ feature → Stage → develop |
| C11 | เก็บ Stage branches และเลิกเก็บ feature branches เมื่อรวมงานครบแล้ว |
| C12 | Final ต้องผ่าน test cases มากกว่า 95% ตาม matrix ที่ครอบคลุมประเภทการทดสอบที่จำเป็น |
| C13 | Final ต้องไม่มีปัญหาระดับ High ขึ้นไปค้างอยู่ |
| C14 | ตกลงอำนาจก่อนเริ่มงาน เพดานสูงสุดคือเปิด PR เข้า staging; คำสั่งผู้ใช้เพิ่มเพดานไม่ได้ |
| C15 | ควบคุมทรัพยากรที่รันอยู่ และเก็บกวาดสิ่งชั่วคราวเมื่อเลิกใช้ |
| C16 | มีหรือรู้วิธีใช้ Playwright และ add-on ที่จำเป็นต่อ UX/UI/design/testing |
| C17 | ทุก Stage มี user guide สำหรับรัน local |
| C18 | Kickoff ต้องรีวิวครบจาก business level ถึง technical level; การเก็บ requirement ต้องซักให้ได้คำตอบชัดเจน |
| C19 | มีผู้ใช้จริง 2–3 คนที่ไม่รู้บริบทและไม่รู้จักกัน ให้ feedback อิสระหลังจบทุกรอบพัฒนา Stage และครั้งแรกที่รับโปรเจ็กต์เดิมมาทำต่อ เพื่อค้นหาปัญหา UX/UI และช่วยสร้าง requirement |
| C20 | ศึกษา Elephant-Goldfish Model เป็นแนวทาง ปรับใช้ได้ ไม่ต้องทำตามทั้งหมด |
| C21 | รับมือข้อจำกัด runtime/dependency versions ของงานเดิมโดยแยก environment ของโปรเจ็กต์ และมีคำแนะนำตั้งค่าแบบทีละขั้นเมื่อจำเป็น |
| C22 | มีคำสั่งที่เข้าใจง่าย เช่น init, start, continue, status ภายใต้ชื่อ project-builder |
| C23 | ไอเดียหรือการเปลี่ยน requirement ที่ไม่เร่งด่วนระหว่างงานให้เก็บ backlog ก่อน ทำ Stage ที่ตกลงไว้ให้จบ แล้วทวนกับผู้ใช้ก่อนเริ่มรอบใหม่ |

รายละเอียดการตั้งชื่อ branch วิธี merge ค่า resource budget และขั้นตอนปิด/แก้ไข feedback ด้านล่างยังเป็นข้อเสนอ เว้นแต่ระบุไว้เป็นอย่างอื่น ความหมายของ DL และจังหวะบังคับเก็บ human feedback ได้รับการยืนยันแล้ว

## 3. ขอบเขตรุ่นแรกและสิ่งที่อยู่นอกขอบเขต

รุ่นแรกมี workflow, role library, shared state, Git/QA/resource policy, local runtime, host adapters, คู่มือ และชุดตรวจความสอดคล้องของแต่ละ adapter เป้าหมายให้ทั้งสาม host ใช้กติกากลางเดียวกัน ไม่จำเป็นต้องมีความสามารถ native เหมือนกันทุกประการ ขอบเขต CLI/Desktop หมายถึงทั้งสอง surfaces ของแต่ละ host บน Windows และ macOS รวม 12 คู่ host/surface/OS ที่ต้องรับรอง แยกผลทดสอบตามเวอร์ชันจริง เป้าหมายรองรับนี้ยังไม่ใช่รายงานว่าทดสอบครบแล้ว

ข้อเสนอการรับรองรุ่นแรก: ทุกคู่ที่ประกาศรองรับต้องทำเส้นทางครบจนถึงเปิด PR เข้า staging ได้เมื่อผ่าน VERIFIED preflight และได้รับอำนาจ LOCAL_ONLY เป็นโหมดสำรองเมื่อเครื่องหรือ repository ยังไม่พร้อม ไม่ถือเป็นหลักฐานว่า adapter นั้นพัฒนาครบหรือผ่าน release acceptance แล้ว การติดตั้งสิทธิ์และ protections ที่จำเป็นเป็น prerequisite ที่ต้องอธิบายและตรวจตั้งแต่ onboarding ไม่ซ่อนภาระนี้ไว้หลังเริ่มงาน

สิ่งที่ไม่อยู่ในรุ่นแรก: Cloud agent sessions, dashboard ที่ต้องมีบริการ cloud ของเรา, ระบบจัดหาผู้ทดลองโดยอัตโนมัติ, การส่งข้อความเชิญบุคคลโดยไม่ได้รับคำสั่ง, การเป็นผู้อนุมัติธุรกิจแทนคนจริง และการทำงานเกินเพดาน PR เข้า staging

Git provider แรกเสนอเป็น GitHub เพราะ repository ปัจจุบันใช้ GitHub; provider อื่นต้องมี adapter และผ่าน policy tests ก่อนประกาศรองรับ Linux ไม่อยู่ใน OS เป้าหมายรุ่นแรก การใช้ container/VM ภายในถ้าจำเป็นต้องรวม overhead ไว้ในงบและแยกจากการประกาศรองรับ host OS

## 4. แนวทางที่พิจารณา

| ทางเลือก | ข้อดี | ข้อแลกเปลี่ยน | ผลการตัดสินใจ |
| --- | --- | --- | --- |
| Native plugins สามชุดเป็นอิสระ | ใช้ความสามารถเฉพาะ host ได้ตรง | กฎและสถานะซ้ำ เสี่ยงเปลี่ยนไม่พร้อมกัน | ไม่เลือก |
| Shared core + host adapters | กฎ สถานะ และผลตรวจใช้สัญญาเดียวกัน | ต้องออกแบบ capability negotiation และทดสอบข้าม host | ผู้ใช้เลือก |

Skills อย่างเดียวใช้สื่อสารวิธีทำงานได้ แต่ไม่เพียงพอสำหรับอ้างว่าบังคับเพดาน Git และควบคุม process ได้จริง จึงเสนอ shared runtime ที่ตรวจการกระทำอย่างเป็นโครงสร้าง พร้อมสิทธิ์ repository ที่จำกัดจากภายนอก runtime ด้วย

## 5. ส่วนประกอบและขอบเขตความรับผิดชอบ

| ส่วนประกอบ | รับผิดชอบ |
| --- | --- |
| Workflow core | Intake, kickoff, stage assessment, work graph, checkpoints, stage completion |
| Team planner | เลือกบทบาท แบ่ง agent กำหนดผู้ทำ/ผู้ตรวจ dependencies และงบการทำงาน |
| Policy core | ตรวจ authority, branch route, evidence, QA gate และเงื่อนไขก่อน mutation |
| State store | บันทึก requirement version, decisions, tasks, ownership, evidence และ receipts |
| Resource supervisor | รับจองงบ เริ่ม/ติดตาม/หยุด process tree และเก็บกวาดทรัพยากรที่เป็นเจ้าของ |
| Environment manager | ตรวจ runtime/version constraints เลือก interpreter/dependencies ที่แยกตามโปรเจ็กต์ และเตรียม setup/rollback guide |
| Command router | รับคำสั่งหรือภาษาธรรมดา แปลงเป็น intent เดียวกัน ตรวจสถานะ/อำนาจ และป้องกันการเริ่ม run ซ้ำ |
| Tool/add-on registry | ตรวจสิ่งที่มี เลือกเครื่องมือที่จำเป็น และผูกผลลัพธ์เข้ากับหลักฐานกลาง |
| Host adapters | แปลง skills, agent delegation, tools, lifecycle และ permissions ของแต่ละ host |
| Git provider adapter | อ่าน refs, สร้าง refs, push, PR และตรวจผลจริง โดยทุก mutation ผ่าน policy |

Host adapter ไม่มีสิทธิ์แก้ hard policy แกนกลาง ชื่อคำสั่งในเอกสารเป็นสัญญาเชิงแนวคิด ยังไม่ใช่คำสั่งที่ติดตั้งได้ ทุก adapter ต้องรายงานสิ่งที่ทำได้จริง เช่น isolated agents, process cancellation, hooks, MCP, resource limits และ remote policy inspection

ถ้า capability ไม่ครบ ให้ลด concurrency หรือเสนอเส้นทางที่ทำได้โดยยังรักษาข้อกำหนด ห้ามจำลองผลตรวจแล้วรายงานว่าทำจริง และห้ามลดเพดานความปลอดภัยเพื่อให้ adapter ดูเหมือนรองรับครบ

## 6. วงจรชีวิตของงาน

ลำดับสถานะที่เสนอ: INTAKE → ASSESSED → KICKOFF_REVIEW → READY → RUNNING → VERIFYING → DEVELOPMENT_COMPLETE → STAGE_FEEDBACK → FEEDBACK_TRIAGE → HANDOFF → COMPLETED

สำหรับงานรับช่วงหรือเวอร์ชันใหม่ของโปรเจ็กต์เดิม ให้มี BASELINE_CAPTURE → BASELINE_FEEDBACK → REQUIREMENT_REFINEMENT ระหว่าง intake ก่อนสรุป requirement และ kickoff โดยเก็บหลักฐานปัญหาปัจจุบันจากผู้ใช้จริงก่อนเลือกเส้นทางพัฒนา

DEVELOPMENT_COMPLETE หมายถึงจบรอบพัฒนาของ Stage และมี build/คู่มือพร้อมส่งให้ผู้ใช้จริงทดลอง ส่วน COMPLETED คือปิด Stage หลังเก็บและจัดการ feedback ตามเงื่อนไข การใช้สองสถานะนี้เป็นข้อเสนอเพื่อรักษาความหมายว่าผู้ใช้ทดลองหลังจบรอบพัฒนา โดยยังไม่อ้างว่ารอบส่งมอบปิดสมบูรณ์ก่อนเห็นผลคนจริง

สถานะประกอบ: NEEDS_INPUT, WAITING_FOR_HUMAN, RESOURCE_WAIT, PAUSED, FAILED, CANCELLED และ CLEANUP_PENDING สถานะรอ/พัก/ยกเลิกไม่เท่ากับงานเสร็จ และห้ามใช้ COMPLETED หากยังมี High ขึ้นไปใน Final หรือยังมีทรัพยากรชั่วคราวที่ควรเก็บกวาดแต่ค้างอยู่

Intake, kickoff และ sprint เป็นขั้นตอนภายในวงจรงาน ไม่เพิ่มเป็น maturity Stage ใหม่ เป้าหมายของ min of max ยังคงเป็นการลด PoC/MVP/Beta/Final ที่ไม่จำเป็น

## 7. การรับงานทั้งสามสถานการณ์

| ประเภทงาน | สิ่งที่ต้องตรวจเพิ่มก่อนวางแผน |
| --- | --- |
| เริ่มจากศูนย์ | ปัญหาธุรกิจ ผู้ใช้ ขอบเขตขั้นต่ำ ความเป็นไปได้ stack และข้อจำกัด local |
| รับงานค้าง | Build/run จริง สิ่งที่ใช้ได้ งานครึ่งเสร็จ หนี้เทคนิค branch/commit ที่เป็นฐาน เหตุผลที่หยุด และ baseline UX/UI feedback จากผู้ใช้จริง 2–3 คน |
| เวอร์ชันใหม่ | ระบบที่ใช้งานอยู่ compatibility, migration, regression baseline ผลกระทบต่อข้อมูล/ผู้ใช้เดิม และ baseline UX/UI feedback จากผู้ใช้จริง 2–3 คน |

การมีไฟล์หรือโค้ดอยู่ไม่ใช่หลักฐานว่าฟีเจอร์ใช้งานได้ ต้องอ่านและตรวจพฤติกรรมที่เกี่ยวข้อง บันทึกผลจริงพร้อม commit/environment ถ้าเข้าถึงระบบบางส่วนไม่ได้ ให้ระบุ unknown แทนการเดาว่าใช้งานได้

Baseline trial ใช้สำเนา local หรือ environment ทดลองที่ได้รับอนุญาตและข้อมูลที่เหมาะสม โดยผ่าน permission/resource preflight ก่อน ถ้าระบบเดิมยังรันไม่ได้ ให้บันทึก onboarding/run failure เป็นหลักฐาน แก้เฉพาะเงื่อนไขตั้งต้นที่ตกลง หรือรอการเข้าถึงก่อนทดลองจริง การดูภาพหรืออ่านเอกสารอย่างเดียวต้องระบุวิธีนั้น ไม่อ้างว่าเป็นการทดลองใช้งานระบบแล้ว

ข้อเสนอเพื่อไม่ให้ intake ติดวงจรรอ kickoff: ตกลง discovery access/setup agreement แบบสั้นก่อน baseline trial ครอบคลุมสิทธิ์อ่าน การรันสำเนา local ข้อมูลทดสอบ งบทรัพยากร และผู้ประสานงานคนจริง อนุญาตเฉพาะการเตรียมสภาพแวดล้อมที่ระบุ ไม่อนุมัติพัฒนาฟีเจอร์หรือแก้ business logic แทน kickoff หากผู้ทดลองลองตามคู่มือแล้วติดตั้ง/เริ่มระบบไม่ได้ ให้เก็บผลความล้มเหลวจากแต่ละคนเป็น baseline evidence ได้ โดยระบุว่ายังไม่มีผล UX ของ flow ที่เข้าไม่ถึง แล้วนำปัญหานั้นไปสร้าง requirement สำหรับการซ่อมอย่างโปร่งใส

## 8. Requirement discovery ที่ต้องได้คำตอบ

BA นำการสัมภาษณ์ โดย PM, UX/UI, SA หรือผู้เชี่ยวชาญร่วมเฉพาะเรื่องที่เกี่ยวข้อง เริ่มจากตัวอย่างงานจริง เป้าหมาย และปัญหา แล้วซักต่อเรื่องเงื่อนไขผิดปกติ ขอบเขต และการตัดสินใจ หลีกเลี่ยงการถามศัพท์เทคนิคที่ลูกค้าไม่จำเป็นต้องรู้

รายการที่ต้องทำให้ชัดตามขนาดงาน:

- Business: ผู้มีส่วนได้ส่วนเสีย ปัญหา/ผลลัพธ์ที่ต้องการ ตัวชี้วัด ผู้ใช้หลัก และเหตุผลที่ทำตอนนี้
- Product: user journeys, feature priority, in/out of scope, business rules, acceptance examples และกรณีใช้งานไม่ได้
- Delivery: เป้าหมาย Stage, เวลา/งบ/ข้อจำกัด, ผู้ตัดสินใจ, สิ่งที่ถือว่าส่งมอบ และผู้ทดลองจริง
- Technical: ระบบเดิม ข้อมูล/สิทธิ์ integrations, local setup, environment, performance/security expectations และเครื่องมือที่มี
- Operations: branch baseline, อำนาจที่ให้, resource budget, การเก็บหลักฐาน และวิธีหยุด/ทำต่อ

คำตอบเช่น “เร็ว”, “ง่าย”, “ปลอดภัย” ต้องซักต่อจนเป็นเงื่อนไขที่ตรวจได้ ถ้าลูกค้ายังไม่รู้ ให้เสนอทางเลือกพร้อมผลกระทบและบันทึกว่าเป็นสมมติฐาน ไม่กดดันให้ยืนยันข้อมูลที่ไม่มี

Requirement ทุกข้อมี ID, เจ้าของ, priority, rationale, acceptance criteria, dependencies และสถานะ confirmed/assumed/open ความไม่ชัดเจนที่เปลี่ยนขอบเขตธุรกิจ อำนาจ หรือเกณฑ์ตรวจรับต้องปิดก่อน READY ส่วนรายละเอียดที่มอบให้ทีมตัดสินใจได้ระบุไว้ในข้อตกลง

สำหรับงานทำต่อ BA และ UX/UI ต้องแปลง baseline feedback เป็นปัญหา/โอกาสที่ตรวจสอบได้ แล้วเชื่อม Observation ID → Requirement ID → Acceptance criteria ให้เจ้าของรีวิว ไม่ถือว่าทุกความเห็นเป็น requirement อัตโนมัติ เก็บทั้งสิ่งที่ผู้ใช้พบจริงและข้อเสนอของทีมแยกกัน

## 9. Kickoff จากธุรกิจถึงเทคนิค

Kickoff package ต้องมีขนาดเหมาะกับงาน แต่ครอบคลุมหัวข้อครบ: business brief, requirement baseline, scope, non-goals, success measures, user journeys/UX, technical design, interfaces/data, NFRs, stage path, backlog, team plan, test matrix, authority, resources, environment/version plan, local guide plan และ human feedback plan

ให้ผู้ใช้รีวิวภาพธุรกิจก่อน แล้วไล่ถึง UX และเทคนิค ตรวจความสัมพันธ์ระหว่าง requirement กับสิ่งที่จะสร้าง ผู้ใช้ไม่จำเป็นต้องอนุมัติศัพท์หรือรายละเอียดภายในทุกบรรทัด แต่ต้องเห็นทางเลือกสำคัญ ข้อแลกเปลี่ยน ค่าใช้จ่าย และประเด็นที่ยังไม่รู้

หลักฐาน kickoff ที่เสนอคือ Stage contract: scope/version, target stage, feature IDs, acceptance/test matrix revision, baseline commit/feedback, team, allowed actions, forbidden actions, resource/tooling budget, decisions delegated, ผู้ประสานงานผู้ทดลอง 2–3 คน, human test window หลังรอบพัฒนา, exit criteria และผู้ยืนยัน ต้องตรวจว่าอำนาจที่ขอเป็น subset ของ hard ceiling เสมอ Kickoff กำหนดวิธีและเวลาได้ แต่ยกเว้นการทดลองคนจริงหลังทุก Stage หรือ baseline trial ของงานทำต่อไม่ได้

## 10. เลือก Stage ตาม min of max

ประเมินก่อนเริ่มโปรเจ็กต์/รอบงาน/ฟีเจอร์และก่อนเปลี่ยน Stage โดยเปรียบเทียบ requirement กับฟีเจอร์ที่พิสูจน์แล้ว เป้าหมายคือลดจำนวน Stage ที่ต้องทำเพื่อถึงเป้าหมายที่ตกลง ไม่ลด requirement หรือสร้าง test matrix ให้ผ่านง่าย

วิธีประเมินที่เสนอ:

1. ทำ requirement-feature-evidence matrix และแยก implemented/verified/partial/missing/unknown
2. ระบุความไม่แน่นอนที่ต้องพิสูจน์ ผลิตภัณฑ์หลักที่ยังขาด และความเสี่ยงการใช้งานจริง
3. เลือกเฉพาะ Stage ที่มีผลลัพธ์จำเป็น พร้อมเหตุผลของ Stage ที่ข้าม
4. รวมกิจกรรมข้ามฟีเจอร์ในรอบงานเดียวเมื่อช่วยลด Stage โดยยังตรวจ integration ครบ
5. ตรวจซ้ำเมื่อ requirement, code, environment หรือความเสี่ยงเปลี่ยนอย่างมีนัยสำคัญ

| Stage | เป้าหมายและหลักฐานที่เสนอ |
| --- | --- |
| PoC | พิสูจน์ข้อสงสัยสำคัญ พร้อมผลทดลองและข้อจำกัด ไม่บังคับทิ้งโค้ดที่เหมาะใช้ต่อ |
| MVP | เส้นทางใช้งานหลักครบตาม scope และมีหลักฐานการทดสอบกับคู่มือ local |
| Beta | ทดลองตามกลุ่มเป้าหมายและสภาพใช้งานที่ตกลง เก็บ/แก้ feedback ตามความรุนแรง |
| Final | ผ่าน matrix >95%, ไม่มี High ขึ้นไป, เอกสาร/คู่มือครบ และเตรียมส่งถึงเพดานที่ได้รับอำนาจ |

เช่น เริ่มที่ MVP เมื่อแนวทางชัด หรือเข้า Final สำหรับงานเดิมที่พร้อมอยู่แล้วได้ ฟีเจอร์ที่พร้อมต่างกันไม่ถูกบังคับเริ่มใหม่ทั้งหมด การข้าม Beta ไม่ยกเว้น baseline feedback ของงานทำต่อหรือ feedback หลัง Stage ที่เลือกทำจริง

## 11. ทีมตามงานและความเสี่ยง

จำนวนบทบาทไม่เท่ากับจำนวน agent ที่ต้องเปิด หัวหน้าประสานงานอาจรับหลายหน้าที่เชิงวางแผน แต่ต้องระบุหน้าที่ให้ครบและแยกผู้ตรวจเมื่อจำเป็น

| บทบาท | ความรับผิดชอบ/ผลงาน |
| --- | --- |
| BA | Business brief, requirement/rules, acceptance examples และ traceability |
| PM | Scope, priority, backlog, iteration plan, dependencies และการตัดสินใจส่งมอบ |
| SA | Architecture, interfaces/data, technical trade-offs และ NFR design |
| DL (Development Lead) | นำงานพัฒนา แบ่งงานเทคนิค กำหนดแนวทางเขียนโค้ด ตรวจ code review/integration ดูแลความเสี่ยงเทคนิค และประสาน SA/นักพัฒนา; PM ดู scope/แผนส่งมอบ ส่วน coordinator ดู workflow/สถานะกลาง |
| UX/UI Designer | Journeys, wireframes/prototypes, design system, interaction/accessibility และ visual acceptance |
| BE developer | Service/API/business logic พร้อม tests และสัญญา integration |
| FE developer | UI/interaction/state พร้อม component/E2E integration ที่เกี่ยวข้อง |
| Data Engineer | Data contracts, pipelines, migration/quality/integrity และการทำซ้ำอย่างปลอดภัย |
| AI Engineer | Model/prompt/retrieval integration, evaluation, failure modes และค่าใช้จ่ายที่เกี่ยวข้อง |
| QA | วาง matrix ก่อนพัฒนา ตรวจ SIT/acceptance/regression/NFRs และบันทึก defect/evidence |
| DevSecOps | Local/CI setup, security checks, secrets, resource controls และ deployment/rollback design ภายในเพดาน |

แยกผู้เชี่ยวชาญเมื่อมีงานชัดที่ต้องใช้ความเชี่ยวชาญ หรือต้องตรวจอิสระ ไม่เปิด agent เพื่อให้ครบรายชื่อ แต่ละงานระบุ inputs, outputs, owner, reviewer, dependencies, allowed files/tools, acceptance และงบ

ข้อเสนอค่าเริ่มต้นคือ coordinator กับ specialist ที่ทำงานครั้งละหนึ่งตัว และงานหนักพร้อมกันหนึ่งงาน ค่อยเพิ่มเมื่อมีงานอิสระและทรัพยากรพอ QA ที่ตรวจ Final ควรเป็น fresh context แยกจากผู้เขียนส่วนที่ตรวจ โดยยังไม่ต้องเปิดทั้งทีมพร้อมกัน

## 12. Agile/Scrum ที่ใช้งานได้จริง

ใช้ product backlog → stage goal → iteration/sprint backlog → work items → review/retrospective ปรับระยะ iteration ตาม scope และความพร้อมของผู้ใช้ ไม่สร้างพิธีประชุมที่ไม่มีผลต่อการตัดสินใจ

Definition of Ready ของ work item: requirement/acceptance ชัด dependencies พร้อม มีผู้รับผิดชอบและขอบเขตไฟล์/branch ส่วน Definition of Done รวมโค้ด ผลทดสอบ review คู่มือที่เกี่ยวข้อง และ resource cleanup

อัปเดตสถานะจากหลักฐานจริง ไม่เปลี่ยน story เป็น Done เพราะ agent รายงานว่าเขียนเสร็จ หาก feedback เป็นงานเพิ่ม ให้แยก defect ภายใน scope ออกจาก requirement ใหม่ และเสนอผลต่อ backlog/Stage โดยไม่เปลี่ยน baseline เงียบ ๆ

## 13. Git bootstrap และเส้นทาง branch

ก่อนพัฒนา ตรวจ local/remote refs, dirty worktree, history, remote identity, existing protections และผลข้างเคียงของ CI ตรวจ remote จริงก่อน mutation ไม่อาศัย remote-tracking refs เก่าอย่างเดียว

ต้องมี main, staging, develop หากมีแล้วไม่ reset/recreate หากขาดให้สร้างเฉพาะที่ขาดจาก baseline ที่ตกลงใน intake สำหรับ repo ว่างใช้ seed commit เฉพาะโครงตั้งต้น แล้วสร้าง branches ก่อนลงมือฟีเจอร์ การสร้างชื่อ branch ไม่ใช่การอนุมัติ release/deploy

กรณีรับงานเดิมที่ไม่มี main/develop ต้องตรวจว่าจุดตั้งต้นที่เลือกเป็นอะไร ห้ามเลือก HEAD ของงานค้างลง main/staging โดยอัตโนมัติ Bootstrap เป็น create-only operation ที่มี receipt และห้ามใช้เป็นทางอัปเดต branch ที่มีอยู่แล้ว ถ้าสิทธิ์ภายนอกไม่แยกการตั้งต้นกับการอัปเดตได้อย่างปลอดภัย ให้ผู้ดูแลเตรียม branch ก่อนเปิด remote automation

รูปแบบชื่อที่เสนอ: Stage เป็น stage/<scope-id>/<stage> เช่น stage/v1/mvp และ feature เป็น feature/<scope-id>/<stage>/<work-item> เช่น feature/v1/mvp/login ชื่อ scope ต้องไม่ซ้ำสำหรับรอบงานใหม่ อาจแทน release หรือฟีเจอร์เดี่ยวตามขอบเขตที่ kickoff ตกลง

| การเปลี่ยนแปลง | แหล่ง → เป้าหมาย | เงื่อนไข |
| --- | --- | --- |
| สร้าง Stage | develop → stage/<scope>/<stage> | บันทึก base commit และ scope |
| สร้างงานพัฒนา | active Stage → feature/... | ทุกงานรวม bugfix/refactor ใช้ active Stage เป็นฐาน |
| รวมฟีเจอร์ | feature → active Stage | ผ่านเกณฑ์ work item; merge/PR ตามอำนาจที่ตกลง |
| รวม Stage | Stage → develop | ผ่านเกณฑ์ Stage, local guide, feedback/triage ของผู้ใช้จริง และ integration ที่จำเป็น; ตามอำนาจที่ตกลง |
| ส่ง Final | develop → PR เข้า staging | Final gate และรอบ feedback ผ่านบนขอบเขต build ที่จะส่งจริง และมีอำนาจเปิด PR |
| หลัง PR staging | ส่งมอบให้ผู้มีอำนาจภายนอก | ไม่มี merge/auto-merge โดยปลั๊กอิน |

ข้อเสนอการรักษาประวัติ: feature → Stage ใช้ squash ได้เมื่อ repo policy อนุญาต; Stage → develop ควรรักษาจุดรวมงานและเชื่อม receipt/PR ให้ติดตามได้ วิธีจริงต้องสอดคล้อง branch protections ห้ามบังคับ merge strategy ที่ repo ปฏิเสธ

ลบ feature เฉพาะ branch ที่งานนี้เป็นเจ้าของ หลังยืนยันผลการรวมงานและตรวจว่าไม่มีการแก้เพิ่มนอก merge อย่าอาศัย ancestry check อย่างเดียวเมื่อใช้ squash เก็บ Stage branch ไว้หลังจบและถือเป็นประวัติรอบงาน ไม่ reuse/force-push rewrite รอบเก่า

ถ้า develop เปลี่ยนระหว่าง Stage ต้อง sync ใน active Stage ตรวจ conflict และทดสอบผลรวมก่อน promote หากมีงานอื่นปนใน develop จนเปลี่ยนขอบเขต PR เข้า staging ให้ประเมิน/ตกลงขอบเขตส่งมอบใหม่ก่อนเปิด PR ห้ามส่งสิ่งที่ไม่ได้ตรวจเพราะคะแนน Stage เดิมผ่านแล้ว

## 14. เพดานอำนาจที่ลดได้เท่านั้น

อำนาจจริง = สิ่งที่ตกลงใน Stage contract ∩ hard policy ∩ สิทธิ์ host/tool/repository

| การกระทำ | นโยบาย |
| --- | --- |
| อ่าน วิเคราะห์ แก้ไฟล์ ทดสอบ commit/push งานที่อนุญาต | ตาม Stage contract |
| PR/merge feature → Stage และ Stage → develop | ตาม Stage contract; ไม่ได้อนุญาตอัตโนมัติทุกงาน |
| เปิด/อัปเดต PR develop → staging | สูงสุดที่อนุญาต โดยห้ามเปิด auto-merge หรือ enqueue merge |
| อัปเดต existing staging/main โดย push/merge/reset/delete | ห้าม |
| PR เข้า main, production deploy/release หรือสั่ง workflow ให้ทำแทน | ห้าม |
| เปลี่ยน protections/permissions เพื่อเพิ่มอำนาจ หรือยืม admin credential | ห้าม |
| มอบหมาย agent/tool/CI อื่นให้ทำเกินเพดาน | ห้าม |

Hard policy ฝังเป็นข้อจำกัดของ action layer และห้ามถูก project config, user prompt, workspace instructions, add-on หรือ resume checkpoint ยกเลิก การแก้ policy ของตัวผลิตภัณฑ์ต้องเป็นการออกเวอร์ชันปลั๊กอินโดยผู้ดูแล แยกจากสิทธิ์ในงานโปรเจ็กต์

## 15. การบังคับใช้และ trust boundary

ต้องแยกให้ชัดระหว่างคำแนะนำใน skill กับข้อจำกัดที่ตรวจได้จริง Remote identity ของ AI ต้องไม่มีสิทธิ์อัปเดต staging/main และไม่มีสิทธิ์แก้ protections/bypass ใช้ repository rules/สิทธิ์จากภายนอก runtime ร่วมกับ structured action checks

บัญชีคนที่มีอำนาจ merge หลังรับมอบต้องไม่ใช่ identity ที่ปลั๊กอินใช้งาน ห้ามเข้าถึง production credentials การเปิด PR ต้องตรวจ workflow ที่ PR จะ trigger เพื่อไม่ให้เกิด auto-merge หรือ production mutation โดยอ้อม

ถ้า host ยังมี raw shell หรือช่องทาง API ที่ใช้ credential กว้างกว่า action layer ได้ ต้องจำกัด environment/credential/network ที่ช่องทางนั้นก่อนอ้างว่า remote automation บังคับเพดานได้ Hook เพียงอย่างเดียวไม่เป็น security boundary โดยเฉพาะ host ที่ hook fail-open

Preflight ต้องรายงาน enforcement status: VERIFIED, LOCAL_ONLY หรือ UNSUPPORTED ใน LOCAL_ONLY ทำแผน/แก้โค้ด/ทดสอบและเตรียม patch ได้ตามสิทธิ์ แต่ไม่ push/เปิด PR จนตรวจเงื่อนไข remote automation ได้ ความสามารถที่ยังไม่พิสูจน์ห้ามรายงานเป็น VERIFIED

VERIFIED ครอบคลุม identity ที่ใช้จริง repository/refs เป้าหมาย protections ที่ตรวจได้ และ configured workflows ที่การกระทำของปลั๊กอินจะ trigger รวมถึง credential/environment isolation ที่จำเป็น ถ้าตรวจเงื่อนไขใดไม่ได้ ห้ามแทนด้วยการเชื่อคำสั่งใน prompt ตรวจซ้ำก่อน remote mutation เมื่อ HEAD/config/permission/workflow เปลี่ยน และยกเลิกการรับรองเดิมเมื่อหลักฐานหมดอายุ การเปลี่ยนระบบภายนอกโดยบุคคลอื่นหลังส่งมอบไม่อยู่ในขอบเขตการควบคุมของ run ที่จบแล้ว

ขอบเขตการรับประกันคือการกระทำของปลั๊กอินที่ติดตั้งและ environment ที่ผ่าน preflight ไม่รับประกันต่อเจ้าของเครื่อง/admin ที่แก้ไบนารี ปิด controls หรือเปลี่ยน credential ภายนอก การสั่งผ่านบทสนทนาปกติต้องไม่สามารถเพิ่มเพดานได้

## 16. QA matrix และเกณฑ์ Final

Matrix เชื่อม Requirement ID → Acceptance criterion → Test case ID → build/environment → result → defect/evidence กำหนดก่อนพัฒนาและ version ทุกการเปลี่ยนแปลง ระบุประเภทที่จำเป็น/ไม่เกี่ยวข้องพร้อมเหตุผลตาม scope/risk ไม่สร้างทุกชนิดเพียงเพื่อให้ครบ checklist

| หมวดที่ต้องประเมิน | ตัวอย่าง |
| --- | --- |
| Functional/logic | Unit, component, API, functional, boundaries/negative paths |
| Integration | SIT, contract, E2E, external dependency/error handling |
| Change assurance | Smoke, regression, confirmation of fixes |
| UX/UI | Interaction, visual, responsive, accessibility, supported browsers/devices |
| Performance | Load/stress/spike/endurance และเกณฑ์เวลาตอบสนอง/ความจุตามงาน |
| Security | Auth/authz, input handling, dependency/secrets, SAST/DAST หรือการตรวจที่เหมาะสม |
| Data/AI | Quality, integrity, migration/idempotency, evaluation, failure/cost bounds เมื่อมี |
| Operations | Start/stop, deploy configuration, recovery/backup/rollback ที่อยู่ใน scope |
| Acceptance | Business scenarios, UAT, baseline feedback ของงานทำต่อ และ feedback ผู้ใช้จริงหลังทุก Stage |

สูตรที่เสนอให้ใช้ตรงกันทุก host: passed_unique_cases / all_applicable_cases_in_final_matrix × 100 > 95 โดยใช้ผลล่าสุดที่เชื่อถือได้ของ build ที่ส่งจริง 95.00% ไม่ผ่าน; 100 เคสต้องผ่านอย่างน้อย 96 เคส; denominator เป็นศูนย์ให้ UNVERIFIED

เคสเดียวมีหลาย tags ได้แต่ไม่นับซ้ำ Skipped/Blocked/Not run/XFail ไม่นับเป็น Passed และยังอยู่ใน denominator หากยังอยู่ใน scope N/A ต้องมีเหตุผลเรื่อง applicability และการเปลี่ยน matrix ที่ตรวจย้อนกลับได้ ห้ามย้ายเคสที่ล้มเหลวเป็น N/A เพิ่มเคส trivial หรือเพิ่มจำนวน retries เพื่อปั่นคะแนน

ผล flaky ต้องรายงาน first failure/retries และไม่รายงานว่าเสถียรเพราะ retry ผ่าน แนวทางการยอมรับ flaky ให้กำหนดใน test strategy และต้องไม่มี High ขึ้นไปค้าง

Final ต้องมี open High/Critical/ระดับสูงกว่า = 0 ครอบคลุม defect และ security findings ในขอบเขตส่งมอบ Severity แยกจาก priority และประเมินจากผลกระทบ ไม่ลดระดับเพราะ deadline/ขนาดทีม/ต้องการผ่าน gate การแก้ false positive หรือ severity ผิดต้องมีหลักฐานและ review

ปัญหาที่เหลือต้องแนบผลกระทบ workaround และผู้รับผิดชอบ เกณฑ์เพิ่มเติมเช่น critical-path 100%, execution completeness หรือผู้มีอำนาจธุรกิจลงนาม UAT ต้องระบุเป็นข้อเสนอและตกลงใน kickoff ไม่อ้างว่าผู้ใช้ยืนยันเกณฑ์เหล่านี้ทุกโปรเจ็กต์แล้ว การลงนาม UAT แยกจากการเก็บ feedback ผู้ใช้จริง 2–3 คนที่บังคับตามจังหวะที่ยืนยันแล้ว

Feedback แต่ละความเห็นไม่นับเป็น test case เพิ่มอัตโนมัติ ถ้าจะวัดเป็นผลทดสอบต้องมี acceptance/test case ที่กำหนดและหลักฐานผลจริง ประเด็น High ขึ้นไปจากคนจริงยังบล็อก Final แม้ automated suite ผ่านเกิน 95% แล้ว

คะแนนรวมเพียงอย่างเดียวไม่แทน requirement coverage หาก requirement สำคัญไม่มีเคสหรือเทสที่จำเป็นยังทำไม่ได้ ให้รายงานช่องว่างและขอปิดเงื่อนไขก่อนรับรองความพร้อม ห้ามสร้างผลทดสอบจากการคาดเดา

## 17. Playwright และระบบ add-on

Playwright เป็นความสามารถหลักที่ปลั๊กอินต้องรู้วิธีเลือกและใช้เมื่อมี browser UI งานไม่เกี่ยวกับ browser ไม่ต้องติดตั้ง browser stack ติดตั้งเฉพาะ runner/browser/dependencies ที่จำเป็นใน tooling plan และตรวจเครื่องมือที่ host/repo มีอยู่ก่อนเพิ่มใหม่

| ผู้ใช้เครื่องมือ | การใช้งานที่เสนอ |
| --- | --- |
| UX/UI Designer | เปิด prototype/หน้าจอจริง ตรวจ flow/interaction/responsive และบันทึกสิ่งที่ต่างจากแบบ |
| FE/QA | Functional browser tests, E2E, visual comparisons, keyboard/accessibility และ console/network failures |
| QA/DevSecOps | เก็บ report/trace ที่จำเป็น ตรวจ runner limits และ teardown |

แยก browser exploration ผ่านเครื่องมือที่ host อนุญาต ออกจาก reproducible test suite ที่อยู่ในโปรเจ็กต์ ผล test ต้องมี assertions และผลรันจริง ไม่ถือว่าสำเร็จเพราะ screenshot ดูถูกต้องอย่างเดียว

Visual baseline ต้องผูกกับแบบที่รีวิวแล้วและ environment/browser/font ที่ระบุ ห้ามอัปเดต snapshots อัตโนมัติเพียงเพื่อให้เคสผ่าน ใช้ visual diff เป็นหลักฐานประกอบการตรวจ ไม่อ้างว่า pixel match พิสูจน์ usability ทั้งหมด

Add-on registry บันทึก capability, version, source, permissions, install footprint, resource estimate, start/stop/cleanup และ evidence schema กลุ่มที่รองรับได้คือ accessibility scanners, design-source connectors, API/contract tools, performance/security/data/AI evaluation tools เลือก implementation ตาม repo และความจำเป็น ไม่ bundle/install ทุกอย่างล่วงหน้า

Playwright เริ่มด้วย worker เดียวในโปรไฟล์ประหยัด ใช้ context/test data ที่แยกกัน ไม่ reuse profile ผู้ใช้โดยปริยาย เก็บ screenshot/trace/video เท่าที่จำเป็นและจัดการ secrets/ข้อมูลส่วนตัวในหลักฐาน ทุก page/context/browser/process ที่สร้างต้อง teardown

## 18. ผู้ใช้จริง 2–3 คนและ feedback อิสระ

ผู้ใช้ยืนยันว่าผู้ทดลองเป็นคนจริง ไม่ใช่ personas หรือ agents ให้เจ้าของโปรเจ็กต์จัดหาผู้เข้าร่วม 2–3 คนที่ไม่มีบริบทภายในและไม่รู้จักกัน ปลั๊กอินเตรียม eligibility questions, task pack, แบบบันทึก และสรุปผล ไม่รับรองความสัมพันธ์จริงของบุคคลจากการเดา

แต่ละคนทดลองแยกกัน ไม่เห็น feedback ของคนอื่นและไม่ถูกชี้นำด้วยคำตอบที่ทีมอยากได้ ใช้ build/guide/task versions เดียวกันและแยก test accounts/data เมื่อจำเป็น เก็บเฉพาะข้อมูลติดต่อ/การบันทึกที่เจ้าของและผู้เข้าร่วมอนุญาต ใช้รหัส P1/P2/P3 ในรายงานที่แชร์ได้

Tasks อธิบายเป้าหมายแบบผู้ใช้ หลีกเลี่ยงสั่งทีละคลิกจนซ่อนปัญหา UX บันทึกการทำสำเร็จ จุดติดขัด ความช่วยเหลือที่ต้องใช้ เวลาโดยประมาณ ความเห็น และหลักฐานที่ผู้เข้าร่วมอนุญาต การต้องช่วยเพิ่มต้องถูกบันทึก ไม่เปลี่ยนเป็น unaided success

สังเคราะห์หลังแต่ละคนส่งผลแล้ว โดยคง raw feedback แยกจากการตีความของทีม แยก usability issue, defect, requirement gap และ suggestion ผูก defect กลับ matrix และ retest ตามผลกระทบ ไม่ใช้คะแนนจาก 2–3 คนอ้างเป็นผลสถิติแทนประชากรทั้งหมด

จังหวะที่บังคับตามคำตอบของผู้ใช้มีสองจุด: (1) ครั้งแรกที่รับโปรเจ็กต์เดิมมาทำต่อ รวมงานค้างและเวอร์ชันใหม่ เพื่อค้นหาปัญหา UX/UI และนำไปสร้าง requirement ก่อน kickoff; (2) หลังจบรอบพัฒนาทุก Stage ที่ทำจริง ทั้งระดับโปรเจ็กต์และฟีเจอร์ตาม scope นั้น รวม PoC ที่ไม่มี GUI ด้วย โดยปรับ tasks ให้เหมาะกับสิ่งที่ Stage ทำได้

หลัง DEVELOPMENT_COMPLETE ให้ส่ง build/guide/task pack ให้ผู้ใช้จริง 2–3 คน ทดลองอย่างอิสระ จากนั้น triage เป็น defect ใน scope, requirement ใหม่ หรือ suggestion แก้ defect ที่ขัด exit criteria บน active Stage ผ่าน feature branch แล้วทดสอบซ้ำตามผลกระทบ งานใหม่เข้าสู่ backlog พร้อมการตัดสินใจของเจ้าของ ไม่ขยาย scope เงียบ ๆ หรือวนทดลองไม่สิ้นสุด

บันทึก build/guide ที่แต่ละคนทดลองและการแก้ภายหลัง ถ้าแก้ flow ที่กระทบผลเดิม ให้ retest งานที่เกี่ยวข้อง ไม่อ้างว่าผลคนจริงของ build เก่าพิสูจน์ build ใหม่โดยอัตโนมัติ จำนวนรอบแก้และวิธี retest ต้องมีขอบเขตใน kickoff แต่ลดข้อกำหนดเก็บ feedback ของรอบ Stage หลักไม่ได้

ห้ามอ้างว่าคนทดลองแล้วหากยังไม่ได้ผลจริง ถ้าผลยังไม่มา ให้ WAITING_FOR_HUMAN และทำงานอื่นที่ไม่พึ่งผลต่อได้ ยังไม่ปิด Stage หรือเริ่ม Stage ถัดไปจากการคาดเดาผล ข้อเสนอเรื่องการใช้คนเดิมซ้ำ: บันทึก fresh/returning และคงความเป็นอิสระของคำตอบ ไม่อ้างว่า returning participant เป็น first-time user; ยังไม่ถือว่าผู้ใช้สั่งให้ต้องหาคนใหม่ทั้งหมดทุกรอบ

ระหว่างรอคนจริง ให้ปิด workload/browser/dev server ที่หมดหน้าที่ เก็บ runnable Stage branch, คู่มือ, test data template และ evidence ที่จำเป็น ผู้ทดลองเปิด/ปิด local ตามคู่มือในเวลาทดลองของตน หากมี preview/test environment ที่จำเป็นต้องเปิดรอ ต้องระบุเจ้าของ งบ และเวลาหมดอายุไว้ล่วงหน้าและอยู่ภายในเพดานอำนาจ ห้ามปล่อย service ชั่วคราวรอ feedback โดยไม่มีขอบเขต

ไม่ส่งคำเชิญ อีเมล หรือข้อความถึงผู้เข้าร่วมโดยไม่มีคำสั่งเฉพาะจากเจ้าของ การออกแบบนี้ไม่รวมการติดต่อบุคคลจริงระหว่างการร่างปลั๊กอิน

## 19. หลักจาก Elephant-Goldfish Model ที่จะปรับใช้

ศึกษา EGM เป็นแนวทางโดยไม่ทำซ้ำทั้งระบบ ข้อเสนอคือให้ coordinator เก็บความรู้และการตัดสินใจในเอกสาร ขณะที่ reviewer ที่จำเป็นเริ่ม fresh context อ่านเฉพาะ artifact และแหล่งที่ระบุ เพื่อหาสิ่งที่ผู้เขียนรู้แต่ลืมอธิบาย

Review สามมุมที่เลือกใช้ตามความเสี่ยง: อธิบายสิ่งที่เข้าใจจากเอกสารได้หรือไม่, มีช่องโหว่/ข้อสมมติซ่อนอยู่หรือไม่, พร้อมวางแผนและสร้างได้หรือยัง งานเล็กใช้ reviewer เดียวแบบมีโจทย์ชัดได้ ไม่สร้าง swarm เต็มชุดทุกงาน

การรีวิวด้วย agent เป็นชั้นตรวจแบบและความครบถ้วน ส่วนการทดลองของผู้ใช้จริงในข้อ 18 เป็นหลักฐานการใช้งานอีกชนิดหนึ่ง ห้ามใช้ผล agent แทนคนจริง และไม่บังคับติดตั้ง EGM เป็น dependency ของ project-builder เพียงเพราะใช้แนวคิดร่วมกัน

## 20. User guide ทุก Stage

ทุก Stage ที่ทำจริงต้องมีคู่มือรัน local ที่ตรงกับ Stage branch และ build/commit นั้น คู่มือเป็น deliverable และ exit criterion ของ Stage รวม PoC ที่มีเพียง CLI หรือ script

เนื้อหาขั้นต่ำ: สิ่งที่ Stage นี้ทำได้/ยังไม่ได้, OS/runtime/prerequisites, checkout ที่ถูกต้อง, dependency/setup commands, environment template ที่ไม่มี secrets, seed/test data, start commands, URL/ports/accounts สำหรับทดลอง, ตัวอย่างใช้งาน, วิธีทดสอบ, stop/cleanup commands และ troubleshooting ต้องแยก Windows/macOS ในขั้นที่ต่างกัน และระบุวิธีตรวจ version/path ของ interpreter ที่ใช้จริง

ใช้เส้นทางตัวอย่าง docs/user-guides/<scope>/<stage>.md และให้ README ใน Stage branch ชี้คู่มือที่ถูกต้อง ไม่เขียนทับคู่มือรอบเก่าด้วยคำสั่งของเวอร์ชันใหม่ คู่มือ final ต้องรวม known issues และการรับช่วงต่อ

ต้องทดลองตามคู่มือใน environment/worktree ที่งานเป็นเจ้าของโดยใช้ข้อมูลทดสอบ บันทึก OS/runtime/tool versions ขั้นตอนที่รันได้จริง และข้อจำกัด ถ้าขั้นสำคัญยังไม่พิสูจน์ ให้ระบุ UNVERIFIED และไม่รับรองว่าผู้ใช้รันได้ คู่มือต้องมีวิธีหยุดและไม่สร้างบริการค้างโดยไม่ตั้งใจ

Prerequisites ที่ยังติดตั้งไม่ได้ต้องปิดตั้งแต่ preflight หรือเป็น blocker ที่แจ้งชัด ห้ามเงียบแล้วอ้างว่าทำ user guide เสร็จครบ

## 21. Resource budgets และ lifecycle

แยกงบ agent/context/token/time ออกจาก CPU/RAM/disk/ports/processes บนเครื่อง ตรวจทั้งความจุและภาระงานปัจจุบันก่อนงานหนัก และนับรวม workers ของ test runner/build/browser/container ไม่ใช่นับเฉพาะ agent

ข้อเสนอค่าเริ่มต้น: งานหนักพร้อมกันหนึ่งงาน เพิ่มได้เมื่อผ่าน resource admission; ใช้ global resource ledger ต่อเครื่องเพื่อให้หลายโปรเจ็กต์/หลาย host ไม่จองทรัพยากรซ้ำ แต่ละโปรเจ็กต์ยังมีงบและ ownership ของตัวเอง

ค่า RAM reserve, CPU ceiling, disk quota, timeouts และ sampling interval ต้องกำหนดจากการวัดบน OS/host ที่รองรับและบันทึกใน kickoff ไม่กำหนดเลขเดียวให้ทุกเครื่อง หากวัดไม่ได้ให้ใช้โหมด conservative และไม่เริ่มงานหนักที่ไม่ทราบขอบเขต

ก่อนเริ่มงานต้องจองงบและลงทะเบียน resource: project/run/task owner, process identity พร้อม start time/command, process-tree/job/container ID, ports, paths, scope, lifetime, stop/cleanup action และสถานะ last verified PID อย่างเดียวไม่พอเพราะอาจถูกนำกลับมาใช้ใหม่

เมื่อเครื่องมีแรงกดดัน ให้หยุดรับงานใหม่ ลด workers หรือพักงานที่ทำ checkpoint ได้ รักษางานของผู้ใช้ก่อนความเร็ว ห้ามเปิด workload เพิ่มเพื่อแก้ timeout ที่เกิดจากแย่งทรัพยากร

## 22. Cleanup เมื่อสำเร็จ ล้มเหลว ยกเลิก หรือหลุด

Resource supervisor เป็นผู้ถือ lifecycle ของงานที่ปลั๊กอินเปิด ไม่ฝากความรับผิดชอบไว้กับคำสั่ง finally ใน agent อย่างเดียว ใช้ process group/job ที่ OS รองรับ พร้อม lease/heartbeat และการตรวจงานตกค้างเมื่อเริ่ม session ถัดไป

ถ้า agent หรือ host ตาย ต้องมีทางหยุด descendants และตรวจ cleanup ที่เหลือ โดยเลือกกลไกที่ทดสอบได้ใน OS นั้น เช่น Windows Job Objects เมื่อรองรับ การมี hook SessionEnd ไม่ถือว่าเพียงพอ และห้ามสัญญาว่าป้องกันเครื่องค้างได้ทุกกรณี

ลำดับ teardown: หยุดรับงาน → cancel อย่างสุภาพ → ให้เวลาปิด/บันทึกงาน → terminate เฉพาะ process tree ที่ยืนยัน ownership → ปิด browser/container/network ของงาน → ลบ disposable files/volumes → ตรวจผลและเขียน receipt

ก่อน recursive delete/move ต้อง resolve absolute path และตรวจให้อยู่ในพื้นที่ที่งานเป็นเจ้าของ ป้องกัน symlink/junction escape ห้าม global prune/kill ตามชื่อ process กว้าง ๆ และห้ามลบ shared cache, browser profile, user database, external volume หรือไฟล์ที่ไม่ทราบเจ้าของ

| ประเภททรัพยากร | หลังเลิกใช้ |
| --- | --- |
| Disposable workloads/scratch | หยุดและลบทันทีเมื่อไม่จำเป็น |
| Deliverable | เก็บโค้ด tests คู่มือ Stage branches และหลักฐานที่จำเป็น |
| User/shared resources | รักษาไว้ ไม่รับ ownership เพียงเพราะนำมาใช้ |
| Logs/traces/screenshots | เก็บเฉพาะตามแผน retention และขนาดที่จำเป็น ลบส่วนชั่วคราว |

ถ้า cleanup ทำไม่สำเร็จ ให้ CLEANUP_PENDING พร้อมรายการที่เหลือและวิธีแก้ ไม่รายงานว่า stage ส่งมอบสะอาดแล้ว MCP/control process ขนาดเล็กอาจอยู่ตามอายุ session ของ host แต่ต้องนับงบและไม่มี workload/browser/server ที่หมดหน้าที่ค้างอยู่ การปิดตัวเองตอน idle ใช้เฉพาะ adapter ที่ reconnect ได้จริง

## 23. State, memory และการเปลี่ยน host

ข้อเสนอให้เก็บข้อมูลที่แชร์ได้ใน repo เช่น brief, requirements, decisions, stage contracts, backlog snapshots, matrix, guides และ handoff ส่วน runtime state/locks/credentials/raw personal feedback อยู่ local หรือพื้นที่ที่ตกลง ไม่ commit secrets และข้อมูลส่วนตัวโดยปริยาย

ข้อมูลกลางต้องมี schema version, project/scope/run IDs, revision, timestamps, policy/core/adapter versions และ commit/environment provenance ใช้ atomic updates กับ mutation lock ห้าม agent หลายตัวเขียนสถานะหรือรวม branch เดียวกันพร้อมกันโดยไม่มีเจ้าของ

เริ่มจากไฟล์ที่ตรวจด้วย schema ได้และ lock ที่ทน crash ตามความจำเป็น ไม่บังคับสร้างฐานข้อมูล/บริการถาวรสำหรับทุกมินิโปรเจ็กต์ การเปลี่ยน host ทำผ่าน handoff checkpoint หลังปล่อย mutation lease และ revalidate refs, running resources, consent และหลักฐานที่ยังใช้ได้

Fresh reviewer ได้เฉพาะ artifact และ references ที่จำเป็น ไม่ inherit บทสนทนาทั้งหมด ห้ามอ้างว่าเป็น blind review หาก adapter สร้าง fresh context ไม่ได้ ให้รายงาน limitation หรือใช้ผู้ตรวจภายนอกแทน

## 24. Autonomy, blockers และการเปลี่ยนขอบเขต

หลัง READY ให้ทีมตัดสินใจรายละเอียดที่ได้รับมอบ แก้ปัญหาภายใน scope และทำจนถึง exit criteria โดยไม่ถามเรื่องที่ตอบจาก repo/ข้อตกลงได้อยู่แล้ว อัปเดตผู้ใช้แบบสรุปผลที่มีสาระ

ไอเดียหรือการเปลี่ยน requirement ที่ไม่เร่งด่วนจากผู้ใช้หลัง READY ตลอด Stage ที่ยังไม่ปิด รวมช่วงพัฒนา ตรวจ และรอ feedback ให้บันทึกเป็น change/backlog item และตอบรับสั้น ๆ โดยไม่เปลี่ยน scope/acceptance ของ Stage ปัจจุบัน ผู้ใช้ยืนยันว่า “รอบปัจจุบัน” หมายถึง Stage ที่ตกลงไว้ จึงทำ Stage นั้นให้เสร็จก่อนทวน backlog เป็นชุด แล้วค่อยตกลง baseline ของรอบใหม่ รายละเอียดอยู่ข้อ 32

หยุดงานที่พึ่งคำตอบเมื่อผู้ใช้สั่งหยุด/ยกเลิก/เปลี่ยนทิศทางให้มีผลทันที พบความเสี่ยงที่ทำให้งานเดิมไม่ควรเดินต่อ ต้องใช้อำนาจใหม่ที่ยังอยู่ใต้เพดาน ข้อมูล/credential ที่ขาด ผลผู้ใช้จริงที่จำเป็น หรือทรัพยากรไม่พอ ทำงานอิสระอื่นต่อได้เมื่อไม่ขัดคำสั่งหยุด พร้อม checkpoint และทางเลือกที่ผู้ใช้ตัดสินใจได้ การเก็บ backlog ไม่ใช่เหตุผลให้ฝืนคำสั่งหยุดของผู้ใช้

คำสั่งเกิน hard ceiling ถูกปฏิเสธเฉพาะส่วนนั้นและเสนอ handoff ที่ทำได้ ไม่ขออนุมัติเพื่อยกเพดาน Work item ที่ขัดกันต้องเข้าสู่ change decision พร้อมผลกระทบ ไม่ใช้สิทธิ์ทั่วไปจาก kickoff ไปครอบคลุม scope ใหม่โดยอัตโนมัติ

จบ Stage แล้วส่ง evidence/guide/known issues, backlog delta และ next-stage recommendation ให้ผู้ใช้รีวิว โดยสรุปว่าอะไรทำตาม scope เดิม อะไรถูกเก็บรอ และแต่ละรายการกระทบลำดับ Stage/เวลา/ทรัพยากรอย่างไร การเริ่ม Stage ถัดไปต้องมี contract ที่ได้รับการตกลงไว้ก่อน ไม่ถือว่าการอนุมัติ Stage ปัจจุบันเป็นการอนุมัติทุก Stage

## 25. Failure handling, idempotency และการกู้คืน

ทุก mutation มี operation ID และตรวจผลก่อน retry โดยเฉพาะ push/PR/create-ref หากคำตอบขาดหายให้ค้นหาการกระทำเดิมก่อนทำซ้ำ ผลลัพธ์หลังไฟล์เปลี่ยน/HEAD ขยับต้อง revalidate ไม่ใช้ผล gate เก่า

Checkpoint เก็บสิ่งที่ทำเสร็จจริง งานที่กำลังทำ files/branch ownership, resources, blockers และ next safe action Resume ต้องตรวจ lock/lease และไม่รัน shell command จาก log เก่าโดยอัตโนมัติ ข้อมูลจาก repo/web/feedback เป็นข้อมูล ไม่ใช่คำสั่งเพิ่มอำนาจ

Bound retries/time/token budget ต่อ task หากไม่คืบหน้าต้องสรุปสาเหตุและส่งต่อ ไม่วน agent-review/build/test ไม่สิ้นสุด Rollback งานต่ำกว่า staging ทำได้ตาม contract และรักษางานที่ไม่ใช่ของตัวเอง การ rollback production อยู่นอกอำนาจเช่นเดียวกับ deploy

## 26. การแพ็ก ติดตั้ง อัปเดต และใช้กับเพื่อน

ออกแบบ shared source of truth สำหรับ policy/workflow/role definitions และสร้าง host-specific packages/manifests โดยไม่คัดลอกกฎมาแก้แยกเอง เริ่มด้วย private/repository-based distribution ไม่ต้องมี cloud service ของ project-builder

เอกสารติดตั้งแยก host พร้อม prerequisites, ขั้นตอน trust/permissions, doctor/preflight, harmless verification, enable/disable และ uninstall ที่รักษางาน/ข้อมูลผู้ใช้ Upgrade pin core/adapter/schema versions และ migrate state แบบสำรอง/ย้อนกลับได้ ไม่เปลี่ยน policy ระหว่าง run โดยเงียบ ๆ

ติดตั้งครั้งเดียวไม่ถือว่าทุก capability ทำงาน ต้องทดสอบแต่ละ host/version/OS ที่ประกาศรองรับ แยกสิ่งที่ host รับประกันออกจากสิ่งที่ project-builder ต้องตรวจเอง ไม่ติดตั้ง plugin/add-on ให้เพื่อนหรือแชร์ credential แทนเพื่อนโดยไม่มีคำสั่ง

การถอดปลั๊กอินต้องหยุดทรัพยากรที่เป็นเจ้าของและแจ้ง state/artifacts ที่เก็บไว้ ไม่ลบ repository หรือ Stage branches ของงาน

## 27. แผนตรวจตัวปลั๊กอินก่อนประกาศใช้งาน

ส่วนนี้เป็นเกณฑ์ออกแบบการตรวจ ไม่ใช่รายงานว่ามี tests หรือผ่านแล้ว ต้องมีทั้ง core tests, adapter conformance และการทดลอง end-to-end ใน host จริง

| กลุ่ม | สิ่งที่ต้องพิสูจน์ |
| --- | --- |
| Stage selection | เริ่มใหม่/รับช่วง/เวอร์ชันใหม่ เลือก Stage น้อยตามหลักฐาน ไม่ข้าม requirement |
| Scope/team | Mini project ใช้ทีม/เอกสาร/tooling พอดี เรียก specialist เมื่อจำเป็น |
| Kickoff | ไล่จาก business ถึง technical และไม่ READY เมื่อมี decision สำคัญที่ยังไม่มีคำตอบ |
| Git | Bootstrap ไม่เขียนทับ, feature จาก Stage, รวมตามเส้นทาง, Stage คงอยู่, feature ลบอย่างมีหลักฐาน |
| Hard ceiling | คำสั่ง user, delegate, raw API/shell, auto-merge, CI workflow และ config changes ไม่ยกอำนาจ |
| Remote controls | AI identity อัปเดต staging/main ไม่ได้จริง; ไม่มี protections ให้ LOCAL_ONLY |
| QA | 95% ไม่ผ่าน, >95% ผ่านเชิงอัตรา, High ทำให้ไม่ผ่าน, denominator/tag/retry ไม่ปั่นคะแนน |
| Playwright/add-ons | Selective setup, reproducible assertions/visual evidence, worker budget และ teardown |
| Human feedback | งานทำต่อมี baseline trial ก่อนสรุป requirement; ทุก Stage มีผลจาก 2–3 คนจริงหลังรอบพัฒนา; ตรวจ WAITING_FOR_HUMAN, triage, retest, High gate และไม่มีผลปลอมหรือการติดต่อที่ไม่ได้รับคำสั่ง |
| Guide | ทุก Stage มีคู่มือ local และทดลองตามคู่มือบน environment ที่ระบุ |
| Resources | Success/failure/cancel/timeout/host crash, child processes, PID reuse, temp cleanup และรักษาของผู้ใช้ |
| Recovery | Unknown mutation outcome, interrupted state write, resume/handoff ข้าม host และ schema migration |
| Installation | โหลดจริงครบ 12 คู่: Codex/Claude Code/Devin × CLI/Desktop × Windows/macOS พร้อมเวอร์ชันและข้อจำกัดที่ตรวจพบ |
| Environment isolation | โปรเจ็กต์ที่ pin Python ต่างกันรันได้ด้วย interpreter/venv ของตนเอง ไม่เปลี่ยน global default/profile; ตรวจ conflicting pins, stale venv, setup guide และ cleanup ownership |
| Commands | init ซ้ำไม่ทำลายข้อมูล, start/continue ซ้ำไม่เพิ่ม run/worker, status เป็น read-only, syntax แสดงตาม host จริง และ pause/cancel เคารพสถานะ/อำนาจ |
| Mid-stage changes | ไอเดียใหม่เข้าคิวโดยไม่ขยาย active baseline, ทวนเมื่อจบ Stage, explicit stop ไม่ถูกเข้าคิวรอ, urgent change ต้อง rebaseline และคำตอบจากคนละ run ไม่ปะปน |

Runbooks ต้องมีตัวอย่าง “สั่งให้ merge staging”, “ขอ deploy ด่วน”, “เปิดหลาย test runners จนเกินงบ”, “browser crash”, “feedback ยังไม่มา” และ “guide รันไม่ได้” เพื่อทดสอบพฤติกรรมจริง ไม่ใช้เพียงการอ่านข้อความ policy

## 28. ข้อเสนอการแบ่งงานสร้างปลั๊กอินภายหลังอนุมัติแบบ

ลำดับเชิง dependency ที่เสนอ: ตกลง open decisions → สัญญาข้อมูล/policy → workflow/state/command intents → Git/resource/environment controls → host adapters → role/tooling/Playwright → guides/human feedback/change backlog → conformance/acceptance

ต้องประเมิน Stage ของการสร้าง project-builder เองตาม min of max แยกจาก Stage ของโปรเจ็กต์ที่มันจะรับผิดชอบ ไม่ถือว่าลำดับข้างต้นเป็นการอนุมัติเริ่ม code หรือเลือก PoC/MVP ให้โปรเจ็กต์นี้แล้ว แผน implementation รายไฟล์จะเขียนหลังเจ้าของรีวิวแบบ

อัปเดตหลังยืนยันแบบวันที่ 7 พฤศจิกายน 2026: [แผน implementation แบบรายงานและรายไฟล์](../plans/2026-11-07-project-builder-implementation.md) เสนอ PoC → MVP → Final และ Beta เฉพาะเมื่อหลักฐานชี้ว่าจำเป็น รวม 19 งาน ยังไม่ได้เริ่มสร้างหรือติดตั้ง dependencies

## 29. ผลรีวิว การตัดสินใจล่าสุด และสิ่งที่มอบให้ผู้สร้าง

Builder check แบบ fresh context รอบแรกพบ 3 ประเด็นระดับแผนสร้าง: ความหมายของ release-complete เทียบกับ LOCAL_ONLY, host/surface/OS matrix และความบังคับของการทดลองคนจริง ข้อแรกถูกทำให้ชัดในข้อ 3/15 เป็นข้อเสนอของผู้ออกแบบ ส่วนคำตอบจากเจ้าของวันที่ 6 พฤศจิกายน 2026 ปิดประเด็น OS, human feedback และบทบาท DL ดังนี้

1. รุ่นแรกต้องรองรับ Windows และ macOS สำหรับ CLI/Desktop ของทั้งสาม host
2. DL คือ Development Lead นำทีมและงานพัฒนา
3. เก็บ feedback ผู้ใช้จริง 2–3 คนหลังจบรอบพัฒนาทุก Stage และครั้งแรกที่รับโปรเจ็กต์เดิมมาทำต่อ เพื่อช่วยค้นหาปัญหา UX/UI และสร้าง requirement

ข้อเสนอการแยก DEVELOPMENT_COMPLETE ออกจาก COMPLETED, discovery access/setup agreement ก่อน baseline trial, การคัดแยกและ retest feedback และการบันทึก fresh/returning participants เป็นรายละเอียดที่เพิ่มเพื่อทำให้ข้อกำหนดทำงานได้ เจ้าของยังต้องรีวิวในเอกสาร ไม่ใช่การยกเว้นจังหวะทดลองที่ยืนยันแล้ว

ผลทบทวนฉบับ v0.3 โดย reviewer อิสระ: ประเด็นที่ขวางการวางแผนสร้างก่อนหน้าถูกปิดแล้ว และไม่พบข้อขัดแย้งสำคัญใหม่ ข้อสรุปนี้รับรองเฉพาะความพร้อมของแบบสำหรับทำ implementation plan ไม่ใช่ผลทดสอบ host/runtime สิทธิ์ Git การติดตั้ง หรือ cleanup จริง ทั้ง 12 คู่แพลตฟอร์มและเส้นทาง VERIFIED จนเปิด PR ยังเป็น acceptance targets ที่ต้องพิสูจน์ระหว่างสร้าง

ข้อกำหนดเพิ่มวันที่ 7 พฤศจิกายน 2026: แยก runtime/dependencies จากเครื่องหลักพร้อมคู่มือทีละขั้น, ใช้ command vocabulary ที่เข้าใจง่าย และเก็บ change request ที่ไม่เร่งด่วนเป็น backlog จนจบ Stage ที่ตกลงไว้ ผู้ใช้ยืนยันระดับรอบเป็น Stage แล้ว ส่วนชื่อคำสั่งรอง รายละเอียดการควบคุม environment และ event handling เป็นข้อเสนอในข้อ 30–32 ที่ต้องรีวิวต่อ ข้อสรุป reviewer ของ v0.3 ไม่ครอบคลุมส่วนเพิ่มโดยอัตโนมัติ

ผลทบทวนส่วนเพิ่ม v0.4 โดย reviewer อิสระ: ไม่พบคำถามหรือข้อขัดแย้งสำคัญที่ขวางการวางแผนด้าน environment isolation/ownership, command routing, Stage-level backlog, ข้อยกเว้น stop/rebaseline และ human feedback เป็นการตรวจแบบเท่านั้น ยังไม่ได้ติดตั้งหรือพิสูจน์ runtime behavior

ข้อเสนอที่ต้องเห็นชอบพร้อมเอกสาร: GitHub เป็น provider แรก, branch naming แบบ scope/stage, Stage branch ที่จบแล้วไม่ reuse, ค่าเริ่มต้นหนึ่ง specialist/หนึ่งงานหนัก, LOCAL_ONLY เมื่อ remote enforcement ไม่พร้อม, วิธีเก็บ state แบบ local-first และการแยกข้อมูลส่วนตัวของผู้ทดลอง

เจ้าของยืนยันเอกสาร v0.4 ด้วยคำตอบ “โอเค” วันที่ 7 พฤศจิกายน 2026 รวมข้อเสนอข้างต้นและรายละเอียดส่วนเพิ่ม 30–32; ข้อความที่บอกว่าต้องรีวิวก่อนหน้านี้เป็นบันทึกลำดับการออกแบบ ไม่ใช่รายการอนุมัติที่ยังค้าง การยืนยันแบบนี้ยังไม่ใช่หลักฐานว่าพฤติกรรมจริงผ่านการทดสอบ

มอบให้ผู้สร้างเลือกและอธิบายใน implementation plan: ภาษา/runtime ที่เหมาะกับ OS เป้าหมาย, modules/interfaces ภายใน, validation library, storage/locking implementation, test runner ของ core, per-OS supervision และค่า resource thresholds ที่ผ่านการวัด โดยต้องรักษาสัญญาและ hard constraints ของเอกสารนี้

## 30. Runtime versions และ environment ที่แยกตามโปรเจ็กต์

ต้องตรวจข้อจำกัดก่อนพยายามรันงานเดิม โดยอ่าน manifest/lockfile, version files เช่น .python-version, CI/container configuration และคู่มือเดิม รวมทั้งตรวจ interpreter/manager ที่มีอยู่จริง ความขัดแย้งระหว่างแหล่งเหล่านี้เป็นข้อมูลที่ต้องคลี่คลาย ไม่เลือก Python ล่าสุดหรือเปลี่ยน pin เงียบ ๆ เพื่อให้ติดตั้งผ่าน

แยกสองหน้าที่: version manager จัดหา/เลือก Python เวอร์ชันที่ต้องใช้ ส่วน virtual environment แยก packages ของโปรเจ็กต์ venv สร้างจาก interpreter ที่เลือกแล้ว ไม่ดาวน์โหลด interpreter คนละเวอร์ชันมาแทนให้โดยตัวมันเอง ตัวอย่างทางเลือกคือ pyenv บน macOS และ pyenv-win บน Windows หรือใช้ manager เดิมของโปรเจ็กต์ถ้าผ่านการตรวจ ไม่บังคับย้ายเครื่องมือทุกงานให้เป็นแบบเดียว

ลำดับที่เสนอ:

1. ตรวจ runtime constraint ที่แน่นอน รวม OS/architecture และ lockfile พร้อมบันทึกสิ่งที่มี/ขาด/ขัดกัน
2. ใช้ interpreter เวอร์ชันที่ถูกต้องซึ่งมีอยู่แล้วก่อน ถ้าขาด ให้เสนอการติดตั้งแบบแยกที่เหมาะกับเครื่องและงบ โดยต้องอยู่ใน tooling/setup authority
3. สร้าง environment ของโปรเจ็กต์ด้วย interpreter นั้น ใช้ executable path แบบระบุชัดในการติดตั้ง packages/build/test ไม่พึ่งว่าผู้ใช้เคย activate อะไรใน terminal อื่น
4. ติดตั้งตาม lockfile/constraints ของงาน ตรวจ version, executable path, dependency resolution และ smoke run แล้วบันทึก environment fingerprint
5. ใช้ fingerprint ของ runtime/lockfile/OS/architecture ตรวจ reuse และความล้าสมัยของ environment ก่อน continue หรือสลับ Stage ไม่รันงานกับ venv ที่สร้างด้วย interpreter ผิดแล้วอ้างว่าพร้อม

กฎเครื่องผู้ใช้: ไม่เปลี่ยน system Python, global default, persistent PATH, shell profile, execution policy หรือ global packages อัตโนมัติ ใช้ project-local selection หรือ child-process environment ที่จำกัดขอบเขต ถ้าการติดตั้ง manager/build prerequisites ต้องแก้ระดับบัญชีผู้ใช้หรือเครื่อง ให้ระบุผลกระทบและให้ผู้ใช้เลือก/ตกลงขั้นตอนก่อน โดยเตรียมคู่มือพร้อมวิธีย้อนกลับ ห้ามคัดลอกคำแนะนำ pyenv global หรือคำสั่งยกระดับสิทธิ์จากเว็บมารันตามโดยไม่ประเมิน

คู่มือ setup แบบทีละขั้นต้องระบุ: ตรวจสิ่งที่มี → ตัวเลือกและผลกระทบ → ติดตั้งเฉพาะที่ขาด → เลือกเวอร์ชันเฉพาะโปรเจ็กต์ → สร้าง venv → ติดตั้ง dependencies → ตรวจ executable/version → รันตัวอย่าง → หยุด/เก็บกวาด → ย้อนกลับ/แก้ปัญหา แสดงคำสั่งที่เหมาะกับ OS/shell ที่ตรวจพบ และผลที่ผู้ใช้ควรเห็นในแต่ละขั้น ไม่อ้างว่ารันได้บนเครื่องอื่นจากการทดสอบเพียงเครื่องเดียว

Environment ของ core/plugin ต้องแยกจาก runtime ของโปรเจ็กต์ที่รับมา ไม่เอา dependencies ของตัวปลั๊กอินไปติดตั้งทับใน venv ของลูกค้า และไม่ใช้การแก้ global runtime เป็นทางซ่อม compatibility ของ core

จำแนก environment เป็น user-owned/shared, project toolchain ที่ตกลงให้เก็บเพื่อรันซ้ำ และ scratch/test environment ที่ลบทิ้งเมื่อจบงาน ไม่ commit venv หรือคัดลอกข้ามเครื่องแทน lock/setup recipe ไม่ลบ pyenv-installed runtimes หรือ cache ของผู้ใช้เพียงเพราะงานหนึ่งเลิกใช้ environment ที่เป็นของปลั๊กอินต้องมี ownership, disk budget และ retention เพื่อไม่ทิ้ง env ซ้ำสะสมทุกรอบ

ถ้าเวอร์ชันที่ pin ไว้ไม่มีสำหรับ OS/architecture นั้น หรือขัดกับ dependencies ให้รายงาน constraint และเสนอวิธีที่พิสูจน์ได้ เช่น runtime ที่รองรับจริง การแก้ pin แบบได้รับการตกลง หรือ environment ทางเลือกที่มีงบและการปิดชัดเจน ไม่แก้ business requirements/lockfile หรือเปลี่ยนเป็น latest เอง เพดาน PR เข้า staging ยังคงเดิม

หลักเดียวกันใช้กับ runtime อื่นเมื่อ repo ต้องการ เช่น Node/JDK โดยใช้ adapter ตาม stack ที่ตรวจพบ ไม่ติดตั้งทุก language manager ล่วงหน้า

## 31. คำสั่งที่ผู้ใช้เข้าใจและเรียกซ้ำได้ปลอดภัย

ชุดชื่อมาตรฐานกลางที่ผู้ใช้เสนอคือ /project-builder:init, /project-builder:start, /project-builder:continue และ /project-builder:status ชื่อเหล่านี้เป็น UX/intent contract ของผลิตภัณฑ์ ไม่ใช่การอ้างว่าติดตั้งแล้วในแชตนี้

| คำสั่งหลัก | ความหมาย/พฤติกรรมที่เสนอ |
| --- | --- |
| /project-builder:init | ตรวจและลงทะเบียนโปรเจ็กต์ ตรวจ repo/branches/runtime/resources เตรียม setup plan และ bootstrap ตามสิทธิ์; เรียกซ้ำแล้วตรวจ/เติมเฉพาะที่ขาด ไม่ reset งานเดิมหรือเปลี่ยน global environment |
| /project-builder:start | รับโจทย์ใหม่หรือรอบใหม่ ทำ intake/assessment/kickoff และเริ่มเมื่อ READY; หากมี active run อยู่ให้แสดงสถานะและทางเลือก ไม่เปิด run ซ้ำ |
| /project-builder:continue | อ่าน checkpoint ตรวจ refs/environment/resources/authority แล้วทำงานเดิมต่อ; ถ้ายังรอคนจริงหรือข้อมูลให้บอกสิ่งที่รอ ไม่ข้าม gate หรือเริ่ม Stage ใหม่เอง |
| /project-builder:status | อ่านภาพรวม Stage/งานที่เสร็จ/กำลังทำ/ติดขัด, QA, ทรัพยากรของงาน, backlog ที่รอ และ next action โดยไม่เริ่ม service/แก้ไฟล์/ซ่อมระบบเอง |

คำสั่งรองที่เสนอให้แสดงเมื่อเกี่ยวข้อง: help อธิบายวิธีใช้, doctor ตรวจความพร้อม, guide เปิดคู่มือ local, change รับไอเดีย/คำขอเปลี่ยน, backlog ดูและจัดลำดับคิว, feedback รับผลคนจริงพร้อมแหล่งที่มา, pause พักพร้อม checkpoint/cleanup, cancel ยกเลิก run โดยรักษางานที่ส่งแล้ว และ cleanup เก็บกวาดเฉพาะทรัพยากรที่ยืนยัน ownership ได้ ใช้ prefix project-builder เดียวกัน; stop อาจเป็น alias ของ pause เพื่อไม่ต้องจำศัพท์หลายชุด

ผู้ใช้เล่าไอเดีย ขอ status หรือสั่งหยุดเป็นภาษาธรรมดาได้ Command router ต้องรับเจตนาเดียวกันและบันทึกผลเหมือนเรียกคำสั่ง ไม่บังคับจำ argument IDs เมื่ออนุมานโปรเจ็กต์/run เดียวได้แน่นอน หากกำกวมหลายโปรเจ็กต์ให้ถามเลือกก่อน mutation

ชื่อที่พิมพ์ได้จริงอาจต่างตาม host/surface/version เช่น เอกสาร Codex อธิบายการเลือก skill ผ่าน /skills หรือการ mention ด้วย $ ขณะที่ Claude Code/Devin มี namespaced plugin skills Adapter ต้องเลือกวิธีเรียกที่ host รองรับ ทดสอบจริง และให้ help/guide แสดงรูปแบบที่ใช้ได้ ไม่อ้างว่า slash syntax เดียวกันใช้งานได้ครบทั้ง 12 คู่ก่อนพิสูจน์ หาก host ไม่มี alias แบบที่ต้องการ ให้มี entry skill/router ที่ใช้ intent สั้น ๆ เดิมแทน

ทุก intent ต้องตรวจ current state, authority, project/run identity และ idempotency key; start/continue ซ้ำหรือคำตอบล่าช้าต้องไม่เพิ่ม agent/process/PR ซ้ำ status/help เป็น read-only; doctor ไม่ซ่อมหรือ install จนกว่าจะมี setup authority; pause/cancel/cleanup ใช้ supervisor และ receipt การไม่มีคำสั่งใดใน host ต้องไม่เปลี่ยน hard policy

ข้อความตอบเริ่มด้วยผลที่ผู้ใช้ต้องรู้ เช่น “กำลังทำ MVP”, “บันทึกไอเดียไว้ทวนหลังจบ MVP”, “รอผลจากผู้ทดลองอีก 1 คน” หรือ “ขาด Python ตามเวอร์ชันที่โปรเจ็กต์กำหนด” แล้วให้ next action ที่ชัด รายละเอียดเทคนิคเปิดดูเพิ่มได้ progressive disclosure ใช้กับทั้งคำสั่งและ role/tool metadata เพื่อลด context/เครื่องมือที่โหลดโดยไม่จำเป็น

## 32. การเปลี่ยน requirement และเหตุการณ์ระหว่าง Stage

ก่อน READY ระหว่าง discovery/co-design ปรับร่าง requirement ได้ตามบทสนทนาโดยมี decision history หลัง READY ให้ active Stage contract และ acceptance baseline มี revision คงที่ ไอเดียใหม่ที่ไม่เร่งด่วนเป็น proposed change ใน backlog ไม่เปลี่ยนงานของ agent ที่กำลังทำอยู่

ผู้ใช้ยืนยันแล้วว่าทำ Stage ปัจจุบันให้เสร็จก่อนทวน backlog ไม่ใช่แทรกไอเดียทุกครั้งที่จบ task หรือ sprint บันทึกทันทีและตอบรับสั้น ๆ ได้ แต่ไม่เปิดทีมวิเคราะห์/พัฒนาฟีเจอร์ใหม่ขนานโดยไม่จำเป็น หลังปิด Stage รวมผลส่งมอบ, human feedback และ change queue ให้ผู้ใช้เลือกสิ่งที่จะทำต่อ แล้วประเมิน Stage ตาม min of max ใหม่สำหรับ scope ที่ตกลง

Change item ที่เสนอมี ID, ผู้เสนอ/แหล่งคำสั่ง, เวลาที่รับ, project/Stage/run IDs, requirement ที่เกี่ยวข้อง, ปัญหา/ผลที่ต้องการ, ประเภท add/change/remove, urgency, dependencies, ผลกระทบที่ยังไม่ประเมิน/ประเมินแล้ว, priority และสถานะ proposed/queued/reviewed/accepted/deferred/rejected/withdrawn พร้อม decision log การ accepted ยังไม่เปลี่ยน active contract จนมีข้อตกลงรอบใหม่หรือ explicit urgent rebaseline

| เหตุการณ์ | การตอบสนองที่เสนอ |
| --- | --- |
| เพิ่มไอเดีย/เปลี่ยน requirement ทั่วไป | บันทึกคิว แจ้งว่าจะทวนหลังจบ Stage และเดิน scope เดิมต่อ |
| ถอนหรือเปลี่ยนลำดับไอเดียที่รอ | อัปเดต backlog พร้อมประวัติ ไม่ลบหลักฐานหรือกระทบ active work |
| ถามความคืบหน้า/เหตุผล | ตอบจากสถานะจริง แล้วเดินงานเดิมต่อ |
| สั่งหยุด/พักอย่างชัดเจน | หยุดรับ mutation ใหม่ cancel งานที่หยุดได้ บันทึก checkpoint และ cleanup ตาม safe shutdown ไม่รอให้จบ Stage |
| สั่งยกเลิก run | ปิด run/ทรัพยากร รักษางานและ branch ที่มีคุณค่า ไม่ rollback/delete งานเดิมโดยปริยาย |
| เปลี่ยนใจแต่ไม่ชัดว่าต้องหยุดงานเดิมทันทีหรือรอรอบหน้า | ขอคำตอบเฉพาะผลที่ต้องการก่อน mutation ที่อาจขัดคำสั่ง ไม่ตีความคำสั่งยกเลิกเป็นเพียงไอเดียเข้าคิว |
| ต้องเปลี่ยนทิศทางทันที | พักงานที่ได้รับผลกระทบ ประเมิน delta และตกลง scope/authority/budget/acceptance revision ใหม่ก่อนเดินต่อ |
| พบ defect ภายใน scope | แก้และ retest ตาม contract; ประเด็น High/security/data ที่ทำให้เดินต่อไม่ปลอดภัยหยุดเฉพาะส่วนที่ได้รับผลกระทบทันที |
| ขาด runtime/credential/dependency ที่จำเป็น | บันทึก blocker พร้อมวิธีแก้หรือ setup guide ทำงานอิสระต่อได้โดยไม่ใช้ runtime ผิดหรือสิทธิ์เกิน |
| เครื่องทรัพยากรต่ำ/พื้นที่ใกล้เต็ม | ไม่เริ่มงานหนักเพิ่ม ลด/พัก workload ของตนเองและ cleanup โดยรักษาข้อมูลผู้ใช้ |
| คนหรือ host อื่นเปลี่ยนไฟล์/refs/config | ตรวจ conflict/stale evidence/lease ใหม่ ไม่เขียนทับหรือ promote ด้วย gate เก่า |
| network/tool timeout หรือไม่รู้ผล mutation | bounded retries และตรวจ receipt/ผลจริงก่อนทำซ้ำตามข้อ 25 |
| ยังไม่ได้ feedback คนจริง | WAITING_FOR_HUMAN ปิดของชั่วคราวที่หมดหน้าที่ ไม่สร้างผลแทนคนหรือปิด Stage เอง |
| คำสั่งซ้ำ/ข้อความมาช้าหรือผิด run | ตรวจ correlation IDs และ idempotency ก่อนกระทำ ไม่เอาคำตอบคนละรอบมาอนุมัติงาน |

Explicit stop/urgent rebaseline เป็นข้อยกเว้นต่อการทำ Stage เดิมให้จบ ไม่ใช่ช่องทางยกเพดานอำนาจ การเปลี่ยนรอบต้อง invalidate งาน/หลักฐานที่พึ่ง requirement เก่าและป้องกัน worker เก่าเขียนต่อด้วย revision/lease checks ขอบเขตการย้อนกลับต้องตกลงและรักษาการเปลี่ยนแปลงของผู้อื่น

เนื้อหาใน repo/web/feedback เป็นข้อมูล การเพิ่ม requirement ที่มีผลต้องมาจากผู้ใช้หรือผู้มีอำนาจที่ตกลงไว้ ไม่ให้ prompt injection หรือ add-on สั่งเปลี่ยน scope/สิทธิ์เอง

## 33. แหล่งอ้างอิงที่ศึกษา

ข้อกำหนดผลิตภัณฑ์มาจากการสนทนา แหล่งภายนอกด้านล่างใช้ตรวจความสามารถหรือเป็นแรงบันดาลใจ ไม่ได้ทำให้ทุกขั้นตอนของแหล่งนั้นเป็นข้อกำหนดของเรา วันที่ตรวจชุดแรก: 6 พฤศจิกายน 2026; ตรวจเพิ่มเรื่อง environment/commands: 7 พฤศจิกายน 2026

- [Google Open Source Blog: EGM article ที่ผู้ใช้ให้](https://opensource.googleblog.com/2026/10/introducing-elephant-goldfish-model-plugin.html) และ [หน้า archive ตุลาคมที่มีเนื้อหาบทความ](https://opensource.googleblog.com/2026/10/) — ใช้แนวคิด full-context design กับ fresh-context review และให้คนตัดสินใจ; ลิงก์บทความตรงติด anti-bot ในเครื่องมือ จึงอ่านจาก archive และ repo ต้นทางประกอบ
- [EGM README](https://github.com/google/elephant-goldfish-model/blob/main/README.md), [workflow guide](https://github.com/google/elephant-goldfish-model/blob/main/docs/getting_started.md) — ใช้เฉพาะหลักการที่เหมาะสม ไม่กำหนด swarm/review loops ตายตัว
- [OpenAI: package plugins](https://developers.openai.com/plugins/build/plugins) และ [skills](https://developers.openai.com/plugins/concepts/skills) — plugin/skills/MCP และข้อจำกัดการติดตั้ง hooks ต้องตรวจตาม surface/version
- [Claude Code plugins](https://code.claude.com/docs/en/plugins) — plugins รวม skills/agents/hooks/MCP; process และสิทธิ์ยังเกี่ยวข้องกับ host session
- [Devin CLI plugins](https://docs.devin.ai/cli/extensibility/plugins/overview) — local custom subagents และข้อจำกัด hooks ที่ยัง fail-open ทำให้ต้องมี enforcement ชั้นอื่น
- [Git branch](https://git-scm.com/docs/git-branch), [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) — start-point, branch updates และสิทธิ์ bypass
- [ISTQB CTFL](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf), [OWASP ASVS](https://asvs.owasp.org/) — traceability/risk-based testing และรายการตรวจด้าน security ตาม applicability; >95% เป็นเกณฑ์ของผู้ใช้ ไม่ใช่ตัวเลขที่อ้างจากมาตรฐาน
- [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots), [traces](https://playwright.dev/docs/trace-viewer), [accessibility](https://playwright.dev/docs/accessibility-testing), [parallelism](https://playwright.dev/docs/test-parallel) — visual evidence, environment consistency, diagnostic artifacts และ worker processes
- [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects), [Docker limits](https://docs.docker.com/engine/containers/resource_constraints/), [Compose teardown](https://docs.docker.com/reference/cli/docker/compose/down/) — process-tree/resource lifecycle และความแตกต่างระหว่างหยุด workload กับลบข้อมูล
- [Python venv](https://docs.python.org/3/library/venv.html), [pyenv commands](https://github.com/pyenv/pyenv/blob/master/COMMANDS.md), [pyenv README](https://github.com/pyenv/pyenv/blob/master/README.md), [pyenv-win](https://github.com/pyenv-win/pyenv-win) — แยก interpreter selection ออกจาก package environment; local selection ไม่ใช่ global selection และเครื่องมือ/ขั้นติดตั้งต่างตาม OS
- [OpenAI: build skills](https://learn.chatgpt.com/docs/build-skills), [Claude plugin skills](https://code.claude.com/docs/en/plugins), [Devin plugin commands](https://docs.devin.ai/cli/extensibility/plugins/overview) — ตรวจวิธีเรียกตาม host ไม่ถือว่าชื่อ logical command ทำให้เกิด native slash command โดยอัตโนมัติ
