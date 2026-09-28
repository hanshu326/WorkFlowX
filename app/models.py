from app import db
# =========================================================
# USER
# =========================================================

class User(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="employee"
    )

    # Employee assigned tasks
    tasks = db.relationship(
        "Task",
        backref="employee",
        lazy=True,
        foreign_keys="Task.assigned_to"
    )


# =========================================================
# PROJECT
# =========================================================

class Project(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    deadline = db.Column(
        db.Date,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="PLANNED"
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    tasks = db.relationship(
        "Task",
        backref="project",
        lazy=True
    )


# =========================================================
# TASK
# =========================================================

class Task(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    priority = db.Column(
        db.String(20),
        default="MEDIUM"
    )

    status = db.Column(
        db.String(30),
        default="TODO"
    )

    deadline = db.Column(
        db.Date,
        nullable=False
    )

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("project.id"),
        nullable=False
    )

    assigned_to = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    progress = db.Column(
        db.Integer,
        default=0
    )


# =========================================================
# NOTIFICATION
# =========================================================

class Notification(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    message = db.Column(
        db.String(255),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    
    
# =========================================================
# TASK UPDATE
# =========================================================
class TaskUpdate(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    task_id = db.Column(
        db.Integer,
        db.ForeignKey("task.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.now()
    )



