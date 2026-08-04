from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from database import get_db
from decorators import login_required


jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/jobs")
def jobs():

    rows = get_db().execute(
        """
        SELECT jobs.*,
        users.name AS employer_name

        FROM jobs

        JOIN users
        ON users.id = jobs.created_by

        ORDER BY jobs.id DESC

        """
    ).fetchall()


    return render_template(
        "jobs/jobs.html",
        jobs=rows
    )



@jobs_bp.route(
    "/jobs/create",
    methods=["GET", "POST"]
)
@login_required
def create_job():

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        description = request.form.get(
            "description",
            ""
        ).strip()


        budget = request.form.get(
            "budget",
            ""
        ).strip()



        if not title or not description or not budget:

            flash(
                "All fields required.",
                "warning"
            )

            return redirect(
                url_for("jobs.create_job")
            )


        db = get_db()


        db.execute(
            """
            INSERT INTO jobs
            (
                title,
                description,
                budget,
                created_by
            )

            VALUES (?,?,?,?)

            """,
            (
                title,
                description,
                budget,
                session["user_id"]
            )
        )


        db.commit()


        flash(
            "Job posted.",
            "success"
        )


        return redirect(
            url_for("jobs.jobs")
        )


    return render_template(
        "jobs/post_job.html"
    )
@jobs_bp.route("/jobs/<int:job_id>/applicants")
@login_required
def applicants(job_id):

    db = get_db()

    job = db.execute(
        """
        SELECT jobs.*, users.name AS employer_name
        FROM jobs
        JOIN users ON users.id = jobs.created_by
        WHERE jobs.id = ?
        """,
        (job_id,)
    ).fetchone()


    if not job:
        flash(
            "Job not found.",
            "danger"
        )
        return redirect(
            url_for("jobs.jobs")
        )


    if job["created_by"] != session["user_id"]:

        flash(
            "Only the employer can view applicants.",
            "danger"
        )

        return redirect(
            url_for("jobs.jobs")
        )


    rows = db.execute(
        """
        SELECT applications.*, users.name, users.email

        FROM applications

        JOIN users
        ON users.id = applications.applicant

        WHERE applications.job_id = ?

        ORDER BY applications.id DESC

        """,
        (job_id,)
    ).fetchall()


    return render_template(
        "jobs/applicants.html",
        job=job,
        applicants=rows
    )