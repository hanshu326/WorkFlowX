import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "workflowx-dev-key")

    SQLALCHEMY_DATABASE_URI = "sqlite:///workflowx.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False