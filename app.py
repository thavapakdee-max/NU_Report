import os
import getpass
from datetime import datetime, timezone
from types import SimpleNamespace

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "admin_login"
login_manager.login_message = "กรุณาเข้าสู่ระบบเจ้าหน้าที่ก่อน"
login_manager.login_message_category = "warning"


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
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=False, index=True)
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
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=False, index=True)
    graduate_id = db.Column(db.Integer, db.ForeignKey("graduate.id"), nullable=False, index=True)
    question_set_id = db.Column(db.Integer, db.ForeignKey("question_set.id"), nullable=False, index=True)
    respondent_gender = db.Column(db.String(30), nullable=True)
    respondent_age = db.Column(db.String(40), nullable=True)
    respondent_position = db.Column(db.String(180), nullable=True)
    employer_type = db.Column(db.String(80), nullable=True)
    work_duration = db.Column(db.String(80), nullable=True)
    job_alignment = db.Column(db.String(40), nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    graduate = db.relationship("Graduate")
    employer = db.relationship("Employer")
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
        assigned = GraduateAssignment.query.filter_by(employer_id=link.employer_id).join(Graduate).filter(
            Graduate.department_id == link.department_id
        ).all()
        done_ids = {
            row[0] for row in db.session.query(Evaluation.graduate_id).filter_by(round_id=link.round_id).all()
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
            section3_questions=section3_questions,
            section4_groups=section4_groups,
        )

    @app.post("/survey/<token>/submit")
    def survey_submit(token):
        link = EvaluationLink.query.filter_by(token=token, is_active=True).first_or_404()
        if not link.round.is_open:
            abort(410)
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
            abort(409, "ยังไม่ได้กำหนดชุดคำถามให้สาขานี้")
        question_rows = Question.query.filter_by(question_set_id=question_set.id).all()
        required_fields = [
            "respondent_gender", "respondent_age", "respondent_position", "employer_type",
            "work_duration", "job_alignment",
        ]
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
            graduate_id=graduate.id,
            question_set_id=question_set.id,
            respondent_gender=request.form.get("respondent_gender"),
            respondent_age=request.form.get("respondent_age"),
            respondent_position=request.form.get("respondent_position", "").strip(),
            employer_type=request.form.get("employer_type"),
            work_duration=request.form.get("work_duration"),
            job_alignment=request.form.get("job_alignment"),
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

    @app.get("/admin")
    @app.get("/admin/dashboard")
    @login_required
    def admin_dashboard():
        faculties = Faculty.query.order_by(Faculty.name).all()
        faculty_id = request.args.get("faculty", type=int)
        if faculty_id not in {f.id for f in faculties}:
            faculty_id = faculties[0].id if faculties else None
        departments = Department.query.filter_by(faculty_id=faculty_id).order_by(Department.name).all() if faculty_id else []
        department_id = request.args.get("department", type=int)
        if department_id not in {d.id for d in departments}:
            department_id = None
        round_row = EvaluationRound.query.order_by(EvaluationRound.id.desc()).first()
        grads_query = Graduate.query.join(Department).filter(Department.faculty_id == faculty_id) if faculty_id else Graduate.query
        if department_id:
            grads_query = grads_query.filter(Graduate.department_id == department_id)
        graduates = grads_query.order_by(Graduate.code).all()
        grad_ids = [g.id for g in graduates]
        evaluations = Evaluation.query.filter(
            Evaluation.graduate_id.in_(grad_ids), Evaluation.round_id == round_row.id
        ).all() if grad_ids and round_row else []
        submitted_ids = {e.graduate_id for e in evaluations}
        total = len(graduates)
        completed = len(submitted_ids)
        rate = round(completed / total * 100, 1) if total else 0
        scored3 = [a.score for e in evaluations for a in e.answers if a.section == 3 and a.score is not None]
        scored4 = [a.score for e in evaluations for a in e.answers if a.section == 4 and a.score is not None]
        average3 = round(sum(scored3) / len(scored3), 2) if scored3 else 0
        average4 = round(sum(scored4) / len(scored4), 2) if scored4 else 0
        dept_rows = []
        for dept in departments:
            dept_grads = [g for g in dept.graduates]
            dept_evals = [e for e in evaluations if e.graduate.department_id == dept.id]
            scores3 = [a.score for e in dept_evals for a in e.answers if a.section == 3 and a.score is not None]
            scores4 = [a.score for e in dept_evals for a in e.answers if a.section == 4 and a.score is not None]
            dept_rows.append({
                "id": dept.id, "name": dept.name, "graduates": len(dept_grads),
                "completed": len(dept_evals),
                "rate": round(len(dept_evals) / len(dept_grads) * 100, 1) if dept_grads else 0,
                "average3": round(sum(scores3) / len(scores3), 2) if scores3 else 0,
                "average4": round(sum(scores4) / len(scores4), 2) if scores4 else 0,
            })
        profile_counts = {}
        for e in evaluations:
            profile_counts[e.employer_type or "ไม่ระบุ"] = profile_counts.get(e.employer_type or "ไม่ระบุ", 0) + 1
        faculty_rows = []
        for faculty in faculties:
            faculty_grads = Graduate.query.join(Department).filter(Department.faculty_id == faculty.id).all()
            faculty_ids = [g.id for g in faculty_grads]
            faculty_evals = Evaluation.query.filter(
                Evaluation.graduate_id.in_(faculty_ids), Evaluation.round_id == round_row.id
            ).all() if faculty_ids and round_row else []
            faculty_scores3 = [a.score for e in faculty_evals for a in e.answers if a.section == 3 and a.score is not None]
            faculty_scores4 = [a.score for e in faculty_evals for a in e.answers if a.section == 4 and a.score is not None]
            faculty_rows.append({
                "name": faculty.name, "graduates": len(faculty_grads), "completed": len(faculty_evals),
                "rate": round(len(faculty_evals) / len(faculty_grads) * 100, 1) if faculty_grads else 0,
                "average3": round(sum(faculty_scores3) / len(faculty_scores3), 2) if faculty_scores3 else 0,
                "average4": round(sum(faculty_scores4) / len(faculty_scores4), 2) if faculty_scores4 else 0,
            })
        selected_department = db.session.get(Department, department_id) if department_id else None
        # Join Department even when no faculty is selected because the query
        # is always ordered by Department.name below.
        links_query = EvaluationLink.query.join(Department).filter(
            EvaluationLink.is_active.is_(True)
        )
        if faculty_id:
            links_query = links_query.filter(Department.faculty_id == faculty_id)
        if department_id:
            links_query = links_query.filter(EvaluationLink.department_id == department_id)
        survey_links = links_query.order_by(Department.name, EvaluationLink.employer_id).all()
        return render_template(
            "admin_dashboard.html",
            faculties=faculties, departments=departments, faculty_id=faculty_id,
            department_id=department_id, selected_department=selected_department,
            total=total, completed=completed, pending=max(total-completed, 0),
            rate=rate, average3=average3, average4=average4, evaluations=evaluations,
            graduates=graduates, submitted_ids=submitted_ids, dept_rows=dept_rows,
            survey_links=survey_links,
            profile_counts=profile_counts, faculty_rows=faculty_rows, round_row=round_row,
            report_mode=request.args.get("view") == "report",
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


@app.cli.command("create-admin")
def create_admin_command():
    """Create an administrator account after the MySQL schema has been migrated."""
    username = input("Username: ").strip()
    if not username:
        raise SystemExit("Username is required.")
    if Admin.query.filter_by(username=username).first():
        raise SystemExit("That username already exists.")
    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    admin = Admin(username=username)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print("Administrator account created.")
