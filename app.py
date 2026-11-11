import os
import getpass
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from flask import Flask, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import inspect, or_, text
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "admin_login"
login_manager.login_message = "กรุณาเข้าสู่ระบบเจ้าหน้าที่ก่อน"
login_manager.login_message_category = "warning"
FACULTY_ALIASES = {
    "เกษตรศาสตร์ ทรัพยากรธรรมชาติและสิ่งแวดล้อม":
        "เกษตรศาสตร์ ทรัพยากรธรรมชาติ และสิ่งแวดล้อม",
}


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False, unique=True)
    departments = db.relationship("Department", backref="faculty", lazy=True)


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    degree_level = db.Column(db.String(20), nullable=False, default="Master")
    graduates = db.relationship("Graduate", backref="department", lazy=True)
    __table_args__ = (db.UniqueConstraint("faculty_id", "name", name="uq_department_faculty_name"),)


class Employer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(220), nullable=False, unique=True)
    assignments = db.relationship("GraduateAssignment", backref="employer", lazy=True)


class Graduate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(180), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False, index=True)
    job_title = db.Column(db.String(180), nullable=True)
    assignments = db.relationship("GraduateAssignment", backref="graduate", lazy=True)


class GraduateAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=False, index=True)
    graduate_id = db.Column(db.Integer, db.ForeignKey("graduate.id"), nullable=False, index=True)
    __table_args__ = (db.UniqueConstraint("employer_id", "graduate_id", name="uq_employer_graduate"),)


class EvaluationRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    is_open = db.Column(db.Boolean, nullable=False, default=True)


class QuestionSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    questions = db.relationship("Question", backref="question_set", cascade="all, delete-orphan", lazy=True)
    department = db.relationship("Department")
    __table_args__ = (db.UniqueConstraint("department_id", "version", name="uq_question_set_dept_version"),)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_set_id = db.Column(db.Integer, db.ForeignKey("question_set.id"), nullable=False, index=True)
    section = db.Column(db.Integer, nullable=False)
    group_name = db.Column(db.String(100), nullable=True)
    question_code = db.Column(db.String(40), nullable=False)
    text = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=1)
    is_required = db.Column(db.Boolean, nullable=False, default=True)
    allow_na = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (db.UniqueConstraint("question_set_id", "question_code", name="uq_question_set_code"),)


class EvaluationLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(80), nullable=False, unique=True, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False, index=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=True, index=True)
    round_id = db.Column(db.Integer, db.ForeignKey("evaluation_round.id"), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    department = db.relationship("Department")
    employer = db.relationship("Employer")
    round = db.relationship("EvaluationRound")
    __table_args__ = (db.UniqueConstraint("department_id", "employer_id", "round_id", name="uq_link_dept_employer_round"),)


class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.Integer, db.ForeignKey("evaluation_link.id"), nullable=False, index=True)
    round_id = db.Column(db.Integer, db.ForeignKey("evaluation_round.id"), nullable=False, index=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=True, index=True)
    graduate_id = db.Column(db.Integer, db.ForeignKey("graduate.id"), nullable=True, index=True)
    question_set_id = db.Column(db.Integer, db.ForeignKey("question_set.id"), nullable=False, index=True)
    respondent_gender = db.Column(db.String(30), nullable=True)
    respondent_age = db.Column(db.String(40), nullable=True)
    respondent_position = db.Column(db.String(180), nullable=True)
    employer_type = db.Column(db.String(80), nullable=True)
    work_duration = db.Column(db.String(80), nullable=True)
    job_alignment = db.Column(db.String(40), nullable=True)
    evaluated_job_title = db.Column(db.String(180), nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    link = db.relationship("EvaluationLink")
    graduate = db.relationship("Graduate")
    employer = db.relationship("Employer")
    round = db.relationship("EvaluationRound")
    question_set = db.relationship("QuestionSet")
    answers = db.relationship("EvaluationAnswer", backref="evaluation", cascade="all, delete-orphan", lazy=True)
    __table_args__ = (db.UniqueConstraint("round_id", "graduate_id", name="uq_evaluation_round_graduate"),)


class EvaluationAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey("evaluation.id"), nullable=False, index=True)
    section = db.Column(db.Integer, nullable=False)
    group_name = db.Column(db.String(100), nullable=True)
    question_code = db.Column(db.String(40), nullable=False)
    answer_text = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, nullable=True)


class ImportLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"), nullable=True, index=True)
    source_file = db.Column(db.String(255), nullable=False)
    data_type = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    rows_seen = db.Column(db.Integer, nullable=False, default=0)
    rows_imported = db.Column(db.Integer, nullable=False, default=0)
    rows_rejected = db.Column(db.Integer, nullable=False, default=0)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)
    entity_id = db.Column(db.String(80), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


def load_questionnaire_seed():
    seed_path = Path(__file__).resolve().parent / "data" / "questionnaires_2567.json"
    with seed_path.open("r", encoding="utf-8") as source:
        return json.load(source)


def upgrade_legacy_schema():
    """Add the columns needed by curriculum-level forms without dropping data."""
    inspector = inspect(db.engine)
    department_columns = {column["name"] for column in inspector.get_columns("department")}
    evaluation_columns = {column["name"] for column in inspector.get_columns("evaluation")}
    link_columns = {column["name"] for column in inspector.get_columns("evaluation_link")}
    with db.engine.begin() as connection:
        if "degree_level" not in department_columns:
            connection.execute(text(
                "ALTER TABLE department ADD COLUMN degree_level VARCHAR(20) NOT NULL DEFAULT 'Master'"
            ))
        if "evaluated_job_title" not in evaluation_columns:
            connection.execute(text(
                "ALTER TABLE evaluation ADD COLUMN evaluated_job_title VARCHAR(180) NULL"
            ))
        if "graduate_id" in evaluation_columns:
            connection.execute(text("ALTER TABLE evaluation MODIFY COLUMN graduate_id INT NULL"))
        if "employer_id" in evaluation_columns:
            connection.execute(text("ALTER TABLE evaluation MODIFY COLUMN employer_id INT NULL"))
        if "employer_id" in link_columns:
            connection.execute(text("ALTER TABLE evaluation_link MODIFY COLUMN employer_id INT NULL"))


def replace_question_set(department, name, section3_questions, section4_questions, version):
    question_set = QuestionSet.query.filter_by(department_id=department.id, version=version).first()
    if question_set and Evaluation.query.filter_by(question_set_id=question_set.id).first():
        raise ValueError(f"หลักสูตร {department.name} มีผลประเมินที่ใช้ชุดคำถามนี้แล้ว")
    if question_set is None:
        question_set = QuestionSet(
            department_id=department.id, name=name, version=version, is_active=True
        )
        db.session.add(question_set)
        db.session.flush()
    else:
        question_set.name = name
        question_set.is_active = True
        question_set.questions.clear()
        db.session.flush()
    for order, question_text in enumerate(section3_questions, start=1):
        db.session.add(Question(
            question_set_id=question_set.id, section=3,
            question_code=f"PLO-{order:02d}", text=question_text,
            sort_order=order, is_required=True, allow_na=False,
        ))
    for order, item in enumerate(section4_questions, start=1):
        db.session.add(Question(
            question_set_id=question_set.id, section=4,
            group_name=item["group"], question_code=f"TQF-{order:02d}",
            text=item["text"], sort_order=order, is_required=True, allow_na=True,
        ))
    department.degree_level = department.degree_level or "Master"
    return question_set


def create_app():
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    secret_key = os.environ.get("SECRET_KEY", "").strip()
    if not database_url.startswith("mysql+pymysql://"):
        raise RuntimeError("กำหนด DATABASE_URL สำหรับ MySQL ในไฟล์ .env ก่อนเริ่มระบบ")
    if not secret_key:
        raise RuntimeError("กำหนด SECRET_KEY ในไฟล์ .env ก่อนเริ่มระบบ")
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        MAX_CONTENT_LENGTH=12 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
    )
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/survey-preview")
    def survey_preview():
        """Show a non-submittable survey preview without writing sample rows to MySQL."""
        def preview_question(question_id, text, allow_na=False):
            return SimpleNamespace(
                id=question_id, text=text, is_required=True, allow_na=allow_na
            )

        link = SimpleNamespace(
            token="preview",
            round=SimpleNamespace(academic_year="ตัวอย่าง"),
            department=SimpleNamespace(name="เทคนิคการแพทย์ (ตัวอย่าง)"),
        )
        graduates = [SimpleNamespace(
            id=1, code="A67001", full_name="บัณฑิตตัวอย่าง", job_title="นักเทคนิคการแพทย์"
        )]
        section3_questions = [
            preview_question(9301, "มีความรู้ตามหลักสูตรและสามารถนำไปประยุกต์ใช้ในการทำงานได้"),
            preview_question(9302, "สามารถวิเคราะห์ข้อมูลและเลือกใช้วิธีการทำงานได้เหมาะสม"),
            preview_question(9303, "สามารถใช้เทคโนโลยีและเครื่องมือที่เกี่ยวข้องกับงานได้"),
        ]
        section4_groups = {
            "เก่งงาน": [preview_question(9401, "มีความรู้และทักษะที่จำเป็นต่องาน"), preview_question(9402, "รับผิดชอบและทำงานได้อย่างมีประสิทธิภาพ")],
            "เก่งคน": [preview_question(9403, "สื่อสารและทำงานร่วมกับผู้อื่นได้ดี"), preview_question(9404, "มีมนุษยสัมพันธ์และให้บริการอย่างเหมาะสม")],
            "เก่งคิด": [preview_question(9405, "คิดวิเคราะห์และแก้ไขปัญหาได้"), preview_question(9406, "เรียนรู้สิ่งใหม่และพัฒนาตนเองอย่างต่อเนื่อง")],
            "เก่งครองชีวิต": [preview_question(9407, "ปรับตัวต่อการเปลี่ยนแปลงได้"), preview_question(9408, "มีวินัยและรับผิดชอบต่อสังคม")],
            "เก่งพิชิตปัญหา": [preview_question(9409, "ประยุกต์ใช้ความรู้เพื่อแก้ปัญหาในงานได้", True)],
        }
        return render_template(
            "survey.html", link=link, graduates=graduates,
            section3_questions=section3_questions, section4_groups=section4_groups,
            preview_mode=True,
        )

    @app.get("/survey/<token>")
    def survey(token):
        link = EvaluationLink.query.filter_by(token=token, is_active=True).first_or_404()
        if not link.round.is_open:
            return render_template("survey_closed.html", link=link), 410
        graduates = []
        if link.employer_id:
            assigned = GraduateAssignment.query.filter_by(employer_id=link.employer_id).join(Graduate).filter(
                Graduate.department_id == link.department_id
            ).all()
            done_ids = {
                row[0] for row in db.session.query(Evaluation.graduate_id).filter_by(
                    round_id=link.round_id
                ).filter(Evaluation.graduate_id.isnot(None)).all()
            }
            graduates = [a.graduate for a in assigned if a.graduate_id not in done_ids]
        question_set = QuestionSet.query.filter_by(department_id=link.department_id, is_active=True).order_by(
            QuestionSet.version.desc()
        ).first()
        questions = Question.query.filter_by(question_set_id=question_set.id).order_by(
            Question.section, Question.sort_order
        ).all() if question_set else []
        if not question_set or not questions:
            return render_template("survey_unconfigured.html", link=link), 503
        section3_questions = [q for q in questions if q.section == 3]
        section4_groups = {}
        for question in questions:
            if question.section == 4:
                section4_groups.setdefault(question.group_name or "สมรรถนะ", []).append(question)
        return render_template(
            "survey.html",
            link=link,
            graduates=graduates,
            individual_mode=bool(link.employer_id),
            section3_questions=section3_questions,
            section4_groups=section4_groups,
        )

    @app.post("/survey/<token>/submit")
    def survey_submit(token):
        link = EvaluationLink.query.filter_by(token=token, is_active=True).first_or_404()
        if not link.round.is_open:
            abort(410)
        graduate = None
        if link.employer_id:
            graduate_id = request.form.get("graduate_id", type=int)
            graduate = Graduate.query.filter_by(id=graduate_id, department_id=link.department_id).first()
            assignment = GraduateAssignment.query.filter_by(
                employer_id=link.employer_id, graduate_id=graduate_id
            ).first()
            if not graduate or not assignment:
                abort(403)
            if Evaluation.query.filter_by(round_id=link.round_id, graduate_id=graduate.id).first():
                flash("บัณฑิตคนนี้ได้รับการประเมินในรอบนี้แล้ว", "warning")
                return redirect(url_for("survey", token=token))
        question_set = QuestionSet.query.filter_by(department_id=link.department_id, is_active=True).order_by(
            QuestionSet.version.desc()
        ).first()
        if not question_set:
            abort(409, "ยังไม่ได้กำหนดชุดคำถามให้หลักสูตรนี้")
        question_rows = Question.query.filter_by(question_set_id=question_set.id).all()
        required_fields = [
            "respondent_gender", "respondent_age", "respondent_position", "employer_type",
            "work_duration", "job_alignment", "evaluated_job_title",
        ]
        if graduate:
            required_fields.remove("evaluated_job_title")
        missing_profile = [field for field in required_fields if not request.form.get(field, "").strip()]
        missing_scores = [
            f"answer_{q.id}" for q in question_rows
            if q.is_required and not request.form.get(f"answer_{q.id}")
        ]
        if missing_profile or missing_scores:
            flash("กรุณาตอบคำถามที่จำเป็นก่อนส่งแบบประเมิน", "warning")
            return redirect(url_for("survey", token=token))
        evaluation = Evaluation(
            link_id=link.id,
            round_id=link.round_id,
            employer_id=link.employer_id,
            graduate_id=graduate.id if graduate else None,
            question_set_id=question_set.id,
            respondent_gender=request.form.get("respondent_gender"),
            respondent_age=request.form.get("respondent_age"),
            respondent_position=request.form.get("respondent_position", "").strip(),
            employer_type=request.form.get("employer_type"),
            work_duration=request.form.get("work_duration"),
            job_alignment=request.form.get("job_alignment"),
            evaluated_job_title=(graduate.job_title if graduate else request.form.get("evaluated_job_title", "").strip()),
        )
        try:
            db.session.add(evaluation)
            db.session.flush()
            for question in question_rows:
                value = request.form.get(f"answer_{question.id}", "")
                if not value:
                    continue
                valid_values = {"1", "2", "3", "4", "5"}
                if question.allow_na:
                    valid_values.add("0")
                if value not in valid_values:
                    raise ValueError("Invalid answer value")
                score = int(value) if value != "0" else None
                db.session.add(EvaluationAnswer(
                    evaluation_id=evaluation.id, section=question.section,
                    group_name=question.group_name, question_code=question.question_code,
                    answer_text="N/A" if value == "0" else None, score=score
                ))
            section5_fields = [
                ("5.1.1", "ความคิดเห็นต่อบัณฑิต", "ความรู้", "section5_knowledge"),
                ("5.1.2", "ความคิดเห็นต่อบัณฑิต", "ทักษะ", "section5_skills"),
                ("5.1.3", "ความคิดเห็นต่อบัณฑิต", "จริยธรรม", "section5_ethics"),
                ("5.1.4", "ความคิดเห็นต่อบัณฑิต", "ลักษณะบุคคล", "section5_character"),
                ("5.2", "ความคิดเห็นต่อมหาวิทยาลัย", "มหาวิทยาลัยนเรศวร", "section5_university"),
                ("5.3", "ข้อชมเชยและข้อเสนอแนะ", "ข้อเสนอแนะอื่น ๆ", "section5_suggestions"),
                ("5.4", "คุณลักษณะบัณฑิตที่พึงประสงค์", "คุณลักษณะเพิ่มเติม", "section5_desired_attributes"),
            ]
            for question_code, group_name, label, field_name in section5_fields:
                answer_text = request.form.get(field_name, "").strip()
                if len(answer_text) > 5000:
                    raise ValueError("Section 5 response is too long")
                if answer_text:
                    db.session.add(EvaluationAnswer(
                        evaluation_id=evaluation.id, section=5, group_name=group_name,
                        question_code=question_code, answer_text=answer_text, score=None
                    ))
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Unable to save evaluation")
            flash("บันทึกไม่สำเร็จ กรุณาตรวจคำตอบและลองอีกครั้ง", "danger")
            return redirect(url_for("survey", token=token))
        return render_template("survey_success.html", link=link, graduate=graduate)

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if current_user.is_authenticated:
            return redirect(url_for("admin_dashboard"))
        if request.method == "POST":
            user = Admin.query.filter_by(username=request.form.get("username", "").strip()).first()
            if user and user.check_password(request.form.get("password", "")):
                login_user(user)
                return redirect(url_for("admin_dashboard"))
            flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "danger")
        return render_template("admin_login.html")

    @app.post("/admin/logout")
    @login_required
    def admin_logout():
        logout_user()
        return redirect(url_for("admin_login"))

    @app.post("/admin/faculties/create")
    @login_required
    def create_faculty():
        name = request.form.get("name", "").strip()
        if not name:
            flash("กรุณาระบุชื่อคณะหรือวิทยาลัย", "warning")
        elif Faculty.query.filter_by(name=name).first():
            flash("มีชื่อคณะหรือวิทยาลัยนี้ในระบบแล้ว", "warning")
        else:
            db.session.add(Faculty(name=name))
            db.session.commit()
            flash("เพิ่มคณะหรือวิทยาลัยแล้ว", "success")
        return redirect(url_for("admin_dashboard", view="manage"))

    @app.post("/admin/faculties/<int:faculty_id>/delete")
    @login_required
    def delete_faculty(faculty_id):
        faculty = db.session.get(Faculty, faculty_id)
        if not faculty:
            flash("ไม่พบคณะหรือวิทยาลัยที่ต้องการลบ", "warning")
        else:
            department_count = Department.query.filter_by(faculty_id=faculty.id).count()
            if department_count:
                flash(
                    f"ยังลบ {faculty.name} ไม่ได้ เพราะมีหลักสูตรผูกอยู่ {department_count} หลักสูตร",
                    "warning",
                )
            else:
                db.session.delete(faculty)
                db.session.commit()
                flash(f"ลบ {faculty.name} แล้ว", "success")
        return redirect(url_for("admin_dashboard", view="manage"))

    @app.post("/admin/curricula/<int:curriculum_id>/delete")
    @login_required
    def delete_curriculum(curriculum_id):
        curriculum = db.session.get(Department, curriculum_id)
        if not curriculum:
            flash("ไม่พบหลักสูตรที่ต้องการลบ", "warning")
            return redirect(url_for("admin_dashboard", view="manage"))

        faculty_id = curriculum.faculty_id
        question_set_ids = [row.id for row in QuestionSet.query.filter_by(department_id=curriculum.id).all()]
        link_ids = [row.id for row in EvaluationLink.query.filter_by(department_id=curriculum.id).all()]
        has_graduates = Graduate.query.filter_by(department_id=curriculum.id).first() is not None
        evaluation_query = Evaluation.query.outerjoin(
            EvaluationLink, Evaluation.link_id == EvaluationLink.id
        )
        evaluation_filters = []
        if link_ids:
            evaluation_filters.append(Evaluation.link_id.in_(link_ids))
        if question_set_ids:
            evaluation_filters.append(Evaluation.question_set_id.in_(question_set_ids))
        has_evaluations = bool(evaluation_filters) and evaluation_query.filter(
            or_(*evaluation_filters)
        ).first() is not None

        if has_graduates or has_evaluations:
            flash(
                f"ยังลบหลักสูตร {curriculum.name} ไม่ได้ เพราะมีข้อมูลบัณฑิตหรือผลประเมินผูกอยู่ ระบบเก็บข้อมูลเหล่านี้ไว้เพื่อรักษาประวัติ",
                "warning",
            )
        else:
            try:
                for link in EvaluationLink.query.filter_by(department_id=curriculum.id).all():
                    db.session.delete(link)
                for question_set in QuestionSet.query.filter_by(department_id=curriculum.id).all():
                    db.session.delete(question_set)
                db.session.delete(curriculum)
                db.session.commit()
                flash(f"ลบหลักสูตร {curriculum.name} และชุดคำถามแล้ว", "success")
            except Exception:
                db.session.rollback()
                app.logger.exception("Unable to delete curriculum %s", curriculum_id)
                flash("ลบหลักสูตรไม่สำเร็จ เนื่องจากยังมีข้อมูลอื่นอ้างถึงอยู่", "danger")
        return redirect(url_for("admin_dashboard", faculty=faculty_id, view="manage"))

    @app.post("/admin/curricula/create")
    @login_required
    def create_curriculum():
        faculty = db.session.get(Faculty, request.form.get("faculty_id", type=int))
        name = request.form.get("name", "").strip()
        degree_level = request.form.get("degree_level", "")
        question_texts = [line.strip() for line in request.form.get("section3_questions", "").splitlines() if line.strip()]
        if not faculty or not name or degree_level not in {"Master", "Doctorate"}:
            flash("กรุณาระบุคณะ หลักสูตร และระดับปริญญาให้ครบ", "warning")
            return redirect(url_for("admin_dashboard", view="manage"))
        if not question_texts or len(question_texts) > 80:
            flash("กรุณาใส่คำถามตอนที่ 3 อย่างน้อย 1 ข้อ (ไม่เกิน 80 ข้อ)", "warning")
            return redirect(url_for("admin_dashboard", view="manage"))
        if Department.query.filter_by(faculty_id=faculty.id, name=name).first():
            flash("มีหลักสูตรชื่อนี้ในคณะที่เลือกแล้ว", "warning")
            return redirect(url_for("admin_dashboard", view="manage"))
        try:
            curriculum = Department(faculty_id=faculty.id, name=name, degree_level=degree_level)
            db.session.add(curriculum)
            db.session.flush()
            seed = load_questionnaire_seed()
            replace_question_set(
                curriculum, f"ชุดคำถาม {name}", question_texts,
                seed["common_section4_questions"], version=1,
            )
            db.session.commit()
            flash("เพิ่มหลักสูตรและชุดคำถามแล้ว", "success")
        except Exception:
            db.session.rollback()
            app.logger.exception("Unable to create curriculum")
            flash("บันทึกหลักสูตรไม่สำเร็จ กรุณาตรวจข้อมูลแล้วลองอีกครั้ง", "danger")
        return redirect(url_for("admin_dashboard", faculty=faculty.id, view="manage"))

    @app.post("/admin/rounds/create")
    @login_required
    def create_round():
        academic_year = request.form.get("academic_year", "").strip()
        name = request.form.get("name", "").strip() or (f"ปีการศึกษา {academic_year}" if academic_year else "")
        if not academic_year or not name:
            flash("กรุณาระบุปีการศึกษา", "warning")
        elif EvaluationRound.query.filter_by(academic_year=academic_year).first():
            flash("มีรอบประเมินปีนี้แล้ว", "warning")
        else:
            db.session.add(EvaluationRound(name=name, academic_year=academic_year, is_open=True))
            db.session.commit()
            flash("เพิ่มรอบประเมินแล้ว", "success")
        return redirect(url_for("admin_dashboard", view="manage"))

    @app.post("/admin/links/create")
    @login_required
    def create_survey_link():
        curriculum = db.session.get(Department, request.form.get("department_id", type=int))
        degree_level = request.form.get("degree_level", "")
        round_row = db.session.get(EvaluationRound, request.form.get("round_id", type=int))
        if not curriculum or degree_level not in {"Master", "Doctorate"} or curriculum.degree_level != degree_level:
            flash("เลือกระดับปริญญาและหลักสูตรให้ตรงกันก่อนสร้างลิงก์", "warning")
        elif not round_row or not round_row.is_open:
            flash("เลือกหลักสูตรและรอบประเมินที่เปิดอยู่ก่อนสร้างลิงก์", "warning")
        elif not QuestionSet.query.filter_by(department_id=curriculum.id, is_active=True).first():
            flash("หลักสูตรนี้ยังไม่มีชุดคำถามที่ใช้งานได้", "warning")
        else:
            link = EvaluationLink.query.filter_by(
                department_id=curriculum.id, employer_id=None,
                round_id=round_row.id, is_active=True,
            ).first()
            if not link:
                link = EvaluationLink(
                    token=secrets.token_urlsafe(32), department_id=curriculum.id,
                    employer_id=None, round_id=round_row.id, is_active=True,
                )
                db.session.add(link)
                db.session.commit()
            flash("ลิงก์แบบประเมินพร้อมส่งให้นายจ้างแล้ว · กดเพื่อไปยังรายการลิงก์ ↓", "link-created")
        return redirect(url_for(
            "admin_dashboard",
            faculty=curriculum.faculty_id if curriculum else None,
            department=curriculum.id if curriculum else None,
            round=round_row.id if round_row else None,
            view="manage",
        ))

    @app.get("/admin")
    @app.get("/admin/dashboard")
    @login_required
    def admin_dashboard():
        faculties = Faculty.query.order_by(Faculty.name).all()
        faculty_id = request.args.get("faculty", type=int)
        if faculty_id not in {f.id for f in faculties}:
            faculty_id = faculties[0].id if faculties else None
        department_query = Department.query
        if faculty_id:
            department_query = department_query.filter_by(faculty_id=faculty_id)
        departments = department_query.filter(
            Department.degree_level.in_(["Master", "Doctorate"])
        ).order_by(Department.name).all()
        department_id = request.args.get("department", type=int)
        if department_id not in {d.id for d in departments}:
            department_id = None
        selected_department = db.session.get(Department, department_id) if department_id else None
        rounds = EvaluationRound.query.order_by(EvaluationRound.academic_year.desc(), EvaluationRound.id.desc()).all()
        round_id = request.args.get("round", type=int)
        round_row = db.session.get(EvaluationRound, round_id) if round_id else (rounds[0] if rounds else None)
        if round_row not in rounds:
            round_row = rounds[0] if rounds else None

        department_ids = [department_id] if department_id else [row.id for row in departments]
        evaluations = []
        if round_row and department_ids:
            evaluations = Evaluation.query.join(
                EvaluationLink, Evaluation.link_id == EvaluationLink.id
            ).filter(
                Evaluation.round_id == round_row.id,
                EvaluationLink.department_id.in_(department_ids),
            ).order_by(Evaluation.submitted_at.desc()).all()

        scores3 = [answer.score for evaluation in evaluations for answer in evaluation.answers
                   if answer.section == 3 and answer.score is not None]
        scores4 = [answer.score for evaluation in evaluations for answer in evaluation.answers
                   if answer.section == 4 and answer.score is not None]
        all_scores = scores3 + scores4
        average3 = round(sum(scores3) / len(scores3), 2) if scores3 else None
        average4 = round(sum(scores4) / len(scores4), 2) if scores4 else None
        overall_average = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
        satisfaction_rate = round(sum(score >= 4 for score in all_scores) / len(all_scores) * 100, 1) if all_scores else None
        total_graduates = Graduate.query.filter(Graduate.department_id.in_(department_ids)).count() if department_ids else 0
        evaluated_graduate_ids = {evaluation.graduate_id for evaluation in evaluations if evaluation.graduate_id}
        evaluated_graduates = len(evaluated_graduate_ids)
        response_rate = round(evaluated_graduates / total_graduates * 100, 1) if total_graduates else None

        course_rows = []
        for course in departments:
            course_evaluations = [evaluation for evaluation in evaluations
                                  if evaluation.link.department_id == course.id]
            course_scores3 = [answer.score for evaluation in course_evaluations for answer in evaluation.answers
                              if answer.section == 3 and answer.score is not None]
            course_scores4 = [answer.score for evaluation in course_evaluations for answer in evaluation.answers
                              if answer.section == 4 and answer.score is not None]
            course_graduates = Graduate.query.filter_by(department_id=course.id).count()
            course_evaluated_ids = {evaluation.graduate_id for evaluation in course_evaluations if evaluation.graduate_id}
            course_rows.append({
                "id": course.id, "name": course.name, "degree_level": course.degree_level,
                "graduates": course_graduates, "respondents": len(course_evaluations),
                "evaluated_graduates": len(course_evaluated_ids),
                "rate": round(len(course_evaluated_ids) / course_graduates * 100, 1) if course_graduates else None,
                "average3": round(sum(course_scores3) / len(course_scores3), 2) if course_scores3 else None,
                "average4": round(sum(course_scores4) / len(course_scores4), 2) if course_scores4 else None,
            })

        question_stats = []
        if selected_department:
            question_set = QuestionSet.query.filter_by(
                department_id=selected_department.id, is_active=True
            ).order_by(QuestionSet.version.desc()).first()
            if question_set:
                for question in sorted(question_set.questions, key=lambda row: (row.section, row.sort_order)):
                    values = [answer.score for evaluation in evaluations for answer in evaluation.answers
                              if answer.section == question.section
                              and answer.question_code == question.question_code
                              and answer.group_name == question.group_name
                              and answer.score is not None]
                    question_stats.append({
                        "section": question.section, "group": question.group_name,
                        "text": question.text,
                        "average": round(sum(values) / len(values), 2) if values else None,
                        "count": len(values),
                    })

        group_values = {}
        for evaluation in evaluations:
            for answer in evaluation.answers:
                if answer.section == 4 and answer.score is not None:
                    group_values.setdefault(answer.group_name or "สมรรถนะ", []).append(answer.score)
        tqf_rows = [{"name": name, "average": round(sum(values) / len(values), 2), "count": len(values)}
                    for name, values in group_values.items()]
        profile_sections = [
            {"title": "ตอนที่ 1 · ข้อมูลผู้ประเมิน", "fields": [
                ("เพศ", "respondent_gender"), ("ช่วงอายุ", "respondent_age"),
                ("ตำแหน่งผู้ประเมิน", "respondent_position"), ("ประเภทหน่วยงาน", "employer_type"),
            ]},
            {"title": "ตอนที่ 2 · ข้อมูลบัณฑิตที่ประเมิน", "fields": [
                ("ตำแหน่งงานบัณฑิต", "evaluated_job_title"), ("ระยะเวลาทำงาน", "work_duration"),
                ("ทำงานตรงหรือสอดคล้องกับสาขา", "job_alignment"),
            ]},
        ]
        for section in profile_sections:
            summaries = []
            for label, field in section["fields"]:
                counts = {}
                for evaluation in evaluations:
                    value = getattr(evaluation, field) or "ไม่ระบุ"
                    counts[value] = counts.get(value, 0) + 1
                summaries.append({
                    "label": label,
                    "values": [{
                        "value": value, "count": count,
                        "percent": round(count * 100 / len(evaluations), 2) if evaluations else 0,
                    } for value, count in counts.items()],
                })
            section["summaries"] = summaries
        comments = [
            answer for evaluation in evaluations for answer in evaluation.answers
            if answer.section == 5 and answer.answer_text
        ]

        survey_links = []
        if department_ids:
            links_query = EvaluationLink.query.filter(
                EvaluationLink.is_active.is_(True),
                EvaluationLink.department_id.in_(department_ids),
            )
            if round_row:
                links_query = links_query.filter_by(round_id=round_row.id)
            survey_links = links_query.order_by(EvaluationLink.id.desc()).all()

        trend_courses = Department.query.filter(Department.degree_level.in_(["Master", "Doctorate"]))
        if faculty_id:
            trend_courses = trend_courses.filter_by(faculty_id=faculty_id)
        degree_filter = request.args.get("degree", "all")
        if degree_filter not in {"all", "Master", "Doctorate"}:
            degree_filter = "all"
        if degree_filter in {"Master", "Doctorate"}:
            trend_courses = trend_courses.filter_by(degree_level=degree_filter)
        trend_course_ids = [course.id for course in trend_courses.all()]
        trend_evaluations = []
        if trend_course_ids:
            trend_evaluations = Evaluation.query.join(
                EvaluationLink, Evaluation.link_id == EvaluationLink.id
            ).filter(EvaluationLink.department_id.in_(trend_course_ids)).all()
        years = sorted({evaluation.round.academic_year for evaluation in trend_evaluations})
        trend_data = {}
        for level in ("Master", "Doctorate"):
            level_rows = []
            for year in years:
                year_evaluations = [evaluation for evaluation in trend_evaluations
                                    if evaluation.round.academic_year == year
                                    and evaluation.link.department.degree_level == level]
                year3 = [answer.score for evaluation in year_evaluations for answer in evaluation.answers
                         if answer.section == 3 and answer.score is not None]
                year4 = [answer.score for evaluation in year_evaluations for answer in evaluation.answers
                         if answer.section == 4 and answer.score is not None]
                combined = year3 + year4
                to_percent = lambda values: round(sum(value >= 4 for value in values) / len(values) * 100, 1) if values else None
                level_rows.append({
                    "year": year, "n": len(year_evaluations), "section3": to_percent(year3),
                    "section4": to_percent(year4), "overall": to_percent(combined),
                })
            trend_data[level] = level_rows

        faculty_rows = []
        for faculty in faculties:
            faculty_courses = [course for course in departments if course.faculty_id == faculty.id]
            if not faculty_courses:
                continue
            faculty_ids = {course.id for course in faculty_courses}
            faculty_evaluations = [evaluation for evaluation in evaluations
                                   if evaluation.link.department_id in faculty_ids]
            faculty_scores = [answer.score for evaluation in faculty_evaluations for answer in evaluation.answers
                              if answer.section in (3, 4) and answer.score is not None]
            faculty_rows.append({
                "name": faculty.name, "respondents": len(faculty_evaluations),
                "average": round(sum(faculty_scores) / len(faculty_scores), 2) if faculty_scores else None,
            })

        return render_template(
            "admin_dashboard.html",
            faculties=faculties, departments=departments, faculty_id=faculty_id,
            department_id=department_id, selected_department=selected_department,
            rounds=rounds, round_row=round_row, respondent_count=len(evaluations),
            total_graduates=total_graduates, evaluated_graduates=evaluated_graduates,
            response_rate=response_rate, average3=average3, average4=average4,
            overall_average=overall_average, satisfaction_rate=satisfaction_rate,
            course_rows=course_rows, question_stats=question_stats, tqf_rows=tqf_rows,
            profile_sections=profile_sections, comments=comments, survey_links=survey_links,
            faculty_rows=faculty_rows, trend_master=trend_data.get("Master", []),
            trend_doctorate=trend_data.get("Doctorate", []),
            degree_filter=degree_filter,
            chart_mode=request.args.get("view") == "charts",
            manage_mode=request.args.get("view") == "manage",
        )

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))


app = create_app()


@app.cli.command("init-db")
def init_database_command():
    """Create the empty application schema in the configured MySQL database."""
    db.create_all()
    print("MySQL schema is ready. No test or sample records were added.")


@app.cli.command("upgrade-db")
def upgrade_database_command():
    """Create missing tables and add nullable graduate fields for course-level surveys."""
    db.create_all()
    upgrade_legacy_schema()
    print("Database structure is ready for curriculum-level surveys.")


@app.cli.command("import-questionnaires")
def import_questionnaires_command():
    """Import the 2567 curriculum question sets from the reviewed source manifest."""
    seed = load_questionnaire_seed()
    created_faculties = 0
    created_curricula = 0
    imported_question_sets = 0
    preserved_question_sets = 0
    try:
        db.create_all()
        upgrade_legacy_schema()
        for item in seed["curricula"]:
            faculty_name = FACULTY_ALIASES.get(item["faculty"], item["faculty"])
            faculty = Faculty.query.filter_by(name=faculty_name).first()
            if not faculty:
                faculty = Faculty(name=faculty_name)
                db.session.add(faculty)
                db.session.flush()
                created_faculties += 1
            curriculum = Department.query.filter_by(
                faculty_id=faculty.id, name=item["name"]
            ).first()
            if not curriculum:
                legacy_names = [name for name, canonical in FACULTY_ALIASES.items()
                                if canonical == faculty_name]
                if legacy_names:
                    legacy_faculty = Faculty.query.filter(Faculty.name.in_(legacy_names)).first()
                    if legacy_faculty:
                        curriculum = Department.query.filter_by(
                            faculty_id=legacy_faculty.id, name=item["name"]
                        ).first()
                        if curriculum:
                            curriculum.faculty_id = faculty.id
            if not curriculum:
                curriculum = Department(
                    faculty_id=faculty.id, name=item["name"],
                    degree_level=item["degree_level"],
                )
                db.session.add(curriculum)
                db.session.flush()
                created_curricula += 1
            else:
                curriculum.degree_level = item["degree_level"]
            current_set = QuestionSet.query.filter_by(
                department_id=curriculum.id, version=1
            ).first()
            if current_set and Evaluation.query.filter_by(question_set_id=current_set.id).first():
                preserved_question_sets += 1
                continue
            replace_question_set(
                curriculum, f"แบบสอบถามปี {seed['academic_year']}",
                item["questions"], seed["common_section4_questions"], version=1,
            )
            imported_question_sets += 1
        for legacy_name in FACULTY_ALIASES:
            legacy_faculty = Faculty.query.filter_by(name=legacy_name).first()
            if legacy_faculty and not Department.query.filter_by(faculty_id=legacy_faculty.id).first():
                db.session.delete(legacy_faculty)
        round_row = EvaluationRound.query.filter_by(academic_year=seed["academic_year"]).first()
        if not round_row:
            round_row = EvaluationRound(
                name=f"ปีการศึกษา {seed['academic_year']}",
                academic_year=seed["academic_year"], is_open=True,
            )
            db.session.add(round_row)
        db.session.add(ImportLog(
            source_file=seed["source_folder"], data_type="questionnaires",
            status="completed", rows_seen=85, rows_imported=len(seed["curricula"]),
            rows_rejected=len(seed["excluded_files"]),
            details=("นำเข้าคำถามตอนที่ 3 แยกหลักสูตร พร้อมคำถามสมรรถนะตอนที่ 4 ร่วมกัน "
                     f"เว้น {len(seed['excluded_files'])} ไฟล์ที่ข้อมูลหลักสูตรในเอกสารไม่ตรงกับชื่อไฟล์: "
                     + ", ".join(seed["excluded_files"])),
        ))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Unable to import questionnaire source data")
        raise SystemExit(f"นำเข้าชุดคำถามไม่สำเร็จ: {type(exc).__name__}")
    print(
        f"นำเข้าคณะใหม่ {created_faculties} คณะ, หลักสูตรใหม่ {created_curricula} หลักสูตร, "
        f"ชุดคำถาม {imported_question_sets} ชุด; เก็บชุดคำถามที่มีผลประเมินเดิมไว้ {preserved_question_sets} ชุด"
    )


@app.cli.command("create-admin")
def create_admin_command():
    """Create an administrator account after the MySQL schema has been migrated."""
    username = input("Username: ").strip()
    if not username:
        raise SystemExit("Username is required.")
    if Admin.query.filter_by(username=username).first():
        raise SystemExit("That username already exists.")
    password = getpass.getpass("Password (at least 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    admin = Admin(username=username)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print("Administrator account created.")
