from flask import Flask, render_template,request,redirect,url_for,flash,session,jsonify
from app import app
from models import db,User,Subject,Chapter,Question,Quiz,Score
from werkzeug.security import generate_password_hash,check_password_hash
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy.sql import func

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    #if username or password did not field in the input box give warning
    if not username or not password:
        flash('Please fill out all fields', 'warning')
        return redirect(url_for('login'))
    #geting the data from data base
    user = User.query.filter_by(username=username).first()
    # if usename not present in the database then redirect to login page and give waring
    if not user:
        flash('Username does not exist', 'danger')
        return redirect(url_for('login'))
    # if password is wrong give Warning
    if not check_password_hash(user.passhash, password):
        flash('Incorrect password', 'danger')
        return redirect(url_for('login'))
    
    # geting the information so that session know that the user details
    session['user_id'] = user.id
    session['username'] = user.username
    session['is_admin'] = user.is_admin  

    flash('Login successful','success')
    
    # render according to user/admin
    if user.is_admin:
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('index',user_id=user.id))
    
# registration page
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    full_name = request.form.get('full_name')
    qualification=request.form.get('qualification')
    dob=request.form.get('dob')
    # if any of the input box is empty give warning massage
    if not username or not password or not confirm_password:
        flash('Please fill out all fields','danger')
        return redirect(url_for('register'))
    
    if password != confirm_password:
        flash('Passwords do not match')
        return redirect(url_for('register'))
    
    user = User.query.filter_by(username=username).first()

    dob_date = None
    if dob:  # Ensuring DOB is not empty
        # using try and except so that we can convert dob in proper formate if not posible did not give error
        try:
            dob = datetime.strptime(dob, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            return redirect(url_for('register'))
        
    # if same username already present give Warning
    if user:
        flash('Username already exists','success')
        return redirect(url_for('register'))
    # increpting the password
    password_hash = generate_password_hash(password)
    # storing all the detail in the database
    new_user = User(username=username, passhash=password_hash, full_name=full_name,qualification=qualification,dob=dob)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))

# decorator for authentication so no one use app without registration
def auth_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login to continue','danger')
            return redirect(url_for('login'))
    return inner

# admin authentication so no user get admin power
def admin_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if 'user_id' not in session:
            flash('Please login to continue','danger')
            return redirect(url_for('login'))
        user=User.query.get(session['user_id'])
        if not user.is_admin:
            flash('You are not authorized to view this page','danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return inner

# landing page for the admin/user
@app.route('/')
@auth_required
def index():
    user = User.query.get(session['user_id'])
    # if user is admin redirect to admin page if not show user page
    if user.is_admin:
        return redirect(url_for('admin'))
    
    search_query = request.args.get('query', '').strip().lower()

    # Fetch all subjects, chapters, and quizzes
    subjects = Subject.query.all()
    chapters = Chapter.query.all()
    quizzes = Quiz.query.all()

    # Filter based on search query
    if search_query:
        subjects = [subject for subject in subjects if search_query in subject.name.lower()]
        subject_ids = [subject.id for subject in subjects]
        chapters = [chapter for chapter in chapters if chapter.subject_id in subject_ids or search_query in chapter.name.lower()]
        quizzes = [quiz for quiz in quizzes if quiz.chapter_id in [chapter.id for chapter in chapters]]

    # Filter only upcoming quizzes
    today_date = datetime.now()
    quizzes = [
        {
            "id": quiz.id,
            "number_of_questions": Question.query.filter_by(quiz_id=quiz.id).count(),
            "date_of_quiz": quiz.date_of_quiz,
            "time_duration": quiz.time_duration
        }
        for quiz in quizzes if quiz.date_of_quiz >= today_date
    ]

    return render_template(
        'index.html',
        subjects=subjects,
        chapters=chapters,
        quizzes=quizzes,
        search_query=search_query
    )



# logout button
@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id')
    flash('Logout successful','success')
    return redirect(url_for('login'))

#------------------------------------------------- admin powers ----------------------------------------------

# --------------------------------------------- admin landing page ---------------------------------------------


@app.route('/admin')
@admin_required
def admin():
    # this is used so that it will show only first 2 div will show and we click on show all so it will show all the div's
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    search_query = request.args.get('query', '').strip().lower()

    # Fetch all subjects,chapter,question
    subjects = Subject.query.all()
    chapters = Chapter.query.all()
    questions = Question.query.all()

    # Calculate the number of questions for each chapter
    chapter_question_count = {chapter.id: 0 for chapter in chapters}
    for question in questions:
        if question.chapter_id in chapter_question_count:
            chapter_question_count[question.chapter_id] += 1

    # Filter subjects based on the search query
    if search_query:
        subjects = [subject for subject in subjects if search_query in subject.name.lower()]
    # showing only firs 2 subjects
    if not show_all and not search_query:
        subjects = subjects[:2]

    return render_template(
        'admin.html',
        subjects=subjects,
        chapters=chapters,
        questions=questions,
        chapter_question_count=chapter_question_count,
        show_all=show_all,
        search_query=search_query
    )



# ------------------------------------------------ for quiz page render --------------------------------------


@app.route('/quiz')
@admin_required
def quiz():
    # geting the search query
    search_query = request.args.get('query', '').strip().lower()
    show_all = request.args.get('show_all', 'false').lower() == 'true'

    # Fetch quizzes
    quizzes = Quiz.query.join(Chapter).all()

    # Filter quizzes based on search query
    if search_query:
        quizzes = [quiz for quiz in quizzes if search_query in quiz.chapter.name.lower()]
    # show only the first 2 quizzes
    if not show_all:
        quizzes = quizzes[:2]

    # Fetch questions for the quizzes
    questions = Question.query.all()

    return render_template(
        'quiz.html',
        quizzes=quizzes,
        questions=questions,
        show_all=show_all,
        search_query=search_query
    )

# ------------------------------------------------user details feating---------------------------------------

@app.route('/user', methods=['GET'])
@admin_required
def user():
    # geting the search query
    search_query = request.args.get('query', '').strip().lower()
    
    # If there is a search query filter users by their username and used ilike so that case-sensitivity dont affect
    if search_query:
        user = User.query.filter(User.username.ilike(f'%{search_query}%')).first()
    else:
        # If no query is provided, just get the user by their ID
        user = User.query.get(1)
    
    return render_template('admin/user_details.html', user=user)

# -----------------------------------subject add/delete in the admin home page----------------
@app.route('/admin/subject/add')
@admin_required
def add_subject():
    return render_template('/admin/subject/add.html')

@app.route('/subject/add',methods=['POST'])
@admin_required
def add_subject_post():
    subject_name=request.form.get('subject_name')
    description=request.form.get('description')
    subject_names_database = db.session.query(Subject.name).all()
    subject_names_list = [name[0].lower() for name in subject_names_database]

    # checking the subject is already present in database
    if subject_name.lower() in subject_names_list:
        flash('Subject already exists','danger')
        return redirect(url_for('add_subject'))
    
    subject=Subject(name=subject_name.upper(), description=description)
    db.session.add(subject)
    db.session.commit()
    flash('subject added sucessfully','success')
    return redirect(url_for('admin'))

@app.route('/subject/<int:subject_id>/delete')
@admin_required
def delete_subject(subject_id):
    subject=Subject.query.get(subject_id)
    if not subject:
        flash('Subject not found','danger')
        return redirect(url_for('admin'))
    return render_template('/admin/subject/delete.html', subject=subject)

@app.route('/subject/<int:subject_id>/delete', methods=['POST'])
@admin_required
def delete_subject_post(subject_id):
    subject=Subject.query.get(subject_id)
    if not subject:
        flash('Subject not found','danger')
        return redirect(url_for('admin'))
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully','success')
    return redirect(url_for('admin'))

# ------------------------------------------chapter add/edit/delete at admin home page---------------------------

@app.route('/chapter/add')
@admin_required
def add_chapter():
    subjects = Subject.query.all()
    return render_template('/admin/chapter/add.html', subjects=subjects)

@app.route('/chapter/add',methods=['POST'])
@admin_required
def add_chapter_post():
    chapter_name = request.form['chapter_name']
    description = request.form['description']
    subject_id = request.form['subject_id']
    chapter_name_database=db.session.query(Chapter.name).all()
    chapter_names_list = [name[0].lower() for name in chapter_name_database]

    # checking chapter name is alreaddy present in database
    if chapter_name.lower() in chapter_names_list:
        flash('Chapter already exists','danger')
        return redirect(url_for('add_chapter'))
    chapter=Chapter(name=chapter_name.upper(), description=description,subject_id=subject_id)
    db.session.add(chapter) 
    db.session.commit()
    flash('chapter added sucessfully','success')
    return redirect(url_for('admin'))

@app.route('/chapter/<int:chapter_id>/delete')
@admin_required
def delete_chapter(chapter_id):
    chapter=Chapter.query.get(chapter_id)
    if not chapter:
        flash('Chapter not found','danger')
        return redirect(url_for('admin'))
    return render_template('/admin/chapter/delete.html', chapter=chapter)

@app.route('/chapter/<int:chapter_id>/delete', methods=['POST'])
@admin_required
def delete_chapter_post(chapter_id):
    chapter = Chapter.query.get(chapter_id)
    
    # If chapter not found, flash a danger message and redirect to admin page
    if not chapter:
        flash('Chapter not found', 'danger')
        return redirect(url_for('admin'))
    
    # Delete the quiz
    quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
    for quiz in quizzes:
        db.session.delete(quiz)
    
    # update in database
    db.session.delete(chapter)
    db.session.commit()
    
    flash('Chapter and related quizzes deleted successfully', 'success')
    return redirect(url_for('admin'))


@app.route('/edit_chapter/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_chapter(id):
    chapter = Chapter.query.get_or_404(id)#id no matching database found

    if request.method == 'POST':
        chapter.name = request.form['name']
        chapter.description = request.form['description']
        db.session.commit()
        flash('Chapter updated successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('/admin/chapter/edit.html', chapter=chapter)

@app.route('/question/<int:question_id>/delete')
@admin_required
def delete_question(question_id):
    question=Question.query.get(question_id)
    if not question:
        flash('Question not found','danger')
        return redirect(url_for('quiz'))
    return render_template('/admin/question/delete.html', question=question)

@app.route('/question/<int:question_id>/delete',methods=['POST'])
@admin_required
def delete_question_post(question_id):
    question=Question.query.get(question_id)
    if not question:
        flash('Question not found','danger')
        return redirect(url_for('quiz'))
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully','success')
    return redirect(url_for('quiz'))

# ---------------------------------------quiz add/delete in quiz page-----------------------------------
@app.route('/quiz/add')
@admin_required
def add_quiz():
    chapters=Chapter.query.all()
    now=datetime.now().strftime('%Y-%m-%d')
    return render_template('/admin/quiz/add.html', chapters=chapters,now=now)

@app.route('/quiz/add', methods=['POST'])
@admin_required
def add_quiz_post():
    chapter_id = request.form['chapter_id']
    date = request.form['date']
    duration_str = request.form['duration']
    # use try except so that if error accurs so website did not crase
    try:
        chapter_id = int(chapter_id)
        quiz_date = datetime.strptime(date, "%Y-%m-%d")  #formate fixing
        quiz = Quiz(
            chapter_id=chapter_id,
            date_of_quiz=quiz_date,
            time_duration=duration_str,  # Store duration directly as a string 
            remarks=request.form.get('remarks'),
        )
        db.session.add(quiz)
        db.session.commit()

        flash('Quiz added successfully','success')
        return redirect(url_for('quiz'))
    except ValueError:
        return "Invalid date or duration format. Ensure date is YYYY-MM-DD and duration is HH:MM.", 400  #this is clint side error
    except Exception as e:
        return f"An error occurred: {e}", 500 #this is server side error
    
@app.route('/quiz/<int:quiz_id>/delete')
@admin_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash('Quiz not found')
        return redirect(url_for('quiz'))
    return render_template('/admin/quiz/delete.html', quiz=quiz)

@app.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@admin_required
def delete_quiz_post(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash('Quiz not found','danger')
        return redirect(url_for('quiz'))
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully','success')
    return redirect(url_for('quiz'))

# ------------------------------------ for add/edit/delete question on quiz page---------------------------------
@app.route('/question/add/<int:quiz_id>', methods=['GET'])
@admin_required
def add_question(quiz_id):
    chapters = Chapter.query.all()
    return render_template('/admin/question/add.html', chapters=chapters, quiz_id=quiz_id)

@app.route('/question/add/<int:quiz_id>', methods=['POST'])
@admin_required
def add_question_post(quiz_id):
    chapter_id = request.form['chapter_id']
    question_title = request.form['question_title']
    question_statement = request.form['question']
    option1 = request.form['option1']
    option2 = request.form['option2']
    option3 = request.form['option3']
    option4 = request.form['option4']
    answer = int(request.form['answer'])

    question = Question(
        chapter_id=chapter_id,
        title=question_title,
        question_statment=question_statement,
        option1=option1,
        option2=option2,
        option3=option3,
        option4=option4,
        answer=answer,
        quiz_id=quiz_id
    )
    db.session.add(question)
    db.session.commit()
    flash('Question added successfully!','success')
    return redirect(url_for('quiz'))

@app.route('/question/edit/<int:question_id>',methods=['GET','POST'])
@admin_required
def edit_question(question_id):
    question=Question.query.get_or_404(question_id)
    chapters = Chapter.query.all()
    if request.method=='POST':
        question.title=request.form['title']
        db.session.commit()
        flash('Question title updated successfully!','success')
        return redirect(url_for('quiz'))
    
    return render_template('/admin/question/edit.html', question=question)

# ----------------------------------------------search button-----------------------------------------


@app.route('/search')
@admin_required
def search():
    search_type = request.args.get('select_search')
    search_query = request.args.get('query', '').strip().lower()

    if search_type == 'subject':
        subjects = Subject.query.all()
        if search_query:
            subjects = [subject for subject in subjects if search_query in subject.name.lower()]
        return render_template('admin.html', subjects=subjects, search_query=search_query)

    elif search_type == 'quiz':
        quizzes = Quiz.query.all()
        if search_query:
            quizzes = [quiz for quiz in quizzes if search_query in quiz.name.lower()]
        return render_template('quiz.html', quizzes=quizzes, search_query=search_query)

    elif search_type == 'user':
        users = User.query.all()
        if search_query:
            users = [user for user in users if search_query in user.username.lower()]
        return render_template('users.html', users=users, search_query=search_query)

    # If no valid search type is selected, return to home page or handle as needed
    return redirect(url_for('home'))



# --------------------------------------user----------------------------------------

@app.route('/quiz/<int:quiz_id>/details', methods=['GET'])
@auth_required
def quiz_details(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)   #when problem during fetching the data
    number_of_questions= Question.query.filter_by(quiz_id=quiz.id).count()
    chapter=Chapter.query.get(quiz.chapter_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    subject = Subject.query.get(chapter.subject_id)
    return render_template('/user/quiz_details.html',
                quiz=quiz,chapter=chapter ,
                questions=questions,number_of_questions=number_of_questions,
                subject=subject
    )

@app.route('/quiz_scores/<int:user_id>')
@auth_required
def quiz_scores(user_id):
    user = User.query.get(session['user_id'])
    if not user or user.id != user_id:
        return "Unauthorized access", 403     #when non authorized person want to access

    scores = Score.query.filter_by(user_id=user.id).all()

    # Combine scores with quiz details
    score_details = []
    for score in scores:
        quiz = Quiz.query.get(score.quiz_id)
        if quiz:
            score_details.append({
                'quiz_id': quiz.id,
                'number_of_questions': len(Question.query.filter_by(quiz_id=quiz.id).all()),
                'attempted_date': score.time_stamp_of_attempt,
                'total_score': score.total_score
            })

    return render_template('/user/quiz_scores.html', score_details=score_details)


@app.route('/start_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@auth_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    user=session['user_id']
    # Handle empty quiz case
    if not questions:
        flash("This quiz has no questions. Please contact the admin.", "warning")
        return redirect(url_for('index'))

    total_questions = len(questions)
    current_index = int(request.form.get('current_index', 0))
    user_answers = request.form.getlist('user_answers') or [''] * total_questions

    if request.method == 'POST':
        selected_option = request.form.get('selected_option')
        if selected_option:
            user_answers[current_index] = selected_option

        # Check if the "Submit" button was clicked
        if 'submit' in request.form:
            correct_answers = 0
            for i, question in enumerate(questions):
                if user_answers[i] == str(question.answer):  # Check if the selected option is correct
                    correct_answers += 1

            # Save the score to the database
            score = Score(
                user_id=user,  # Ensure the user is logged in
                quiz_id=quiz.id,
                total_score=correct_answers,
                time_stamp_of_attempt=db.func.now(),
            )
            db.session.add(score)
            db.session.commit()

            flash(f"Quiz submitted! Your score is {correct_answers}/{total_questions}.", "success")
            return redirect(url_for('index'))

        # If "Save & Next" was clicked, move to the next question
        current_index += 1
        if current_index >= total_questions:
            current_index = total_questions - 1  # Prevent going out of bounds

    # Render the current question
    question = questions[current_index]
    return render_template(
        '/user/start_quiz.html',
        quiz=quiz,
        question=question,
        current_index=current_index,
        total_questions=total_questions,
        user_answers=user_answers
    )


@app.route('/summary/<int:user_id>/')
def user_summary(user_id):
    # Subject-wise number of quizzes attempted by the user
    subject_quizzes = db.session.query(
        Subject.name.label('subject_name'),
        func.count(Score.quiz_id).label('quiz_count')
    ).join(Chapter, Chapter.subject_id == Subject.id)\
     .join(Quiz, Quiz.chapter_id == Chapter.id)\
     .join(Score, Quiz.id == Score.quiz_id)\
     .filter(Score.user_id == user_id)\
     .group_by(Subject.name)\
     .all()

    subject_quiz_data = {row.subject_name: row.quiz_count for row in subject_quizzes}
    # Month-wise number of quizzes attempted
    month_quizzes = db.session.query(
        func.strftime('%m', Score.time_stamp_of_attempt).label('month'),
        func.count(Score.id).label('quiz_count')
    ).filter(Score.user_id == user_id)\
     .group_by(func.strftime('%m', Score.time_stamp_of_attempt))\
     .all()

    month_quiz_data = {row.month: row.quiz_count for row in month_quizzes}

    # Fetch user details for the summary page
    user = User.query.get(user_id)

    return render_template(
        '/user/summary.html',
        user=user,  # Pass user details
        subject_data=subject_quiz_data,
        month_data=month_quiz_data
    )


@app.route('/admin/summary/')
def admin_summary():
    # Subject-wise top scores
    subject_top_scores = db.session.query(
        Subject.name.label('subject_name'),
        func.max(Score.total_score).label('top_score')
    ).join(Chapter, Chapter.subject_id == Subject.id)\
     .join(Quiz, Quiz.chapter_id == Chapter.id)\
     .join(Score, Quiz.id == Score.quiz_id)\
     .group_by(Subject.name)\
     .all()

    top_scores_data = {row.subject_name: row.top_score for row in subject_top_scores}

    # Subject-wise number of user attempts
    subject_attempts = db.session.query(
        Subject.name.label('subject_name'),
        func.count(Score.id).label('attempt_count')
    ).join(Chapter, Chapter.subject_id == Subject.id)\
     .join(Quiz, Quiz.chapter_id == Chapter.id)\
     .join(Score, Quiz.id == Score.quiz_id)\
     .group_by(Subject.name)\
     .all()

    user_attempts_data = {row.subject_name: row.attempt_count for row in subject_attempts}

    return render_template(
        '/admin/summary_admin.html',
        top_scores=top_scores_data,
        user_attempts=user_attempts_data
    )