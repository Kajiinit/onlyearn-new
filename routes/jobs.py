from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from database import get_db
from decorators import login_required


jobs_bp = Blueprint("jobs", __name__)


# ---------------------------------------------------
# JOB LIST
# ---------------------------------------------------

@jobs_bp.route("/jobs")
def jobs():

    search = request.args.get("search", "").strip()

    db = get_db()

    if search:

        rows = db.execute(
            """
            SELECT jobs.*,
                   users.name AS employer_name

            FROM jobs

            JOIN users
            ON users.id = jobs.created_by

            WHERE
                jobs.title LIKE ?
                OR jobs.description LIKE ?
                OR users.name LIKE ?

            ORDER BY jobs.id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        ).fetchall()

    else:

        rows = db.execute(
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
        jobs=rows,
        search=search
    )


# ---------------------------------------------------
# CREATE JOB
# ---------------------------------------------------

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
                "All fields are required.",
                "warning"
            )

            return redirect(
                url_for("jobs.create_job")
            )

        now = datetime.now().isoformat()

        db = get_db()

        db.execute(
            """
            INSERT INTO jobs
            (
                title,
                description,
                budget,
                created_by,
                created_at,
                updated_at
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                budget,
                session["user_id"],
                now,
                now,
            )
        )

        db.commit()

        flash(
            "Job posted successfully.",
            "success"
        )

        return redirect(
            url_for("jobs.jobs")
        )

    return render_template(
        "jobs/post_job.html"
    )

# ---------------------------------------------------
# APPLY TO JOB
# ---------------------------------------------------

@jobs_bp.route(
    "/jobs/<int:job_id>/apply",
    methods=["POST"]
)
@login_required
def apply_to_job(job_id):

    db = get_db()

    # Find the job
    job = db.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
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

    # Prevent the employer from applying to their own job
    if job["created_by"] == session["user_id"]:

        flash(
            "You cannot apply to your own job.",
            "warning"
        )

        return redirect(
            url_for("jobs.jobs")
        )

    # Check if the user already applied
    existing = db.execute(
        """
        SELECT id
        FROM applications
        WHERE job_id = ?
        AND applicant = ?
        """,
        (
            job_id,
            session["user_id"]
        )
    ).fetchone()

    if existing:

        flash(
            "You have already applied for this job.",
            "warning"
        )

        return redirect(
            url_for("jobs.jobs")
        )

    # Create application
    db.execute(
        """
        INSERT INTO applications
        (
            job_id,
            applicant,
            status
        )
        VALUES (?, ?, ?)
        """,
        (
            job_id,
            session["user_id"],
            "Applied"
        )
    )

    db.commit()

    flash(
        "Application submitted successfully.",
        "success"
    )

    return redirect(
        url_for("jobs.jobs")
    )

# ---------------------------------------------------
# VIEW APPLICANTS
# ---------------------------------------------------

@jobs_bp.route("/jobs/<int:job_id>/applicants")
@login_required
def applicants(job_id):

    db = get_db()

    job = db.execute(
        """
        SELECT jobs.*,
               users.name AS employer_name

        FROM jobs

        JOIN users
        ON users.id = jobs.created_by

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

    applicants = db.execute(
        """
        SELECT applications.*,
               users.name,
               users.email

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
        applicants=applicants
    )

# ---------------------------------------------------
# EDIT JOB
# ---------------------------------------------------

@jobs_bp.route(
    "/jobs/<int:job_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_job(job_id):

    db = get_db()

    job = db.execute(
        """
        SELECT jobs.*,
               users.name AS employer_name
        FROM jobs
        JOIN users
        ON users.id = jobs.created_by
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
            "You can only edit your own job postings.",
            "danger"
        )

        return redirect(
            url_for("jobs.jobs")
        )

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
                "All fields are required.",
                "warning"
            )

            return redirect(
                url_for(
                    "jobs.edit_job",
                    job_id=job_id
                )
            )

        now = datetime.now().isoformat()

        db.execute(
            """
            UPDATE jobs

            SET
                title = ?,
                description = ?,
                budget = ?,
                updated_at = ?

            WHERE id = ?
            """,
            (
                title,
                description,
                budget,
                now,
                job_id
            )
        )

        db.commit()

        flash(
            "Job posting updated successfully.",
            "success"
        )

        return redirect(
            url_for("jobs.jobs")
        )

    return render_template(
        "jobs/edit_job.html",
        job=job
    )

# ---------------------------------------------------
# DELETE JOB
# ---------------------------------------------------

# ---------------------------------------------------
# DELETE JOB
# ---------------------------------------------------

@jobs_bp.route(
    "/jobs/<int:job_id>/delete",
    methods=["POST"]
)
@login_required
def delete_job(job_id):

    db = get_db()

    # Find the job
    job = db.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
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

    # Only the employer who created the job
    # can delete it.
    if job["created_by"] != session["user_id"]:

        flash(
            "You can only delete your own job postings.",
            "danger"
        )

        return redirect(
            url_for("jobs.jobs")
        )

    try:

        # -------------------------------------------
        # Delete applications belonging to this job
        # -------------------------------------------

        db.execute(
            """
            DELETE FROM applications
            WHERE job_id = ?
            """,
            (job_id,)
        )

        # -------------------------------------------
        # Delete the job itself
        # -------------------------------------------

        db.execute(
            """
            DELETE FROM jobs
            WHERE id = ?
            """,
            (job_id,)
        )

        db.commit()

        flash(
            "Job posting deleted successfully.",
            "success"
        )

    except Exception:

        db.rollback()

        flash(
            "Unable to delete this job posting.",
            "danger"
        )

    return redirect(
        url_for("jobs.jobs")
    )