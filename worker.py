import os
from celery import Celery
from app import app, make_celery

celery = make_celery(app)