# ระบบประเมินความพึงพอใจของนายจ้าง

โครงการใช้ Python + Flask เป็นฝั่งระบบ, MySQL เป็นฐานข้อมูล และ HTML/CSS/JavaScript สำหรับหน้าเว็บ กราฟ Dashboard ใช้ Chart.js ระบบไม่สร้างผลประเมินปลอมหรือบัญชีผู้ดูแลให้อัตโนมัติ

## ติดตั้งบน Windows เครื่องใหม่ (localhost)

โปรเจกต์ต้องมี Python 3.10 ขึ้นไป และ MySQL/MariaDB ในเครื่อง (ใช้ XAMPP ได้) โฟลเดอร์ `.venv` และไฟล์ `.env` ไม่ควรนำมาจากเครื่องเดิม ให้สร้างใหม่ตามขั้นตอนนี้

### 1. ติดตั้งและเตรียมฐานข้อมูล

1. ติดตั้ง Python และ XAMPP จากแหล่งทางการ แล้วเปิด XAMPP Control Panel และ Start `MySQL` (ถ้าจะใช้ phpMyAdmin ให้ Start `Apache` ด้วย)
2. เปิด `http://127.0.0.1/phpmyadmin` แล้ว Import ไฟล์ `sql/schema.sql` จากโปรเจกต์ ไฟล์นี้สร้างฐานข้อมูล `employer_satisfaction` และตารางเปล่า
3. ใน phpMyAdmin เลือกแท็บ SQL และสร้างผู้ใช้ของแอป (เปลี่ยนรหัสผ่านตัวอย่างก่อนรัน):

~~~sql
CREATE USER 'employer_app'@'127.0.0.1' IDENTIFIED BY 'ใส่รหัสผ่านใหม่ที่เดายาก';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON employer_satisfaction.* TO 'employer_app'@'127.0.0.1';
FLUSH PRIVILEGES;
~~~

### 2. ติดตั้ง Python packages และตั้งค่า

เปิด PowerShell ในโฟลเดอร์โปรเจกต์ แล้วรัน:

~~~powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
~~~

เปิดไฟล์ `.env` แล้วแก้ `DATABASE_URL` ให้ใช้รหัสผ่านเดียวกับผู้ใช้ MySQL ที่สร้างไว้ และกำหนด `SECRET_KEY` แบบสุ่ม เช่น สร้างค่าด้วยคำสั่ง:

~~~powershell
& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
~~~

นำค่าที่แสดงไปใส่หลัง `SECRET_KEY=` ใน `.env` อย่าแชร์ไฟล์ `.env` หรือเก็บไว้ใน Git

### 3. เตรียมบัญชีแอดมินและเปิดเว็บ

~~~powershell
& .\.venv\Scripts\python.exe -m flask --app app upgrade-db
& .\.venv\Scripts\python.exe -m flask --app app import-questionnaires
& .\.venv\Scripts\python.exe -m flask --app app create-admin
& .\.venv\Scripts\python.exe -m flask --app app run --debug
~~~

คำสั่ง `create-admin` จะถามชื่อผู้ใช้และรหัสผ่าน (อย่างน้อย 8 ตัวอักษร) จากนั้นเปิดเว็บ:

- หน้าแรก: http://127.0.0.1:5000
- เข้าสู่ระบบเจ้าหน้าที่: http://127.0.0.1:5000/admin/login
- แบบประเมิน: `/survey/<token>` หลังสร้างลิงก์จากหน้าเจ้าหน้าที่

คำสั่ง `import-questionnaires` นำเข้าคณะ หลักสูตร และคำถามตอนที่ 3 จากชุดเอกสารปี 2567 พร้อมคำถามสมรรถนะตอนที่ 4 โดยไม่สร้างผลประเมินตัวอย่าง เอกสาร 3 หลักสูตรที่ข้อมูลภายในไม่ตรงกับชื่อไฟล์จะถูกพักไว้ก่อน หน้าจัดการเจ้าหน้าที่ใช้เพิ่มคณะ วิทยาลัย รอบประเมิน และหลักสูตรพร้อมคำถามตอนที่ 3 ได้

ในระยะนี้แบบฟอร์มเก็บผลประเมินภาพรวมของหลักสูตร การเลือกบัณฑิตรายบุคคลและการคำนวณอัตราตอบกลับต่อจำนวนบัณฑิตจะเปิดใช้เมื่อเพิ่มฐานข้อมูลบัณฑิต

เว็บนี้จะเปิดให้เข้าได้เฉพาะเครื่องที่รัน Flask อยู่ ส่วนฐานข้อมูลจริงจากเครื่องเดิมไม่ได้ติดมากับไฟล์โปรเจกต์ หากต้องการย้ายข้อมูลจริง ให้ Export ฐานข้อมูลจาก MySQL เครื่องเดิม แล้ว Import แยกบนเครื่องใหม่

## โครงสร้างฐานข้อมูล

มีตารางสำหรับ admins, faculties, curricula (ใช้ตาราง departments), employers, graduates, employer-graduate assignments, evaluation rounds, question sets, questions, evaluation links, evaluations, answers, import logs และ audit logs

การปรับ schema ในอนาคตใช้ Flask-Migrate/Alembic หลังตั้งค่าการเชื่อมต่อ MySQL แล้ว

## ความปลอดภัยก่อนใช้งานจริง

ตั้ง SECRET_KEY แบบสุ่มและเก็บใน environment, เปิด HTTPS และตั้ง COOKIE_SECURE=1 ใน production ใช้บัญชี MySQL สิทธิ์จำกัด และใช้ create-admin สำหรับบัญชีเจ้าหน้าที่ ห้ามใช้ root หรือฝังรหัสผ่านไว้ในโค้ด
