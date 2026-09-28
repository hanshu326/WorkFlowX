from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from datetime import date
from sqlalchemy import func

from app import db
from app.models import User, Project, Task, Notification, TaskUpdate
from werkzeug.security import generate_password_hash


main = Blueprint("main", __name__)
# =========================================================
# GLOBAL UNREAD NOTIFICATION COUNT
# =========================================================

@main.app_context_processor
def inject_unread_count():

    unread_count = 0

    if session.get("user_id"):

        unread_count = Notification.query.filter_by(
            user_id=session["user_id"],
            is_read=False
        ).count()

    return {
        "unread_count": unread_count
    }
 
# =========================================================
# DASHBOARD
# =========================================================
@main.route("/")
@main.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()
    user_id = session.get("user_id")
    name = session.get("user_name", "User")

    # Default value
    overall_progress = 0

    # ================= ADMIN / MANAGER =================

    if role in ["admin", "manager"]:

        total_projects = Project.query.count()

        active_projects = Project.query.filter_by(
            status="ACTIVE"
        ).count()

        total_employees = User.query.filter(
            User.role == "employee"
        ).count()

        total_tasks = Task.query.count()

        completed_tasks = Task.query.filter_by(
            status="COMPLETED"
        ).count()

        # Overall task progress
        if total_tasks > 0:
            overall_progress = round(
                (completed_tasks / total_tasks) * 100
            )

        pending_tasks = Task.query.filter(
            Task.status != "COMPLETED"
        ).count()

        upcoming_tasks = Task.query.filter(
            Task.status != "COMPLETED",
            Task.deadline >= date.today()
        ).order_by(
            Task.deadline.asc()
        ).limit(5).all()

        overdue_tasks = Task.query.filter(
            Task.deadline < date.today(),
            Task.status != "COMPLETED"
        ).count()

        recent_tasks = Task.query.order_by(
            Task.id.desc()
        ).limit(5).all()

    # ================= EMPLOYEE =================

    else:

        total_projects = Project.query.count()

        total_employees = User.query.filter(
            User.role == "employee"
        ).count()

        active_projects = Project.query.filter_by(
            status="ACTIVE"
        ).count()

        total_tasks = Task.query.filter_by(
            assigned_to=user_id
        ).count()

        completed_tasks = Task.query.filter_by(
            assigned_to=user_id,
            status="COMPLETED"
        ).count()

        # Employee's own task progress
        if total_tasks > 0:
            overall_progress = round(
                (completed_tasks / total_tasks) * 100
            )

        pending_tasks = Task.query.filter(
            Task.assigned_to == user_id,
            Task.status != "COMPLETED"
        ).count()

        overdue_tasks = Task.query.filter(
            Task.assigned_to == user_id,
            Task.deadline < date.today(),
            Task.status != "COMPLETED"
        ).count()

        recent_tasks = Task.query.filter_by(
            assigned_to=user_id
        ).order_by(
            Task.id.desc()
        ).limit(5).all()

        upcoming_tasks = Task.query.filter(
            Task.assigned_to == user_id,
            Task.status != "COMPLETED",
            Task.deadline >= date.today()
        ).order_by(
            Task.deadline.asc()
        ).limit(5).all()

    # ================= DASHBOARD =================

    return render_template(
        "dashboard.html",
        name=name,
        role=role,
        total_projects=total_projects,
        active_projects=active_projects,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        overall_progress=overall_progress,
        pending_tasks=pending_tasks,
        overdue_tasks=overdue_tasks,
        recent_tasks=recent_tasks,
        upcoming_tasks=upcoming_tasks,
        total_employees=total_employees
    )
     
# =========================================================
# PROJECTS
# =========================================================

@main.route("/projects")
def projects():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()
    user_id = session.get("user_id")

    if role not in ["admin", "manager", "employee"]:
        flash("Invalid user role.")
        return redirect(url_for("auth.login"))

    # ================= ADMIN / MANAGER =================

    if role in ["admin", "manager"]:

        projects = Project.query.order_by(
            Project.id.desc()
        ).all()

    # ================= EMPLOYEE =================

    else:

        # Show only projects where this employee
        # has at least one assigned task
        projects = Project.query.join(
            Task,
            Project.id == Task.project_id
        ).filter(
            Task.assigned_to == user_id
        ).distinct().order_by(
            Project.id.desc()
        ).all()

    # ================= PROJECT PROGRESS =================

    project_progress = {}

    for project in projects:

        if role in ["admin", "manager"]:

            project_tasks = Task.query.filter_by(
                project_id=project.id
            ).all()

        else:

            project_tasks = Task.query.filter_by(
                project_id=project.id,
                assigned_to=user_id
            ).all()

        total = len(project_tasks)

        completed = sum(
            1
            for task in project_tasks
            if task.status == "COMPLETED"
        )

        if total > 0:
            progress = round(
                (completed / total) * 100
            )
        else:
            progress = 0

        project_progress[project.id] = progress

    return render_template(
        "projects.html",
        projects=projects,
        project_progress=project_progress
    )
# =========================================================
# SEARCH PROJECTS
# =========================================================

@main.route("/projects/search")
def search_projects():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    query = request.args.get(
        "search",
        ""
    ).strip()

    if query:

        projects = Project.query.filter(
            Project.name.ilike(
                f"%{query}%"
            )
        ).order_by(
            Project.id.desc()
        ).all()

    else:

        projects = Project.query.order_by(
            Project.id.desc()
        ).all()

    return render_template(
        "projects.html",
        projects=projects,
        search_query=query
    )


# =========================================================
# CREATE PROJECT
# =========================================================

@main.route(
    "/projects/create",
    methods=["GET", "POST"]
)
@main.route("/create-project", methods=["GET", "POST"])
def create_project():

    print(">>> CREATE PROJECT ROUTE REACHED <<<")

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager"]:
        flash("You do not have permission to create projects.")
        return redirect(url_for("main.dashboard"))
     

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        description = request.form.get("description", "").strip()

        start_date = request.form.get("start_date")
        deadline = request.form.get("deadline")

        status = request.form.get(
            "status",
            "PLANNED"
        )

        # Convert dates safely
        if start_date and isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)

        if deadline and isinstance(deadline, str):
            deadline = date.fromisoformat(deadline)

        # Validate project name
        if not name:

            flash("Project name is required.")

            return render_template(
                "create_project.html"
            )

        # Create project
        project = Project(
            name=name,
            description=description,
            start_date=start_date,
            deadline=deadline,
            status=status,
            created_by=session["user_id"]
        )

        db.session.add(project)
        db.session.commit()

        flash("Project created successfully!")

        return redirect(
            url_for("main.projects")
        )

    return render_template(
        "create_project.html"
    )


# =========================================================
# EDIT PROJECT
# =========================================================

@main.route(
    "/projects/edit/<int:project_id>",
    methods=["GET", "POST"]
)
def edit_project(project_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager"]:
        flash("You do not have permission to edit projects.")
        return redirect(url_for("main.dashboard"))

    project = Project.query.get_or_404(project_id)

    if request.method == "POST":

        project.name = request.form.get(
            "name",
            ""
        ).strip()

        project.description = request.form.get(
            "description",
            ""
        ).strip()

        start_date = request.form.get(
            "start_date"
        )

        deadline = request.form.get(
            "deadline"
        )

        if start_date:
            project.start_date = date.fromisoformat(
                start_date
            )
        else:
            project.start_date = None

        if deadline:
            project.deadline = date.fromisoformat(
                deadline
            )
        else:
            project.deadline = None

        project.status = request.form.get(
            "status",
            "PLANNED"
        )

        db.session.commit()

        flash(
            "Project updated successfully!"
        )

        return redirect(
            url_for("main.projects")
        )

    return render_template(
        "edit_project.html",
        project=project
    )
 # =========================================================
# PROJECT DETAILS
# =========================================================

@main.route("/projects/<int:project_id>")
def project_details(project_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager", "employee"]:
        flash("Invalid user role.")
        return redirect(url_for("auth.login"))

    project = Project.query.get_or_404(project_id)

    # Admin and Manager can see all tasks
    if role in ["admin", "manager"]:

        tasks = Task.query.filter_by(
            project_id=project.id
        ).order_by(
            Task.id.desc()
        ).all()

    # Employee can see only their assigned tasks
    else:

        tasks = Task.query.filter_by(
            project_id=project.id,
            assigned_to=session["user_id"]
        ).order_by(
            Task.id.desc()
        ).all()

    # Calculate project progress
    total_tasks = len(tasks)

    completed_tasks = sum(
        1 for task in tasks
        if task.status == "COMPLETED"
    )

    if total_tasks > 0:
        project_progress = round(
            (completed_tasks / total_tasks) * 100
        )
    else:
        project_progress = 0

    return render_template(
        "project_details.html",
        project=project,
        tasks=tasks,
        project_progress=project_progress
    )

 
# =========================================================
# DELETE PROJECT
# =========================================================

@main.route("/projects/delete/<int:project_id>", methods=["POST"])
def delete_project(project_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager"]:
        flash("You do not have permission to delete projects.")
        return redirect(url_for("main.dashboard"))

    project = Project.query.get_or_404(project_id)

    Task.query.filter_by(
        project_id=project.id
    ).delete(
        synchronize_session=False
    )

    db.session.delete(project)
    db.session.commit()

    flash("Project and its tasks deleted successfully!")

    return redirect(
        url_for("main.projects")
    )
 
@main.route("/tasks/search")
def search_tasks():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager", "employee"]:
        flash("Invalid user role.")
        return redirect(url_for("auth.login"))

    query = request.args.get(
        "search",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()

    priority = request.args.get(
        "priority",
        ""
    ).strip()

    # Admin and Manager can search all tasks
    if role in ["admin", "manager"]:
        tasks_query = Task.query

    # Employee can search only their assigned tasks
    else:
        tasks_query = Task.query.filter_by(
            assigned_to=session["user_id"]
        )

    # Search by task title
    if query:
        tasks_query = tasks_query.filter(
            Task.title.ilike(
                f"%{query}%"
            )
        )

    # Filter by status
    if status:
        tasks_query = tasks_query.filter(
            Task.status == status
        )

    # Filter by priority
    if priority:
        tasks_query = tasks_query.filter(
            Task.priority == priority
        )

    tasks = tasks_query.order_by(
        Task.id.desc()
    ).all()

    return render_template(
        "tasks.html",
        tasks=tasks,
        search=query,
        status=status,
        priority=priority
    )

      
# =========================================================
# TASKS
# =========================================================

@main.route("/tasks")
def tasks():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).lower()
    user_id = session.get("user_id")

    # ADMIN / MANAGER → See all tasks
    if role in ["admin", "manager"]:
        tasks = Task.query.order_by(Task.id.desc()).all()

    elif role == "employee":
        tasks = Task.query.filter_by(
            assigned_to=session["user_id"]
    ).order_by(Task.id.desc()).all()

    else:
        flash("Invalid user role.")
        return redirect(url_for("auth.login"))

    return render_template(
        "tasks.html",
        tasks=tasks
    )
@main.route("/task/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
 
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    task = Task.query.get_or_404(task_id)

    role = str(session.get("role", "")).strip().lower()
    user_id = session.get("user_id")

    # Admin and Manager can update any task
    if role in ["admin", "manager"]:
        pass

    # Employee can update only their assigned task
    elif task.assigned_to == user_id:
        pass

    else:
        flash("You do not have permission to update this task.")
        return redirect(url_for("main.my_tasks"))

    new_status = request.form.get("status")

    allowed_statuses = [
        "TODO",
        "IN PROGRESS",
        "REVIEW",
        "COMPLETED"
    ]

    if new_status not in allowed_statuses:
        flash("Invalid task status.")
        return redirect(url_for("main.my_tasks"))

    # Update task status
    task.status = new_status

    # Create notifications for Admins and Managers
    recipients = User.query.filter(
        User.role.in_(["admin", "manager"])
    ).all()

    for recipient in recipients:

        # Don't notify the person who changed the status
        if recipient.id == user_id:
            continue

        notification = Notification(
            message=f"Task '{task.title}' status changed to {new_status}.",
            user_id=recipient.id,
            is_read=False
        )

        db.session.add(notification)

    db.session.commit()

    print("STATUS NOTIFICATIONS CREATED")

    flash("Task status updated successfully.")

    return redirect(url_for("main.my_tasks"))


# =========================================================
# UPDATE TASK PROGRESS
# =========================================================

@main.route("/task/<int:task_id>/progress", methods=["POST"])
def update_task_progress(task_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    task = Task.query.get_or_404(task_id)

    role = str(session.get("role", "")).strip().lower()
    user_id = session.get("user_id")

    # Admin and Manager can update any task
    if role in ["admin", "manager"]:
        pass

    # Employee can update only their assigned task
    elif task.assigned_to == user_id:
        pass

    else:
        flash("You do not have permission to update this task.")
        return redirect(url_for("main.my_tasks"))

    # Get progress from form
    progress_value = request.form.get("progress", "").strip()

    try:
        progress = int(progress_value)
    except (ValueError, TypeError):
        flash("Invalid progress value.")
        return redirect(url_for("main.my_tasks"))

    # Progress must be between 0 and 100
    if progress < 0 or progress > 100:
        flash("Progress must be between 0 and 100.")
        return redirect(url_for("main.my_tasks"))

    # Update progress
    task.progress = progress

    # Automatically update status based on progress
    if progress == 0:
        task.status = "TODO"

    elif progress < 100:
        task.status = "IN PROGRESS"

    elif progress == 100:
        task.status = "COMPLETED"

    # Notify Admins and Managers
    recipients = User.query.filter(
        User.role.in_(["admin", "manager"])
    ).all()

    for recipient in recipients:

        # Don't notify the person who changed progress
        if recipient.id == user_id:
            continue

        notification = Notification(
            message=f"Task '{task.title}' progress updated to {progress}%.",
            user_id=recipient.id,
            is_read=False
        )

        db.session.add(notification)

    db.session.commit()

    flash("Task progress updated successfully.")

    return redirect(url_for("main.my_tasks"))
# =========================================================
# CREATE TASK
# =========================================================
@main.route("/tasks/create", methods=["GET", "POST"])
def create_task():

    # Login check
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    # Only Admin and Manager can create tasks
    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager"]:
        flash("You do not have permission to create tasks.")
        return redirect(url_for("main.tasks"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        project_id = request.form.get("project_id")
        assigned_to = request.form.get("assigned_to")

        priority = request.form.get("priority", "MEDIUM")
        status = request.form.get("status", "TODO")

        deadline = request.form.get("deadline")

        # Validation
        if not title or not project_id or not assigned_to or not deadline:
            flash("Please fill all required fields.")
            projects = Project.query.all()
            employees = User.query.filter(
                User.role == "employee"
                ).order_by(
                    User.name.asc()
                ).all()
            return render_template(
                "create_task.html",
                projects=projects,
                users=employees
            )

        # Convert values
        project_id = int(project_id)
        assigned_to = int(assigned_to)
        deadline = date.fromisoformat(deadline)

        task = Task(
            title=title,
            description=description,
            priority=priority,
            status=status,
            deadline=deadline,
            project_id=project_id,
            assigned_to=assigned_to
        )

        db.session.add(task)
        db.session.commit()
        notification = Notification(
            message=f"New task assigned to you: {task.title}",
            user_id=assigned_to,
            is_read=False
        )

        db.session.add(notification)
        db.session.commit()
 
        print("NOTIFICATION CREATED:", notification.id, notification.message)
         

        flash("Task created successfully!")

        return redirect(url_for("main.tasks"))

    projects = Project.query.all()
    employees = User.query.filter(
        User.role == "employee"
    ).order_by(User.name.asc()).all()
    return render_template(
        "create_task.html",
        projects=projects,
        users=employees
    )

# =========================================================
# NOTIFICATIONS
# =========================================================

@main.route("/notifications/mark-all-read", methods=["POST"])
def mark_all_notifications_read():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    notifications = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).all()

    for notification in notifications:
        notification.is_read = True

    db.session.commit()

    flash("All notifications marked as read.")

    return redirect(url_for("main.notifications"))
 
 
# =========================================================
# EDIT TASK
# =========================================================

@main.route(
    "/tasks/edit/<int:task_id>",
    methods=["GET", "POST"]
)
def edit_task(task_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if str(session.get("role", "")).lower() not in ["admin", "manager"]:

        flash(
            "You do not have permission to edit tasks."
        )

        return redirect(
            url_for("main.tasks")
        )

    task = Task.query.get_or_404(
        task_id
    )

    projects = Project.query.order_by(
        Project.name.asc()
    ).all()

    employees = User.query.filter(
        User.role == "employee"
    ).order_by(
        User.name.asc()
    ).all()

    if request.method == "POST":

        task.title = request.form.get(
            "title",
            ""
        ).strip()

        task.description = request.form.get(
            "description",
            ""
        ).strip()

        project_id = request.form.get(
            "project_id"
        )

        assigned_to = request.form.get(
            "assigned_to"
        )

        task.priority = request.form.get(
            "priority"
        )

        task.status = request.form.get(
            "status"
        )

        deadline = request.form.get(
            "deadline"
        )

        # Convert deadline correctly
        if deadline:
            task.deadline = date.fromisoformat(
                deadline
            )
        else:
            task.deadline = None

        if project_id:

            task.project_id = int(
                project_id
            )

        if assigned_to:

            task.assigned_to = int(
                assigned_to
            )

        db.session.commit()

        flash(
            "Task updated successfully!"
        )

        return redirect(
            url_for("main.tasks")
        )

    return render_template(
        "edit_task.html",
        task=task,
        projects=projects,
        employees=employees
    )


# =========================================================
# DELETE TASK
# =========================================================

@main.route(
    "/tasks/delete/<int:task_id>",
    methods=["POST"]
)
def delete_task(task_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if str(session.get("role", "")).lower() not in ["admin", "manager"]:

        flash(
            "You do not have permission to delete tasks."
        )

        return redirect(
            url_for("main.tasks")
        )

    task = Task.query.get_or_404(
        task_id
    )

    db.session.delete(task)

    db.session.commit()

    flash(
        "Task deleted successfully!"
    )

    return redirect(
        url_for("main.tasks")
    )


# =========================================================
# MY TASKS
# =========================================================

@main.route("/my-tasks")
def my_tasks():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()
    user_id = session.get("user_id")

    if role not in ["admin", "manager", "employee"]:
        flash("Invalid user role.")
        return redirect(url_for("auth.login"))

    my_tasks = Task.query.filter_by(
        assigned_to=user_id
    ).order_by(
        Task.id.desc()
    ).all()

    # Each task's previous work updates
    task_updates = {}

    for task in my_tasks:
        task_updates[task.id] = TaskUpdate.query.filter_by(
            task_id=task.id
        ).order_by(
            TaskUpdate.id.desc()
        ).all()

    return render_template(
        "my_tasks.html",
        tasks=my_tasks,
        task_updates=task_updates
    )
# =========================================================
# TASK DETAILS
# =========================================================

@main.route("/tasks/<int:task_id>/details")
def task_details(task_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    role = str(session.get("role", "")).strip().lower()

    task = Task.query.get_or_404(task_id)

    # Employee can view only their assigned tasks
    if role == "employee" and task.assigned_to != user_id:
        flash("You can view only your assigned tasks.")
        return redirect(url_for("main.my_tasks"))

    updates = TaskUpdate.query.filter_by(
        task_id=task.id
    ).order_by(
        TaskUpdate.id.desc()
    ).all()

    update_users = {}

    for update in updates:
        update_users[update.id] = User.query.get(update.user_id)

    return render_template(
        "task_details.html",
        task=task,
        updates=updates,
        update_users=update_users
    )
 
# =========================================================
# ADD TASK WORK UPDATE + NOTIFICATION
# =========================================================

@main.route("/tasks/<int:task_id>/update", methods=["POST"])
def add_task_update(task_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager", "employee"]:
        flash("Invalid user role.")
        return redirect(url_for("auth.login"))

    task = Task.query.get_or_404(task_id)

    # Employee can update only their own task
    if role == "employee" and task.assigned_to != user_id:
        flash("You do not have permission to update this task.")
        return redirect(url_for("main.my_tasks"))

    message = request.form.get("message", "").strip()

    if not message:
        flash("Work update cannot be empty.")
        return redirect(url_for("main.my_tasks"))

    # Create work update
    update = TaskUpdate(
        message=message,
        task_id=task.id,
        user_id=user_id
    )

    db.session.add(update)

    # Notify Admin and Manager when employee adds update
    if role == "employee":

        users_to_notify = User.query.filter(
            User.role.in_(["admin", "manager"])
        ).all()

        employee = User.query.get(user_id)

        employee_name = (
            employee.name
            if employee
            else "Employee"
        )

        notification_message = (
            f"{employee_name} added a work update to task "
            f"'{task.title}'."
        )

        for user in users_to_notify:

            notification = Notification(
                message=notification_message,
                user_id=user.id,
                is_read=False
            )

            db.session.add(notification)

    db.session.commit()

    flash("Work update added successfully.")

    return redirect(url_for("main.my_tasks"))
     
    # -----------------------------------------------------
    # CREATE NOTIFICATIONS
    # -----------------------------------------------------

     
 
@main.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user = User.query.get_or_404(session["user_id"])

    assigned_tasks = Task.query.filter_by(
        assigned_to=user.id
    ).all()

    total_tasks = len(assigned_tasks)

    completed_tasks = sum(
        1 for task in assigned_tasks
        if task.status == "COMPLETED"
    )

    pending_tasks = total_tasks - completed_tasks

    return render_template(
        "profile.html",
        user=user,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks
    )


# =========================================================
# UPDATE TASK STATUS
# =========================================================
@main.route("/employees")
def employees():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role != "admin":
        flash("You do not have permission to view employees.")
        return redirect(url_for("main.dashboard"))

    employees = User.query.filter(
        User.role == "employee"
    ).order_by(
        User.name.asc()
    ).all()

    return render_template(
        "employees.html",
        employees=employees
    )

 
@main.route("/employees/create", methods=["GET", "POST"])
def create_employee():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role != "admin":
        flash("You do not have permission to create employees.")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Employees created from this page
        # must always have employee role.
        employee_role = "employee"

        if not name or not email or not password:
            flash("Name, email and password are required.")
            return render_template(
                "create_employee.html"
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash("An account with this email already exists.")
            return render_template(
                "create_employee.html"
            )

        employee = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=employee_role
        )

        db.session.add(employee)
        db.session.commit()

        flash("Employee created successfully!")

        return redirect(
            url_for("main.employees")
        )

    return render_template(
        "create_employee.html"
    )


@main.route(
    "/employees/edit/<int:user_id>",
    methods=["GET", "POST"]
)
def edit_employee(user_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role != "admin":
        flash("You do not have permission to edit employees.")
        return redirect(url_for("main.dashboard"))

    employee = User.query.get_or_404(user_id)

    # Only employee accounts should be edited from this page
    if str(employee.role).strip().lower() != "employee":
        flash("Only employee accounts can be edited here.")
        return redirect(url_for("main.employees"))

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not name or not email:
            flash("Name and email are required.")
            return render_template(
                "edit_employee.html",
                employee=employee
            )

        # Check whether another user already has this email
        existing_user = User.query.filter(
            User.email == email,
            User.id != employee.id
        ).first()

        if existing_user:
            flash("An account with this email already exists.")
            return render_template(
                "edit_employee.html",
                employee=employee
            )

        employee.name = name
        employee.email = email

        # Keep this account as an employee
        employee.role = "employee"

        db.session.commit()

        flash("Employee updated successfully!")

        return redirect(
            url_for("main.employees")
        )

    return render_template(
        "edit_employee.html",
        employee=employee
    )


@main.route(
    "/employees/delete/<int:user_id>",
    methods=["POST"]
)
def delete_employee(user_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role != "admin":
        flash("You do not have permission to delete employees.")
        return redirect(url_for("main.dashboard"))

    # Prevent Admin from deleting their own account
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.")
        return redirect(
            url_for("main.employees")
        )

    employee = User.query.get_or_404(user_id)

    # Only employee accounts can be deleted from this page
    if str(employee.role).strip().lower() != "employee":
        flash("Only employee accounts can be deleted here.")
        return redirect(
            url_for("main.employees")
        )

    # Check whether the employee has assigned tasks
    assigned_tasks = Task.query.filter_by(
        assigned_to=employee.id
    ).all()

    if assigned_tasks:
        flash(
            "This employee has assigned tasks. "
            "Reassign or complete the tasks before deleting the employee."
        )
        return redirect(
            url_for("main.employees")
        )

    db.session.delete(employee)
    db.session.commit()

    flash("Employee deleted successfully!")

    return redirect(
        url_for("main.employees")
    )


# =========================================================
# TEAM
# =========================================================

@main.route("/team")
def team():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    if role not in ["admin", "manager"]:
        flash(
            "You do not have permission to view the team."
        )
        return redirect(
            url_for("main.dashboard")
        )

    employees = User.query.filter(
        User.role == "employee"
    ).order_by(
        User.name.asc()
    ).all()

    return render_template(
        "team.html",
        employees=employees
    )

 
# =========================================================
# NOTIFICATIONS
# =========================================================
@main.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    notifications = Notification.query.filter_by(
        user_id=user_id
    ).order_by(
        Notification.id.desc()
    ).all()

    unread_count = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).count()

    return render_template(
        "notifications.html",
        notifications=notifications,
        unread_count=unread_count
    )
@main.route("/notifications/read/<int:notification_id>", methods=["POST"])
def mark_notification_read(notification_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != session["user_id"]:
        flash("You do not have permission.")
        return redirect(url_for("main.notifications"))

    notification.is_read = True
    db.session.commit()

    return redirect(url_for("main.notifications"))


 
# ANALYTICS DASHBOARD
# =========================================================

@main.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    role = str(session.get("role", "")).strip().lower()

    # Only Admin and Manager
    if role not in ["admin", "manager"]:
        flash("You do not have permission to view analytics.")
        return redirect(url_for("main.dashboard"))

    # ================= TASK STATUS =================

    todo_tasks = Task.query.filter_by(
        status="TODO"
    ).count()

    in_progress_tasks = Task.query.filter_by(
        status="IN PROGRESS"
    ).count()

    review_tasks = Task.query.filter_by(
        status="REVIEW"
    ).count()

    completed_tasks = Task.query.filter_by(
        status="COMPLETED"
    ).count()

    # ================= TASK TOTAL =================

    total_tasks = Task.query.count()

    # ================= OVERALL COMPLETION =================

    if total_tasks > 0:
        completion_percentage = round(
            (completed_tasks / total_tasks) * 100
        )
    else:
        completion_percentage = 0

    # ================= OVERDUE TASKS =================

    overdue_tasks = Task.query.filter(
        Task.deadline < date.today(),
        Task.status != "COMPLETED"
    ).count()

    # ================= PROJECTS =================

    total_projects = Project.query.count()

    active_projects = Project.query.filter_by(
        status="ACTIVE"
    ).count()

    # ================= EMPLOYEE WORKLOAD =================

    employees = User.query.filter(
        User.role == "employee"
    ).order_by(
        User.name.asc()
    ).all()

    employee_workload = []

    for employee in employees:

        task_count = Task.query.filter_by(
            assigned_to=employee.id
        ).count()

        completed_count = Task.query.filter_by(
            assigned_to=employee.id,
            status="COMPLETED"
        ).count()

        employee_workload.append({
            "name": employee.name,
            "total": task_count,
            "completed": completed_count
        })

    return render_template(
        "analytics.html",
        todo_tasks=todo_tasks,
        in_progress_tasks=in_progress_tasks,
        review_tasks=review_tasks,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        completion_percentage=completion_percentage,
        overdue_tasks=overdue_tasks,
        total_projects=total_projects,
        active_projects=active_projects,
        employee_workload=employee_workload
    )
