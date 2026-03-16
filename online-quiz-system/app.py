from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
import os

app = Flask(__name__)

# Secret key
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///quiz.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =======================
# Database Models
# =======================

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


# =======================
# Create Database
# =======================

with app.app_context():
    db.create_all()

# =======================
# Student Routes
# =======================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user:
            flash('Email already exists. Please login.')
            return redirect(url_for('login'))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session['user_id'] = user.id
            session['user_name'] = user.name

            flash(f'Welcome back, {user.name}!')

            return redirect(url_for('start_quiz'))

        else:
            flash('Invalid email or password.')

    return render_template('login.html')


@app.route('/start-quiz')
def start_quiz():

    if 'user_id' not in session:
        flash('Please login to start the quiz.')
        return redirect(url_for('login'))

    session['score'] = 0
    session['current_question_index'] = 0
    session['result_saved'] = False

    questions = Question.query.all()

    session['question_ids'] = [q.id for q in questions]

    if not session['question_ids']:
        flash('No questions available in the quiz yet.')
        return redirect(url_for('index'))

    return redirect(url_for('quiz'))


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    question_ids = session.get('question_ids', [])
    current_index = session.get('current_question_index', 0)

    if current_index >= len(question_ids):
        return redirect(url_for('result'))

    question_id = question_ids[current_index]
    question = Question.query.get(question_id)

    if request.method == 'POST':

        selected_option = request.form.get('option')

        if selected_option:

            if int(selected_option) == question.correct_option:
                session['score'] += 1

        session['current_question_index'] += 1

        return redirect(url_for('quiz'))

    return render_template(
        'quiz.html',
        question=question,
        current_num=current_index + 1,
        total_num=len(question_ids)
    )


@app.route('/result')
def result():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    score = session.get('score', 0)
    total = len(session.get('question_ids', []))
    name = session.get('user_name')

    if not session.get('result_saved'):

        new_result = Result(
            student_name=name,
            score=score,
            total_questions=total
        )

        db.session.add(new_result)
        db.session.commit()

        session['result_saved'] = True

    return render_template(
        'result.html',
        name=name,
        score=score,
        total=total
    )


@app.route('/leaderboard')
def leaderboard():

    top_results = Result.query.order_by(
        Result.score.desc(),
        Result.date.asc()
    ).limit(10).all()

    return render_template('leaderboard.html', top_results=top_results)


# =======================
# Admin Routes
# =======================

@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():

    if request.method == 'POST':

        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        admin = Admin.query.filter_by(email=email).first()

        if admin:
            flash('Admin email already exists. Please login.')
            return redirect(url_for('admin_login'))

        new_admin = Admin(name=name, email=email, password=password)

        db.session.add(new_admin)
        db.session.commit()

        flash('Admin registration successful!')
        return redirect(url_for('admin_login'))

    return render_template('admin_register.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        admin = Admin.query.filter_by(email=email, password=password).first()

        if admin:

            session['admin_logged_in'] = True
            session['admin_name'] = admin.name

            flash(f'Welcome Admin {admin.name}!')

            return redirect(url_for('admin_dashboard'))

        else:
            flash('Invalid admin credentials.')

    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():

    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    questions = Question.query.all()
    results = Result.query.order_by(Result.date.desc()).all()

    total_students = User.query.count()
    total_quizzes = Result.query.count()

    avg_score = db.session.query(func.avg(Result.score)).scalar() or 0
    avg_score = round(avg_score, 2)

    analytics = {
        "total_students": total_students,
        "total_quizzes": total_quizzes,
        "avg_score": avg_score
    }

    return render_template(
        'admin_dashboard.html',
        questions=questions,
        results=results,
        analytics=analytics
    )


@app.route('/admin/add', methods=['GET', 'POST'])
def add_question():

    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':

        text = request.form.get('text')
        op1 = request.form.get('option1')
        op2 = request.form.get('option2')
        op3 = request.form.get('option3')
        op4 = request.form.get('option4')
        correct = request.form.get('correct_option')

        new_q = Question(
            text=text,
            option1=op1,
            option2=op2,
            option3=op3,
            option4=op4,
            correct_option=int(correct)
        )

        db.session.add(new_q)
        db.session.commit()

        flash('Question added successfully!')

        return redirect(url_for('admin_dashboard'))

    return render_template('add_question.html')


@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('index'))


# =======================
# Run Flask App
# =======================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)