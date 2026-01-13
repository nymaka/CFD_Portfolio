from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from RunQueries import Classroom, Database, users, Assignment, Submission, Sorting, Teacher
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
from matplotlib.path import Path
import os
import bcrypt
import imageio
import threading

app = Flask(__name__)

app.secret_key = 'Nirukt'

@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    # Checking if the admin has entered the correct password
    if 'admin_authenticated' not in session:
        if request.method == 'POST':
            entered_password = request.form['admin_password']

            # Only 1 admin account so hash is stored here itself
            admin_password_hash = b'$2b$12$h7gkzQoVLnMFJYgmfaELGecWEdwLQrgaGbPYYIbY1aUMuuf6dneYi'
            if bcrypt.checkpw(entered_password.encode('utf-8'), admin_password_hash):
                session['admin_authenticated'] = True
                flash("Password correct. Now you can add a teacher.", "success")
                return redirect(url_for('add_teacher_form'))
            else:
                flash("Incorrect password. Please try again.", "error")
                return redirect(url_for('add_teacher'))
        return render_template('add_teacher1.html') 
    # If admin is authenticated, allow them to add a teacher
    return redirect(url_for('add_teacher_form'))

@app.route('/add_teacher_form', methods=['GET', 'POST'])
def add_teacher_form():
    if 'admin_authenticated' not in session:
        flash("You need to authenticate first.", "warning")
        return redirect(url_for('add_teacher'))

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        
        valid, message = Sorting.validate_password(password)
        if not valid:
            flash(message, "error")
            return redirect(url_for('add_teacher_form'))

        db = Database()
        user_class = users(db)

        if user_class.addUser(email, first_name, last_name, password):
            flash("Teacher added successfully!", "success")
            session.clear() # clear session so that no-one else can add a teacher without signing in again
            return redirect(url_for('home'))
        else:
            flash("An error occurred while adding the teacher. Please try again.", "error")

    return render_template('add_teacher2.html')

@app.route('/')
def home():
    if 'user_id' not in session:
        flash("Please log in to access the dashboard", "warning")
        return redirect(url_for('login'))
    # Checks for login to prevent accessing data without credentials.

    db = Database()
    class_instance = Classroom(db) # instantiation

    user_id = session['user_id']
    dashboard_data = class_instance.getDashboard(user_id)
    # SQL query gets the data needed for the dashboard to be displayed

    total_students_data = class_instance.getTotalStudents()
    total_students_dict = {row[0]: row[1] for row in total_students_data}  
    # Maps class name to total students

    classes = []
    for row in dashboard_data:
        class_name = row[0]
        classes.append({
            "name": class_name,
            "assignment": row[2],
            "total_students": total_students_dict.get(class_name, 0)  
        })
    # puts the data in a format to be displayed by the HTML template
    return render_template('dashboard.html', classes=classes)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        forename = request.form['forename']
        surname = request.form['surname']

        valid, message = Sorting.validate_password(password)
        if not valid:
            flash(message, "error")
            return redirect(url_for('register'))
        # This is to validate passwords that are being made 

        db = Database()
        user_class = users(db)
        
        # Instantiation of addStudent function from users class to add the new student
        if user_class.addUser(email, forename, surname, password):
            flash("Account created successfully!", "success")
            return redirect(url_for('home'))
        else:
            flash("Email already exists. Please use a different email.", "error")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()  # Clears all session data
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))  # Redirects to the login page


@app.route('/login', methods=['GET', 'POST'])
def login():
    db = Database()  # Instantiation
    user_instance = users(db)

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Using the loginUser function to check password
        user = user_instance.loginUser(email, password)

        if user:
            # Login successful
            session['user_id'] = user[0] 
            session['email'] = user[1]
            session['forename'] = user[2]
            session['surname'] = user[3] 
            session['user_type'] = user[5]
            # stpring data in the session 
            
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Incorrect email or password.", "error")

    return render_template('login.html')

@app.route('/add_class', methods=['GET', 'POST'])
def add_class():
    # Ensuring the user is logged in
    if 'user_id' not in session:
        flash("Please log in to add a class.", "warning")
        return redirect(url_for('login'))

    db = Database()
    class_instance = Classroom(db)
    user_instance = users(db)
    # instantiation

    #Grabbing user id from session
    user_id = session['user_id']
    
    # Checking if the user is a teacher
    user_type = user_instance.getUserType(user_id)
    if not user_type or user_type[0] != 1:  # Type 1 = teacher
        flash("You are not authorized to add a class.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        class_name = request.form['class_name']

        result = class_instance.addClass(class_name, user_id)

        if result["success"]:
            flash(result["message"], "success")
            return redirect(url_for('home'))
        else:
            flash(result["message"], "error")

    return render_template('add_class.html')


@app.route('/assignments/<class_name>')
def assignments(class_name):
    if 'user_id' not in session:
        flash("Please log in to view assignments", "warning")
        return redirect(url_for('login'))

    db = Database()
    user_id = session['user_id']
    user_instance = users(db)
    assignment_instance = Assignment(db)
    # instantiation

    # Check if the user is a teacher
    user_type = user_instance.getUserType(user_id)
    if user_type and user_type[0]:  # Type 1 = teacher
        return redirect(url_for('teacher_assignments', class_name=class_name))

    # Fetching assignments for the student
    assignments = assignment_instance.getAssignments(class_name)

    assignments_data = []
    for assignment in assignments:
        assignment_id = assignment[0]
        submission_instance = Submission(db)

        # Checking if the student has submitted this assignment
        submission = submission_instance.getSubmissions(assignment_id=assignment_id, user_id=user_id)

        # Counting the number of students who submitted this assignment
        submitted_count = submission_instance.getSubmissionCount(assignment_id)

        assignments_data.append({
            "id": assignment_id,
            "title": assignment[1],
            "task": assignment[2],
            "submitted_count": submitted_count,
            "is_submitted": bool(submission),
            "submission_text": submission[0] if submission else None,
        })

    # Sort assignments, unsubmitted first, then submitted.
    assignments_data.sort(key=lambda x: x["is_submitted"])

    return render_template('assignments.html', class_name=class_name, assignments=assignments_data)


@app.route('/teacher_assignments/<class_name>')
def teacher_assignments(class_name):
    if 'user_id' not in session:
        flash("Please log in to view assignments", "warning")
        return redirect(url_for('login'))

    db = Database()
    assignment_instance = Assignment(db)

    # Fetching assignments for the class
    assignments = assignment_instance.getAssignments(class_name)

    assignments_data = []
    for assignment in assignments:
        assignment_id = assignment[0]
        submission_instance = Submission(db)

        # Fetchingt the number of students who submitted the assignment
        submitted_count = submission_instance.getSubmissionCount(assignment_id)

        # Fetching the latest submission time
        latest_submission = submission_instance.getLatestSubmissionTime(assignment_id)

        assignments_data.append({
            "id": assignment_id,
            "title": assignment[1],
            "task": assignment[2],
            "submitted_count": submitted_count,
            "latest_submission": latest_submission,
        })

    # Sorting completed assignments by latest submission time
    completed_assignments = [a for a in assignments_data if a["latest_submission"] is not None]
    uncompleted_assignments = [a for a in assignments_data if a["latest_submission"] is None]
    completed_assignments.sort(key=lambda x: x["latest_submission"], reverse=True)

    sorted_assignments = completed_assignments + uncompleted_assignments

    return render_template('teacher_assignments.html', class_name=class_name, assignments=sorted_assignments)

@app.route('/teacher_assignments_sorted/<class_name>')
def teacher_assignments_sorted(class_name):
    if 'user_id' not in session:
        flash("Please log in to view assignments", "warning")
        return redirect(url_for('login'))

    db = Database()
    assignment_instance = Assignment(db)

    # Fetching assignments for the class to sort
    assignments = assignment_instance.getAssignmentsForClass(class_name)

    assignments_data = []
    submission_instance = Submission(db)

    for assignment in assignments:
        assignment_id = assignment[0]

        # Fetching the number of students who submitted the assignment
        submitted_count = submission_instance.getSubmissionCount(assignment_id)

        # Fetching the latest submission time
        latest_submission = submission_instance.getLatestSubmissionTime(assignment_id)

        assignments_data.append({
            "id": assignment_id,
            "title": assignment[1],
            "task": assignment[2],
            "submitted_count": submitted_count,
            "latest_submission": latest_submission,
        })

    # Merge Sort to sort in ascending order of time submitted
    sorted_assignments = Sorting.merge_sort_assignments(assignments_data, key="id")

    # Reversing the list if user clicks descending
    sort_order = request.args.get('order', 'asc').lower()
    if sort_order == 'desc':
        sorted_assignments = Sorting.reverse_assignments(sorted_assignments)

    return render_template(
        'teacher_assignments_sorted.html',
        class_name=class_name,
        assignments=sorted_assignments,
        current_order=sort_order
    )


@app.route('/teacher_marksheet/<int:assignment_id>')
def teacher_marksheet(assignment_id):
    if 'user_id' not in session:
        flash("Please log in to view the marksheet", "warning")
        return redirect(url_for('login'))

    db = Database()
    submission_instance = Submission(db)

    # Fetch the marksheet data for the assignment
    marksheet_data = submission_instance.getMarksheet(assignment_id)

    # Fetch assignment details
    assignment_instance = Assignment(db)
    assignment_title = assignment_instance.getAssignmentTitle(assignment_id)

    formatted_marksheet = [{
        "UserID": row[0],
        "StudentName": row[1],
        "SubmissionText": row[2],
        "SubmissionMark": row[3],
        "SubmissionGrade": row[4],
        "SubmissionTime": row[5],
    } for row in marksheet_data]
    # Putting it in format for the HTML
    return render_template('teacher_marksheet.html',
                           marksheet_data=formatted_marksheet,
                           assignment_title=assignment_title,
                           assignment_id=assignment_id)


@app.route('/join_class', methods=['GET', 'POST'])
def join_class():
    if 'user_id' not in session:
        flash("Please log in to join a class.", "warning")
        return redirect(url_for('login'))

    db = Database()
    class_instance = Classroom(db)
    user_id = session['user_id']
    # instantiation

    if request.method == 'POST':
        class_name = request.form['class_id']
        # checking is class already exists since names must be unique
        if not class_instance.classExists(class_name):
            flash("Invalid Class Code. Please try again.", "error")
        else:
            if class_instance.addClassUsers(user_id, class_name):
                flash(f"You have successfully joined the class '{class_name}'.", "success")
            else:
                flash(f"You are already part of the class '{class_name}'.", "info")
        return redirect(url_for('join_class'))

    return render_template('join_class.html')


@app.route('/submit_assignment/<int:assignment_id>', methods=['GET', 'POST'])
def submit_assignment(assignment_id):
    if 'user_id' not in session:
        flash("Please log in to submit assignments", "warning")
        return redirect(url_for('login'))

    db = Database()
    assignment_instance = Assignment(db)
    submission_instance = Submission(db)

    user_id = session['user_id']

    assignment = assignment_instance.getAssignmentById(assignment_id)

    if not assignment:
        flash("Assignment not found.", "danger")
        return redirect(url_for('home'))

    if request.method == 'POST':
        submission_text = request.form['submission_text']
        submission_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


        if submission_instance.addSubmission(submission_time, submission_text, user_id, assignment_id):
            flash(f"Assignment '{assignment['Title']}' submitted successfully!", "success")
            return redirect(url_for('assignments', class_name=assignment['ClassName']))
        else:
            flash("Failed to submit assignment. Please try again.", "danger")

    return render_template(
        'submit_assignment.html',
        assignment_id=assignment_id,
        assignment_title=assignment['Title'],  
        assignment_summary=assignment['Task']
    )


@app.route('/view_submission/<int:assignment_id>')
def view_submission(assignment_id):
    if 'user_id' not in session:
        flash("Please log in to view your submission", "warning")
        return redirect(url_for('login'))

    db = Database()
    submission_instance = Submission(db)
    assignment_instance = Assignment(db)
    user_id = session['user_id']

    assignment = assignment_instance.getAssignmentDetails(assignment_id)
    submission = submission_instance.getUserSubmission(user_id, assignment_id)

    if not assignment or not submission:
        flash("Submission not found or not completed.", "danger")
        return redirect(url_for('assignments', class_name=session.get('class_name', '')))

    return render_template(
        'view_submission.html',
        assignment_title=assignment[0],
        assignment_summary=assignment[1],
        submission_text=submission[0]
    )


@app.route('/marksheet/<class_name>')
def marksheet(class_name):
    if 'user_id' not in session:
        flash("Please log in to view your marksheet", "warning")
        return redirect(url_for('login'))

    db = Database()
    assignment_instance = Assignment(db)
    submission_instance = Submission(db)
    user_id = session['user_id']

    assignments = assignment_instance.getAssignmentsForClass(class_name)
    submissions = submission_instance.getSubmissionsInClass(user_id, class_name)

    submissions_dict = {
        sub[0]: {
            "mark": sub[1],
            "grade": sub[2],
            "submission_text": sub[3],
            "submission_date": sub[4] if sub[4] else None
        }
        for sub in submissions
    }
    # putting data in a format for the HTML.
    marksheet_data = []
    for assignment in assignments:
        assignment_id = assignment[0]
        title = assignment[1]

        if assignment_id in submissions_dict:
            # writes marks in a format out of 100 so its clear on the marksheet.
            marks = f"{submissions_dict[assignment_id]['mark']}/100" if submissions_dict[assignment_id]['mark'] else "Missing"
            grade = submissions_dict[assignment_id]["grade"]
            comments = submissions_dict[assignment_id]["submission_text"]
            date = submissions_dict[assignment_id]["submission_date"]
        else:
            marks = "Missing"
            grade = None
            comments = ""
            date = None
            # goes to none fot no data so that doesn't crash

        marksheet_data.append({
            "title": title,
            "marks": marks,
            "grade": grade,
            "comments": comments,
            "date": date
        })

    return render_template('marksheet.html', class_name=class_name, marksheet_data=marksheet_data)

@app.route('/plot_marks/<class_name>')
def plot_marks(class_name):
    if 'user_id' not in session:
        flash("Please log in to view your data", "warning")
        return redirect(url_for('login'))

    db = Database()
    submission_instance = Submission(db)
    user_id = session['user_id']

    # Fetch grades and marks for the user in the specified class
    grades_data = submission_instance.getGradesAndMarks(class_name, user_id)
    # filters out any submissions which are not given a mark
    filtered_data = [row for row in grades_data if row[1] is not None]
    # grades mapping since can't calculate with qualitative data.
    grade_mapping = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1, 'U': 0}

    titles = [row[0] for row in filtered_data]
    marks = [row[1] for row in filtered_data]
    grades = [grade_mapping.get(row[2], 0) for row in filtered_data]

    avg_mark = sum(marks) / len(marks) if marks else 0
    avg_grade = sum(grades) / len(grades) if grades else 0
    # working out averages which need to be plotted

    graph_data = {
        "titles": titles,
        "marks": marks,
        "grades": grades,
        "avg_mark": avg_mark,
        "avg_grade": avg_grade,
    }

    return render_template('plot_marks.html', class_name=class_name, graph_data=graph_data)

@app.route('/user_submissions/<int:user_id>')
def user_submissions(user_id):
    if 'user_id' not in session:
        flash("Please log in to view your submissions", "warning")
        return redirect(url_for('login'))

    db = Database()
    submission_instance = Submission(db)

    submissions = submission_instance.getUserSubmissions(user_id)

    submissions_data = []
    for row in submissions:
        submission_time = row[4]
        if submission_time:
            try:
                formatted_time = datetime.strptime(submission_time, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y %I:%M %p")
            except ValueError:
                formatted_time = "Invalid Date"
        else:
            formatted_time = "—"
            #checks the time and formats it since I was having some issues

        submissions_data.append({
            "title": row[0],
            "marks": row[1] if row[1] is not None else "Not Graded",
            "grade": row[2] if row[2] is not None else "—",
            "answer": row[3],
            "time": formatted_time
        })

    return render_template('user_submissions.html', user_id=user_id, submissions=submissions_data)


@app.route('/plot_user_marks/<int:user_id>')
# very similar to plot marks
def plot_user_marks(user_id):
    if 'user_id' not in session:
        flash("Please log in to view your graphs", "warning")
        return redirect(url_for('login'))
    db = Database()
    submission_instance = Submission(db)

    user_data = submission_instance.getUserGradeAndMarks(user_id)

    titles_with_dates = []
    marks = []
    grades = []
    grade_map = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1, 'U': 0}

    for row in user_data:
        if row[1] is not None:
            date_part = row[3].split(" ")[0] if row[3] else "—"
            label = f"{date_part} - {row[0]}"
            titles_with_dates.append(label)
            marks.append(row[1])
            grades.append(grade_map.get(row[2], None))

    avg_mark = sum(marks) / len(marks) if marks else 0
    avg_grade = sum(grades) / len(grades) if grades else 0

    #predicted grade algorithm being called
    predicted_grade = Sorting.predict_grade(grades)

    graph_data = {
        "titles": titles_with_dates,
        "marks": marks,
        "grades": grades,
        "avg_mark": avg_mark,
        "avg_grade": avg_grade,
        "predicted_grade": predicted_grade
    }

    return render_template('plot_user_marks.html', user_id=user_id, graph_data=graph_data)

@app.route('/add_assignment/<class_name>', methods=['GET', 'POST'])
def add_assignment(class_name):

    if 'user_id' not in session:
        flash("Please log in to create an assignment.", "warning")
        return redirect(url_for('login'))

    # Ensure the user is a teacher
    user_id = session['user_id']
    db = Database()
    user_instance = users(db)
    user_type = user_instance.getUserType(user_id)
    if not user_type or user_type[0] != 1:  # Type 1 = teacher
        flash("Only teachers can create assignments.", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        task = request.form['task']

        assignment_instance = Assignment(db)
        success, message = assignment_instance.addAssignment(title, task, class_name)
        if success:
            flash(message, "success")
            return redirect(url_for('assignments', class_name=class_name))
        else:
            flash(message, "error")

    return render_template('add_assignment.html', class_name=class_name)

@app.route('/marksheet/assignment/<int:assignment_id>')
#similar to marksheer
def assignment_marksheet(assignment_id):
    if 'user_id' not in session:
        flash("Please log in to view the marksheet", "warning")
        return redirect(url_for('login'))

    db = Database()
    submission_instance = Submission(db)
    assignment_instance = Assignment(db)

    marksheet_data = submission_instance.getAssignmentSubmissions(assignment_id)

    processed_marksheet_data = []
    for row in marksheet_data:
        submission_time = row[4]
        if submission_time:
            try:
                formatted_time = datetime.strptime(submission_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                formatted_time = 'Invalid Date'
        else:
            formatted_time = None

        processed_marksheet_data.append({
            "UserID": row[0],
            "UserName": row[1],
            "SubmissionMark": row[2],
            "SubmissionGrade": row[3],
            "SubmissionTime": formatted_time,
        })

    assignment = assignment_instance.getAssignmentDetails(assignment_id)
    if not assignment:
        return "Assignment not found", 404

    return render_template(
        'assignment_marksheet.html',
        marksheet_data=processed_marksheet_data,
        assignment_title=assignment[0]
    )

@app.route('/plot_assignment_marks/<int:assignment_id>')
#similar to plot marks
def plot_assignment_marks(assignment_id):
    db = Database()
    submission_instance = Submission(db)

    assignment_data = submission_instance.getAssignmentGradesAndMarks(assignment_id)

    user_names = []
    marks = []
    grades = []
    grade_map = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1, 'U': 0}
    for row in assignment_data:
        if row[1] is not None:
            user_names.append(row[0])
            marks.append(row[1])
            grades.append(grade_map.get(row[2], None))

    avg_mark = sum(marks) / len(marks) if marks else 0
    avg_grade = sum(grades) / len(grades) if grades else 0

    graph_data = {
        "user_names": user_names,
        "marks": marks,
        "grades": grades,
        "avg_mark": avg_mark,
        "avg_grade": avg_grade        
    }

    return render_template('plot_assignment_marks.html', assignment_id=assignment_id, graph_data=graph_data)


@app.route('/teacher_grade_submission/<int:user_id>/<int:assignment_id>', methods=['GET', 'POST'])
def teacher_grade_submission(user_id, assignment_id):
    if 'user_id' not in session:
        flash("Please log in to view and grade submissions", "warning")
        return redirect(url_for('login'))

    db = Database()
    submission_instance = Submission(db)

    submission_data = submission_instance.getSubmissionDetails(user_id, assignment_id)

    if not submission_data:
        flash("No submission found for this student.", "warning")
        return redirect(url_for('teacher_marksheet', assignment_id=assignment_id))

    submission_text = submission_data[0]
    current_mark = submission_data[1]
    current_grade = submission_data[2]

    if request.method == 'POST':
        new_mark = request.form.get('mark')
        new_grade = request.form.get('grade', '').strip().upper()

        # Validate inputs
        if not new_mark.isdigit() or not (0 <= int(new_mark) <= 100):
            flash("Mark must be a number between 0 and 100.", "error")
        elif new_grade not in ['A', 'B', 'C', 'D', 'E']:
            flash("Grade must be one of: A, B, C, D, or E.", "error")
        else:
            submission_instance.updateSubmissionGradeAndMark(user_id, assignment_id, int(new_mark), new_grade)
            flash("Mark and grade updated successfully!", "success")
            return redirect(url_for('teacher_marksheet', assignment_id=assignment_id))

    return render_template(
        'teacher_grade_submission.html',
        user_id=user_id,
        assignment_id=assignment_id,
        submission_text=submission_text,
        current_mark=current_mark,
        current_grade=current_grade
    )

app.config["UPLOAD_FOLDER"] = "simulation_results"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

simulation_progress = {"status": "idle", "progress": 0, "file": None}

def run_simulation(params):
    global simulation_progress

    grid_size_x = params["grid_size_x"]
    grid_size_y = params["grid_size_y"]
    num_time_steps = params["num_time_steps"]
    viscosity = params["viscosity"]
    rotation_angle = params["rotation_angle"]
    max_camber = params["max_camber"]
    camber_position = params["camber_position"] 
    max_thickness = params["max_thickness"]


    grid_spacing_x = 2 / (grid_size_x - 1)
    grid_spacing_y = 2 / (grid_size_y - 1) 
    time_step_size = 0.001 
    density = 1.0 

    # Generate airfoil coordinates (NACA 4-digit)
    airfoil_x, airfoil_y = generate_naca_airfoil(max_camber, camber_position, max_thickness, 1.0)
    airfoil_x = airfoil_x * 0.8 + 0.6  # Scale and translate
    airfoil_y = airfoil_y * 0.4 + 0.8
    airfoil_coords = np.column_stack((airfoil_x, airfoil_y))

    # Rotate airfoil about the center (1,1)
    center = np.array([1.0, 1.0])
    translated_coords = airfoil_coords - center  # Translate to origin
    rotation_angle_rad = np.radians(rotation_angle)  # Convert angle to radians
    rotation_matrix = np.array([
        [np.cos(rotation_angle_rad), -np.sin(rotation_angle_rad)],
        [np.sin(rotation_angle_rad), np.cos(rotation_angle_rad)]
    ])
    rotated_coords = translated_coords @ rotation_matrix.T  # Apply rotation
    rotated_coords += center  # Translate back to original center
    airfoil_coords = rotated_coords  # Update airfoil coordinates
    airfoil_path = Path(airfoil_coords)

    # Initialize velocity and pressure fields
    velocity_x = np.zeros((grid_size_y, grid_size_x))  # u (x-component of velocity)
    velocity_y = np.zeros((grid_size_y, grid_size_x))  # v (y-component of velocity)
    pressure = np.zeros((grid_size_y, grid_size_x))  # p (pressure)
    pressure_source_term = np.zeros((grid_size_y, grid_size_x))  # b (source term for pressure Poisson equation)

    output_dir = app.config["UPLOAD_FOLDER"]
    frames = []

    for time_step in range(num_time_steps):
        # Save previous time step velocities
        velocity_x_prev = velocity_x.copy()
        velocity_y_prev = velocity_y.copy()

        # Adjust time step size dynamically
        time_step_size = calculate_time_step(velocity_x, velocity_y, grid_spacing_x, grid_spacing_y)

        # Calculate the source term for the pressure equation
        # b = ρ * (∇ · (u · ∇u) + ∇ · (v · ∇v))
        pressure_source_term = calculate_pressure_source_term(
            pressure_source_term, velocity_x, velocity_y, grid_size_x, grid_size_y, grid_spacing_x, grid_spacing_y, time_step_size, density
        )

        # Solve the pressure Poisson equation
        # ∇²p = b
        pressure = solve_pressure_poisson(
            pressure, pressure_source_term, grid_size_x, grid_size_y, grid_spacing_x, grid_spacing_y, num_iterations=100
        )

        # Update velocity fields using the Navier-Stokes equations
        # ∂u/∂t + u · ∇u = -∇p/ρ + ν∇²u
        velocity_x[1:-1, 1:-1] = (
            velocity_x_prev[1:-1, 1:-1]
            - velocity_x_prev[1:-1, 1:-1] * time_step_size / grid_spacing_x * (velocity_x_prev[1:-1, 1:-1] - velocity_x_prev[1:-1, :-2])  # Convection term (u · ∇u)
            - velocity_y_prev[1:-1, 1:-1] * time_step_size / grid_spacing_y * (velocity_x_prev[1:-1, 1:-1] - velocity_x_prev[:-2, 1:-1])  # Convection term (v · ∇u)
            - time_step_size / (2 * density * grid_spacing_x) * (pressure[1:-1, 2:] - pressure[1:-1, :-2])  # Pressure gradient term (-∇p/ρ)
            + viscosity * (
                time_step_size / grid_spacing_x**2 * (velocity_x_prev[1:-1, 2:] - 2 * velocity_x_prev[1:-1, 1:-1] + velocity_x_prev[1:-1, :-2])  # Diffusion term (ν∇²u)
                + time_step_size / grid_spacing_y**2 * (velocity_x_prev[2:, 1:-1] - 2 * velocity_x_prev[1:-1, 1:-1] + velocity_x_prev[:-2, 1:-1])  # Diffusion term (ν∇²u)
            )
        )

        # ∂v/∂t + u · ∇v = -∇p/ρ + ν∇²v
        velocity_y[1:-1, 1:-1] = (
            velocity_y_prev[1:-1, 1:-1]
            - velocity_x_prev[1:-1, 1:-1] * time_step_size / grid_spacing_x * (velocity_y_prev[1:-1, 1:-1] - velocity_y_prev[1:-1, :-2])  # Convection term (u · ∇v)
            - velocity_y_prev[1:-1, 1:-1] * time_step_size / grid_spacing_y * (velocity_y_prev[1:-1, 1:-1] - velocity_y_prev[:-2, 1:-1])  # Convection term (v · ∇v)
            - time_step_size / (2 * density * grid_spacing_y) * (pressure[2:, 1:-1] - pressure[:-2, 1:-1])  # Pressure gradient term (-∇p/ρ)
            + viscosity * (
                time_step_size / grid_spacing_x**2 * (velocity_y_prev[1:-1, 2:] - 2 * velocity_y_prev[1:-1, 1:-1] + velocity_y_prev[1:-1, :-2])  # Diffusion term (ν∇²v)
                + time_step_size / grid_spacing_y**2 * (velocity_y_prev[2:, 1:-1] - 2 * velocity_y_prev[1:-1, 1:-1] + velocity_y_prev[:-2, 1:-1])  # Diffusion term (ν∇²v)
            )
        )

        # Apply boundary conditions
        apply_boundary_conditions(velocity_x, velocity_y, pressure, airfoil_path, grid_size_x, grid_size_y, grid_spacing_x, grid_spacing_y)

        # Visualize and save frame
        if time_step % 2 == 0:
            plt.figure(figsize=(11, 7), dpi=100)
            plt.contourf(np.linspace(0, 2, grid_size_x), np.linspace(0, 2, grid_size_y), pressure, alpha=0.5, cmap="viridis")
            plt.colorbar()
            plt.contour(np.linspace(0, 2, grid_size_x), np.linspace(0, 2, grid_size_y), pressure, cmap="viridis")
            plt.streamplot(np.linspace(0, 2, grid_size_x), np.linspace(0, 2, grid_size_y), velocity_x, velocity_y, color='black')

            airfoil_patch = patches.Polygon(airfoil_coords, linewidth=2, edgecolor="r", facecolor="none")
            plt.gca().add_patch(airfoil_patch)

            plt.xlabel("X")
            plt.ylabel("Y")
            plt.title(f"2D Cavity Flow with Airfoil (Step {time_step})")
            frame_path = os.path.join(output_dir, f"frame_{time_step:04d}.png")
            plt.savefig(frame_path)
            frames.append(imageio.imread(frame_path))
            plt.close()

        # Update progress
        simulation_progress["progress"] = (time_step / num_time_steps) * 100

    # Save animation as MP4
    mp4_path = os.path.join(output_dir, "cfd_simulation.mp4")
    imageio.mimsave(mp4_path, frames, fps=10)
    simulation_progress["status"] = "completed"
    simulation_progress["file"] = mp4_path

@app.route("/simulate", methods=["GET", "POST"])
def simulate():
    if request.method == "POST":
        # Get form inputs
        grid_size_x = int(request.form["grid_size_x"])
        grid_size_y = grid_size_x
        num_time_steps = int(request.form["num_time_steps"])
        viscosity = float(request.form["viscosity"])
        rotation_angle = float(request.form["rotation_angle"])

        naca_code = request.form.get("naca_code", "").strip()
        if not naca_code.isdigit() or len(naca_code) != 4:
            return jsonify({"status": "error", "message": "Invalid NACA code. Please provide a 4-digit number."})

        try:
            max_camber = int(naca_code[0]) / 100  # Maximum camber
            camber_position = int(naca_code[1]) / 10   # Location of max camber
            max_thickness = int(naca_code[2:]) / 100  # Maximum thickness
        except ValueError:
            return jsonify({"status": "error", "message": "Failed to parse NACA code."})

        simulation_progress.update({"status": "running", "progress": 0, "file": None})

        # Start the simulation in a separate thread
        threading.Thread(
            target=run_simulation,
            args=(
                {
                    "grid_size_x": grid_size_x,
                    "grid_size_y": grid_size_y,
                    "num_time_steps": num_time_steps,
                    "viscosity": viscosity,
                    "rotation_angle": rotation_angle,
                    "max_camber": max_camber,
                    "camber_position": camber_position,
                    "max_thickness": max_thickness,
                },
            ),
        ).start()

        return jsonify({"status": "started"})

    return render_template("simulate.html")

@app.route("/progress", methods=["GET"])
def progress():
    return jsonify(simulation_progress)

@app.route("/download", methods=["GET"])
def download():
    if simulation_progress["file"]:
        return send_file(simulation_progress["file"], as_attachment=True)
    return "No file available", 404

def generate_naca_airfoil(max_camber, camber_position, max_thickness, chord_length, num_points=100):
    x = np.linspace(0, chord_length, num_points)
    thickness_distribution = 5 * max_thickness * chord_length * (
        0.2969 * np.sqrt(x / chord_length)
        - 0.1260 * (x / chord_length)
        - 0.3516 * (x / chord_length) ** 2
        + 0.2843 * (x / chord_length) ** 3
        - 0.1015 * (x / chord_length) ** 4
    )
    camber_line = np.where(
        x <= camber_position * chord_length,
        max_camber * x / camber_position**2 * (2 * camber_position - x / chord_length),
        max_camber * (chord_length - x) / (1 - camber_position) ** 2 * (1 + x / chord_length - 2 * camber_position),
    )
    camber_slope = np.where(
        x <= camber_position * chord_length,
        2 * max_camber / camber_position**2 * (camber_position - x / chord_length),
        2 * max_camber / (1 - camber_position) ** 2 * (camber_position - x / chord_length),
    )
    angle = np.arctan(camber_slope)
    upper_surface_x = x - thickness_distribution * np.sin(angle)
    upper_surface_y = camber_line + thickness_distribution * np.cos(angle)
    lower_surface_x = x + thickness_distribution * np.sin(angle)
    lower_surface_y = camber_line - thickness_distribution * np.cos(angle)
    x_coords = np.concatenate([upper_surface_x[::-1], lower_surface_x[1:]])
    y_coords = np.concatenate([upper_surface_y[::-1], lower_surface_y[1:]])
    return x_coords, y_coords

def apply_boundary_conditions(velocity_x, velocity_y, pressure, airfoil_path, grid_size_x, grid_size_y, grid_spacing_x, grid_spacing_y):
    # Boundary conditions for velocity
    velocity_x[0, :] = 0  # Bottom wall
    velocity_x[-1, :] = 0  # Top wall
    velocity_x[:, 0] = 0   # Left wall
    velocity_x[:, -1] = 1  # Right wall (driven cavity)
    velocity_y[0, :] = 0   # Bottom wall
    velocity_y[-1, :] = 0  # Top wall
    velocity_y[:, 0] = 0   # Left wall
    velocity_y[:, -1] = 0  # Right wall

    # Boundary conditions for pressure
    pressure[-1, :] = pressure[-2, :]  # dp/dy = 0 at the top
    pressure[0, :] = pressure[1, :]    # dp/dy = 0 at the bottom
    pressure[:, -1] = pressure[:, -2]  # dp/dx = 0 at the right
    pressure[:, 0] = pressure[:, 1]    # dp/dx = 0 at the left

    # No-slip condition on the airfoil
    for i in range(grid_size_y):
        for j in range(grid_size_x):
            x = j * grid_spacing_x
            y = i * grid_spacing_y
            if airfoil_path.contains_point((x, y)):
                velocity_x[i, j] = 0
                velocity_y[i, j] = 0

def solve_pressure_poisson(pressure, pressure_source_term, grid_size_x, grid_size_y, grid_spacing_x, grid_spacing_y, num_iterations):
    for _ in range(num_iterations):
        pressure_prev = pressure.copy()
        pressure[1:-1, 1:-1] = (
            (
                (pressure_prev[1:-1, 2:] + pressure_prev[1:-1, :-2]) * grid_spacing_y**2
                + (pressure_prev[2:, 1:-1] + pressure_prev[:-2, 1:-1]) * grid_spacing_x**2
            )
            / (2 * (grid_spacing_x**2 + grid_spacing_y**2))
            - grid_spacing_x**2 * grid_spacing_y**2 / (2 * (grid_spacing_x**2 + grid_spacing_y**2)) * pressure_source_term[1:-1, 1:-1]
        )
        # Enforce boundary conditions for pressure
        pressure[-1, :] = pressure[-2, :]  # dp/dy = 0 at the top
        pressure[0, :] = pressure[1, :]    # dp/dy = 0 at the bottom
        pressure[:, -1] = pressure[:, -2]  # dp/dx = 0 at the right
        pressure[:, 0] = pressure[:, 1]    # dp/dx = 0 at the left
    return pressure

def calculate_pressure_source_term(pressure_source_term, velocity_x, velocity_y, grid_size_x, grid_size_y, grid_spacing_x, grid_spacing_y, time_step_size, density):
    pressure_source_term[1:-1, 1:-1] = (
        density
        * (
            (1 / time_step_size)
            * (
                (velocity_x[1:-1, 2:] - velocity_x[1:-1, :-2]) / (2 * grid_spacing_x)
                + (velocity_y[2:, 1:-1] - velocity_y[:-2, 1:-1]) / (2 * grid_spacing_y)
            )
            - ((velocity_x[1:-1, 2:] - velocity_x[1:-1, :-2]) / (2 * grid_spacing_x)) ** 2
            - 2
            * ((velocity_x[2:, 1:-1] - velocity_x[:-2, 1:-1]) / (2 * grid_spacing_y))
            * ((velocity_y[1:-1, 2:] - velocity_y[1:-1, :-2]) / (2 * grid_spacing_x))
            - ((velocity_y[2:, 1:-1] - velocity_y[:-2, 1:-1]) / (2 * grid_spacing_y)) ** 2
        )
    )
    return pressure_source_term

def calculate_time_step(velocity_x, velocity_y, grid_spacing_x, grid_spacing_y, cfl=0.5):
    max_velocity = max(np.max(np.abs(velocity_x)), np.max(np.abs(velocity_y)))
    return cfl * min(grid_spacing_x, grid_spacing_y) / max_velocity if max_velocity > 0 else 0.001

if __name__ == "__main__":
    app.run(debug=True)