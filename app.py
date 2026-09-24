from flask import Flask, render_template, request, redirect, url_for, session, flash
# pyrefly: ignore [missing-import]
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pymysql
import pymysql.cursors
# pyrefly: ignore [missing-import]
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)

# Database Connection Helper
def get_db_connection():
    try:
        connection = pymysql.connect(
            host=app.config['DB_HOST'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            database=app.config['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"Database connection error: {e}")
        return None

# Decorators for Role-Based Access Control
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('You are not authorized to access the admin panel.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.', 'danger')
            return redirect(url_for('register'))
            
        try:
            with conn.cursor() as cursor:
                # Check if email exists
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash('Email already registered.', 'danger')
                    return redirect(url_for('register'))
                
                # Insert new user
                cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, 'user')", 
                               (username, email, hashed_password))
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash('An error occurred during registration.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.', 'danger')
            return redirect(url_for('login'))

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    
                    if user['role'] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid email or password.', 'danger')
        except Exception as e:
            flash('An error occurred during login.', 'danger')
        finally:
            conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- USER ROUTES ---
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    stats = {'total': 0, 'avg': 0, 'best': 0, 'latest': 0}
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total, AVG(percentage) as avg_score, 
                       MAX(percentage) as best_score 
                FROM quiz_results WHERE user_id = %s
            """, (session['user_id'],))
            result = cursor.fetchone()
            if result['total'] > 0:
                stats['total'] = result['total']
                stats['avg'] = round(result['avg_score'], 2)
                stats['best'] = result['best_score']
            
            cursor.execute("""
                SELECT percentage FROM quiz_results 
                WHERE user_id = %s ORDER BY completed_at DESC LIMIT 1
            """, (session['user_id'],))
            latest = cursor.fetchone()
            if latest:
                stats['latest'] = latest['percentage']
    finally:
        if conn:
            conn.close()
            
    return render_template('dashboard.html', stats=stats)

@app.route('/quiz')
@login_required
def quiz():
    conn = get_db_connection()
    questions = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, question, option_a, option_b, option_c, option_d, category FROM questions ORDER BY RAND() LIMIT 10")
            questions = cursor.fetchall()
    finally:
        if conn:
            conn.close()
            
    if not questions:
        flash('No questions available right now.', 'warning')
        return redirect(url_for('dashboard'))
        
    return render_template('quiz.html', questions=questions)

@app.route('/quiz/submit', methods=['POST'])
@login_required
def submit_quiz():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get all questions involved in this submission
            question_ids = [key.split('_')[1] for key in request.form.keys() if key.startswith('question_')]
            
            if not question_ids:
                flash('No answers submitted.', 'danger')
                return redirect(url_for('dashboard'))

            format_strings = ','.join(['%s'] * len(question_ids))
            cursor.execute(f"SELECT id, correct_answer FROM questions WHERE id IN ({format_strings})", tuple(question_ids))
            db_questions = {str(q['id']): q['correct_answer'] for q in cursor.fetchall()}
            
            score = 0
            total_questions = len(db_questions)
            answers_to_insert = []
            
            for q_id, correct_ans in db_questions.items():
                selected = request.form.get(f'question_{q_id}')
                is_correct = (selected == correct_ans)
                if is_correct:
                    score += 1
                answers_to_insert.append((q_id, selected, is_correct))
                
            percentage = (score / total_questions) * 100
            
            # Save Result
            cursor.execute("""
                INSERT INTO quiz_results (user_id, score, total_questions, percentage) 
                VALUES (%s, %s, %s, %s)
            """, (session['user_id'], score, total_questions, percentage))
            result_id = cursor.lastrowid
            
            # Save Individual Answers (Optional feature but good for detail)
            for q_id, selected, is_correct in answers_to_insert:
                cursor.execute("""
                    INSERT INTO quiz_answers (result_id, question_id, selected_answer, is_correct)
                    VALUES (%s, %s, %s, %s)
                """, (result_id, q_id, selected, is_correct))
                
            conn.commit()
            return redirect(url_for('result', id=result_id))
    except Exception as e:
        conn.rollback()
        flash('An error occurred while submitting the quiz.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

@app.route('/result/<int:id>')
@login_required
def result(id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM quiz_results WHERE id = %s AND user_id = %s", (id, session['user_id']))
            result = cursor.fetchone()
            if not result:
                flash('Result not found.', 'danger')
                return redirect(url_for('dashboard'))
            return render_template('result.html', result=result)
    finally:
        if conn:
            conn.close()

@app.route('/history')
@login_required
def history():
    conn = get_db_connection()
    results = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM quiz_results WHERE user_id = %s ORDER BY completed_at DESC", (session['user_id'],))
            results = cursor.fetchall()
    finally:
        if conn:
            conn.close()
    return render_template('history.html', results=results)

@app.route('/security-awareness')
def security_awareness():
    return render_template('security_awareness.html')


# --- ADMIN ROUTES ---
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    stats = {'users': 0, 'questions': 0, 'attempts': 0, 'avg_score': 0}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'user'")
            stats['users'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM questions")
            stats['questions'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count, AVG(percentage) as avg FROM quiz_results")
            res = cursor.fetchone()
            stats['attempts'] = res['count']
            if res['avg'] is not None:
                stats['avg_score'] = round(res['avg'], 2)
    finally:
        if conn:
            conn.close()
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/questions')
@admin_required
def admin_questions():
    conn = get_db_connection()
    questions = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM questions ORDER BY created_at DESC")
            questions = cursor.fetchall()
    finally:
        if conn:
            conn.close()
    return render_template('admin/questions.html', questions=questions)

@app.route('/admin/questions/add', methods=['GET', 'POST'])
@admin_required
def add_question():
    if request.method == 'POST':
        question = request.form['question']
        option_a = request.form['option_a']
        option_b = request.form['option_b']
        option_c = request.form['option_c']
        option_d = request.form['option_d']
        correct_answer = request.form['correct_answer']
        category = request.form['category']
        difficulty = request.form['difficulty']

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_answer, category, difficulty)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (question, option_a, option_b, option_c, option_d, correct_answer, category, difficulty))
                conn.commit()
                flash('Question added successfully.', 'success')
                return redirect(url_for('admin_questions'))
        except Exception as e:
            flash('Error adding question.', 'danger')
        finally:
            if conn:
                conn.close()

    return render_template('admin/add_question.html')

@app.route('/admin/questions/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_question(id):
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE questions SET 
                        question=%s, option_a=%s, option_b=%s, option_c=%s, option_d=%s, 
                        correct_answer=%s, category=%s, difficulty=%s 
                    WHERE id=%s
                """, (
                    request.form['question'], request.form['option_a'], request.form['option_b'],
                    request.form['option_c'], request.form['option_d'], request.form['correct_answer'],
                    request.form['category'], request.form['difficulty'], id
                ))
                conn.commit()
                flash('Question updated successfully.', 'success')
                return redirect(url_for('admin_questions'))
        except Exception as e:
            flash('Error updating question.', 'danger')
        finally:
            if conn:
                conn.close()
    else:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM questions WHERE id = %s", (id,))
                question = cursor.fetchone()
                if not question:
                    flash('Question not found.', 'danger')
                    return redirect(url_for('admin_questions'))
                return render_template('admin/edit_question.html', question=question)
        finally:
            if conn:
                conn.close()

@app.route('/admin/questions/delete/<int:id>', methods=['POST'])
@admin_required
def delete_question(id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM questions WHERE id = %s", (id,))
            conn.commit()
            flash('Question deleted successfully.', 'success')
    except Exception as e:
        flash('Error deleting question.', 'danger')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('admin_questions'))

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    users = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, email, role, created_at FROM users WHERE role = 'user' ORDER BY created_at DESC")
            users = cursor.fetchall()
    finally:
        if conn:
            conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/results')
@admin_required
def admin_results():
    conn = get_db_connection()
    results = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT qr.id, qr.score, qr.total_questions, qr.percentage, qr.completed_at, u.username, u.email 
                FROM quiz_results qr
                JOIN users u ON qr.user_id = u.id
                ORDER BY qr.completed_at DESC
            """)
            results = cursor.fetchall()
    finally:
        if conn:
            conn.close()
    return render_template('admin/results.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)