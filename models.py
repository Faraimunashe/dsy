from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import datetime

db = SQLAlchemy()

#from .models import User
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    role = db.Column(db.Integer)

    def __init__(self, email, password, name, role):
        self.email=email
        self.password=password
        self.name=name
        self.role=role


class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    characters = db.Column(db.String(30))
    file = db.Column(db.String(30))

    def __init__(self, characters, file):
        self.characters=characters
        self.file=file

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)

    def __init__(self, userid):
        self.userid=userid


class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sessionid = db.Column(db.Integer)
    wordid = db.Column(db.Integer)
    passed = db.Column(db.Boolean)
    answer = db.Column(db.String(30))

    def __init__(self, sessionid, wordid, passed, answer):
        self.sessionid=sessionid
        self.wordid=wordid
        self.passed=passed
        self.answer=answer