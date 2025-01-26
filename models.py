from app import app 
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
db=SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(32),unique=True,nullable=False)
    passhash=db.Column(db.String(256), nullable=False)
    full_name=db.Column(db.String(64), nullable=True)
    qualification=db.Column(db.String(64), nullable=True)
    dob=db.Column(db.DateTime, nullable=True)
    is_admin=db.Column(db.Boolean, nullable=False, default=False)

class Subject(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(64), nullable=False)
    description=db.Column(db.String(256), nullable=True)
    # chapter_id=db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)

class Chapter(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(64), nullable=False)
    description=db.Column(db.String(256), nullable=True)
    subject_id=db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    quizzes = db.relationship('Quiz', backref='chapter', lazy=True)

class Question(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(256), nullable=False)
    question_statment=db.Column(db.String(256), nullable=False)
    option1=db.Column(db.String(256), nullable=False)
    option2=db.Column(db.String(256), nullable=False)
    option3=db.Column(db.String(256), nullable=False)
    option4=db.Column(db.String(256), nullable=False)
    answer=db.Column(db.Integer, nullable=False)
    quiz_id=db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    

class Quiz(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    chapter_id=db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    date_of_quiz=db.Column(db.DateTime, nullable=False)
    time_duration = db.Column(db.String(16), nullable=False)
    remarks=db.Column(db.String(256), nullable=True)
    

class Score(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id=db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    total_score=db.Column(db.Integer, nullable=False)
    time_stamp_of_attempt=db.Column(db.DateTime, nullable=False)


with app.app_context():
    db.create_all()
    admin=User.query.filter_by(is_admin=True).first()
    if not admin:
        password_hash=generate_password_hash('admin')
        admin=User(username='admin', passhash=password_hash,full_name='admin', is_admin=True)
        db.session.add(admin)
        db.session.commit()