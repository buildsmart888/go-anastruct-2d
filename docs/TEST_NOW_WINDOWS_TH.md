# ทดลอง GO anaStruct 2D v0.5.5 บน Windows ได้เลย

**รุ่นสำหรับทดสอบเท่านั้น (ยังไม่ใช่ Release ที่ผ่านการรับรอง)**

รองรับเป้าหมาย IngeTrazo 0.5.9 / Windows 10 หรือ Windows 11 รุ่น 64-bit

## ดาวน์โหลดครั้งเดียว

ดาวน์โหลด ZIP ของสาขาแก้ไขนี้จาก:
https://github.com/buildsmart888/go-anastruct-2d/archive/refs/heads/fix/v055-offline-portable-runtime-installer.zip

แตกไฟล์ ZIP ลงในโฟลเดอร์ปกติ แล้วปิด IngeTrazo ให้สนิทก่อนเริ่ม

## วิธี A — อยากลองปลั๊กอิน v0.5.5 เลย

1. ดับเบิลคลิก `setup_windows.cmd` ในโฟลเดอร์ที่แตก ZIP
2. ตัวติดตั้งตรวจสอบ checksum ของ ZIP ปลั๊กอินและสำรองปลั๊กอินเดิม
3. ถ้ายังไม่มี portable runtime จะลองใช้ Python แบบแยก environment ตามระบบเดิม (อาจต้องติดตั้ง Python และต่ออินเทอร์เน็ต)
4. เปิด IngeTrazo 0.5.9 > GO 2D anaStruct > Check Solver > Run Analysis
5. ทดลอง Simply Supported Beam และ Portal 3 Storey 3 Bay จากตัวอย่าง

> วิธี A **ยังไม่ใช่** การทดสอบแบบไม่มี Python; หากต้องการ EXE แบบพกพาให้ใช้วิธี B

## วิธี B — สร้างและทดสอบ Portable EXE บนคอมของคุณ (ไม่ต้องพึ่ง GitHub Actions)

**ต้องมี Python 3.11 รุ่น 64-bit บนเครื่องที่ใช้ Build เพียงครั้งเดียว** (ต่างจากเครื่องผู้ใช้โปรแกรมสำเร็จรูปซึ่งไม่ต้องมี Python เมื่อ EXE ผ่านการทดสอบแล้ว) และต่ออินเทอร์เน็ตตอน Build

1. หากยังไม่มี Python 3.11 x64 ให้ติดตั้งจาก https://www.python.org/downloads/ หรือผ่าน Windows Package Manager โดยเลือก Python 3.11 รุ่น 64-bit
2. ดับเบิลคลิก `BUILD_PORTABLE_AND_TEST_WINDOWS.cmd`
3. สคริปต์สร้าง Virtual Environment แยกใน `.local-build/` และติดตั้ง dependencies ที่ล็อกเวอร์ชัน
4. สร้าง `go_anastruct_worker.exe` ด้วย PyInstaller จากนั้นทดสอบ:
   - EXE `--check` และ JSON worker protocol
   - วิเคราะห์คานและ Portal เทียบ v0.5.4 กับ v0.5.5
   - ติดตั้งใน APPDATA/LOCALAPPDATA โปรไฟล์จำลองที่แยกออกมา
   - ตรวจสอบว่าหาก ZIP ถูกแก้ไขแล้ว checksum ผิด จะติดตั้งไม่ได้
5. หากผลขึ้น `PASS` จะได้ไฟล์:
   - `dist/go_anastruct_2d-runtime-windows-x64-v0.5.5.zip`
   - `dist/go_anastruct_2d-runtime-windows-x64-v0.5.5.zip.sha256`
   - `dist/numerical-regression-v055.json`
   - `.local-build/build-and-test-v055.log`
6. จากนั้นปิด IngeTrazo และดับเบิลคลิก `setup_windows.cmd` เพื่อให้โปรแกรมติดตั้ง Portable Runtime ที่สร้างได้ แล้วเปิดโปรแกรมเพื่อตรวจใน GUI จริง

ถ้า Build ขึ้น `BUILD OR TEST FAILED` ให้ดูไฟล์ `.local-build/build-and-test-v055.log` และแจ้งข้อผิดพลาด ไม่ควรนำ EXE/ZIP ที่ยังไม่ผ่านไปแจกจ่าย

## GitHub Actions ยังขึ้นแดง

ตอนนี้ Workflow บน GitHub ล้มเหลวตั้งแต่ก่อนเริ่ม Runner ขั้นตอนหลัก จึงยังไม่มี EXE Artifact จาก CI ให้ดาวน์โหลด วิธี B จะ Build บน Windows ของคุณเองโดยตรง ไม่ต้องรอ Runner

เปิดหน้า Run ที่ล้มเหลวแล้วตรวจคำเตือนบนหน้าจอ:
https://github.com/buildsmart888/go-anastruct-2d/actions/runs/40270905445

เช็กสิทธิ์ Actions ของ Repository และ `GitHub Settings > Billing and licensing` ว่ามีปัญหาเรื่อง billing/budget/การจัดสรร Runner หรือไม่ **ยังไม่สามารถยืนยันสาเหตุได้จากสถานะที่ได้รับ**

### กรณี Build EXE ผ่านแล้ว แต่ติดขั้นตอน [8/9]

หากสคริปต์เดิมขึ้นถึง `[8/9] Comparing v0.5.4 vs v0.5.5 vs EXE`
แปลว่าคอมสร้าง `go_anastruct_worker.exe` และ Portable ZIP สำเร็จแล้ว แต่
**ยังไม่ผ่าน numerical regression** ห้ามตีความว่า EXE ผ่านการตรวจเชิงวิศวกรรม

ไม่ต้องสร้าง EXE ใหม่ ให้รัน `RETEST_STEP8_9_WINDOWS.cmd` ที่อยู่ในโฟลเดอร์
โปรเจกต์เดียวกับ `.local-build/` และ `dist/` (ดาวน์โหลดไฟล์ .cmd ล่าสุดจาก
GitHub หาก ZIP เก่าของคุณยังไม่มีไฟล์นี้) จะใช้ EXE และ Python environment
เดิมเพื่อทดสอบเฉพาะขั้นตอน 8 และ 9 และพิมพ์ Error เต็มออกหน้าจอทันที

หรือเปิด PowerShell ในโฟลเดอร์โปรเจกต์แล้วอ่าน Log รอบล่าสุด:

```powershell
Get-Content -LiteralPath ".\.local-build\build-and-test-v055.log" -Tail 100
```

หากพบผล N/V/M/Deflection ต่างกัน **อย่าปรับ tolerance หรือแก้ผลเพื่อให้ผ่าน**
ให้ส่งบรรทัด AssertionError / RuntimeError พร้อมชื่อ Case ให้ผู้พัฒนาตรวจสอบ

# ข้อควรระวัง

- ผลคำนวณทั้งหมดเป็นรุ่นทดลอง ต้องตรวจสอบทางวิศวกรรมก่อนใช้ออกแบบจริง
- Build บน Windows 10/11 x64 ตามข้อกำหนด และไม่ใช้ไฟล์ EXE จากแหล่งที่ไม่น่าเชื่อถือ
- การตรวจสอบ SHA-256 ของ ZIP กับ manifest ในโฟลเดอร์เดียวกันไม่ใช่การยืนยันตัวผู้เผยแพร่ ต้องตรวจเทียบค่า checksum กับแหล่งเผยแพร่ที่ยืนยันได้
- ยังต้องทดสอบ GUI จริงทั้ง Windows 10 และ 11 ก่อนออก Public Release

รายละเอียดเงื่อนไข Release: [V055_RELEASE_GATE.md](V055_RELEASE_GATE.md)
