import sqlite3
import Create_Tables_D8
import bcrypt
import numpy as np

class Database:
    # connects the database with the queries
    def __init__(self, db_name='nea.db'):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.connection.row_factory = sqlite3.Row
    
    def execute(self, query, params = None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        self.connection.commit()
    
    def fetchall(self, query, params = None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def fetchone(self, query, params = None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchone()

    def close(self):
        self.connection.close()

class users:
    def __init__(self, db):
        self.db = db

    # adds a user if new email, stores hashed password.
    def addUser(self, Email, Forename, Surname, Password):
        query = '''
        SELECT * FROM UserData
        WHERE Email = ?
        '''
        flag = self.db.fetchone(query, (Email,))

        if flag:
            print("Email Already Exists")
            return False
        else:
            hashed_password = bcrypt.hashpw(Password.encode('utf-8'), bcrypt.gensalt())
            query = '''
            INSERT INTO UserData (Email, Forename, Surname, Password, Type)
            VALUES (?,?,?,?,False)
            '''
            self.db.execute(query, (Email, Forename, Surname, hashed_password,))
            print(f"{Email} User Added")
            return True

    # checks user credentials when log in
    def loginUser(self, email, password):
        query = '''
        SELECT UserID, Email, Forename, Surname, Password, Type
        FROM UserData
        WHERE Email = ?
        '''
        user = self.db.fetchone(query, (email,))

        if user:
            stored_hashed_password = user[4]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
                return user
        return None

    # used to tell teacher or student
    def getUserType(self, user_id):
        query = "SELECT Type FROM UserData WHERE UserID = ?"
        return self.db.fetchone(query, (user_id,))

    
class Teacher(users):
    #inherits from users
    def __init__(self, db):
        # initialising db in this class
        super().__init__(db)

    #polymorphism of addUser in users class. Used to add a teacher through admin.
    def addUser(self, Email, Forename, Surname, Password):
        query = '''
        SELECT * FROM UserData
        WHERE Email = ?
        '''
        flag = self.db.fetchone(query, (Email,))

        if flag:
            print("Email Already Exists")
            return False
        else:
            query = '''
            INSERT INTO UserData (Email, Forename, Surname, Password, Type)
            VALUES (?,?,?,?,True)
            '''
            self.db.execute(query, (Email, Forename, Surname, Password,))
            print(f"{Email} User Added")
            return True
    

    
class Classroom(Teacher):
    def __init__(self, db):
        self.db = db
    
    def classExists(self, class_name):
        query = "SELECT * FROM ClassContent WHERE ClassName = ?"
        return self.db.fetchone(query, (class_name,))

    # checks if a teacher is creating the class and that it is a new unique class name
    # before adding to the db
    def addClass(self, class_name, user_id):
        teacher_check = '''
        SELECT Type FROM UserData WHERE UserID = ? AND Type = 1
        '''
        is_teacher = self.db.fetchone(teacher_check, (user_id,))
        if not is_teacher:
            return {"success": False, "message": "Only teachers can create classes."}

        class_exists_query = '''
        SELECT * FROM ClassContent WHERE ClassName = ?
        '''
        class_exists = self.db.fetchone(class_exists_query, (class_name,))
        if class_exists:
            return {"success": False, "message": "Class already exists."}

        insert_class_query = '''
        INSERT INTO ClassContent (ClassName, UserID)
        VALUES (?, ?) 
        '''
        self.db.execute(insert_class_query, (class_name, user_id))
        return {"success": True, "message": f"Class '{class_name}' created successfully."}

    # Checks if the student is already in a class before adding the student to the class.    
    def addClassUsers(self, user_id, class_name):
        query = '''
        SELECT * FROM ClassContent
        WHERE UserID = ? AND ClassName = ?
        '''
        if self.db.fetchone(query, (user_id, class_name)):
            return False

        query = '''
        INSERT INTO ClassContent (UserID, ClassName)
        VALUES (?, ?)
        '''
        self.db.execute(query, (user_id, class_name))
        return True
    
    # returns classname, student count, latest assignment title
    def getDashboard(self, user_id):
        query = '''
        SELECT 
            ClassContent.ClassName AS classname,
            COUNT(DISTINCT UserData.UserID) AS student_count,
            AssignmentData.Title AS assignment_title
        FROM 
            ClassContent
        LEFT JOIN 
            UserData ON ClassContent.UserID = UserData.UserID
        LEFT JOIN 
            AssignmentData ON ClassContent.ClassName = AssignmentData.ClassName
        WHERE 
            ClassContent.UserID = ?
        GROUP BY 
            ClassContent.ClassName
        ORDER BY 
            ClassContent.ClassName;
        '''
        return self.db.fetchall(query, (user_id,))

    # returns total students in class
    def getTotalStudents(self):
        query = '''
        SELECT 
            ClassContent.ClassName, 
            COUNT(ClassContent.UserID) AS total_students
        FROM 
            ClassContent
        JOIN 
            UserData ON ClassContent.UserID = UserData.UserID
        WHERE 
            UserData.Type = 0
        GROUP BY 
            ClassContent.ClassName
        ORDER BY 
            ClassContent.ClassName;
        '''
        return self.db.fetchall(query)


class Assignment:
    def __init__(self, db):
        self.db = db

    def addAssignment(self, title, task, class_name):
        # Verifying if the class exists
        query = "SELECT * FROM ClassContent WHERE ClassName = ?"
        flag = self.db.fetchone(query, (class_name,))
        if not flag:
            return False, f"Class '{class_name}' does not exist."

        # Adding the assignment to db
        query = '''
        INSERT INTO AssignmentData (Title, Task, ClassName)
        VALUES (?, ?, ?)
        '''
        self.db.execute(query, (title, task, class_name))
        return True, f"Assignment '{title}' added to class '{class_name}'."
    
    # gets title and summary for assignment
    def getAssignmentDetails(self, assignment_id):
        query = '''
        SELECT Title, Task
        FROM AssignmentData
        WHERE AssignmentID = ?
        '''
        return self.db.fetchone(query, (assignment_id,))

    # gets assignemnt title
    def getAssignmentTitle(self, assignment_id):
        query = "SELECT Title FROM AssignmentData WHERE AssignmentID = ?"
        result = self.db.fetchone(query, (assignment_id,))
        return result[0] if result else None
    
    # returns all the assignments in a class
    def getAssignmentsForClass(self, class_name):
        query = '''
        SELECT AssignmentID, Title, Task
        FROM AssignmentData
        WHERE ClassName = ?
        '''
        return self.db.fetchall(query, (class_name,))
    
    # gets assignment id along with title and task
    def getAssignments(self, class_name):
        query = '''
        SELECT AssignmentID, Title, Task 
        FROM AssignmentData 
        WHERE ClassName = ?
        '''
        return self.db.fetchall(query, (class_name,))
    
    # finds an assignmment byu id
    def getAssignmentById(self, assignment_id):
        query = '''
        SELECT Title, Task, ClassName 
        FROM AssignmentData 
        WHERE AssignmentID = ?
        '''
        result = self.db.fetchone(query, (assignment_id,))
        if result:
            return {
                "Title": result[0],
                "Task": result[1],
                "ClassName": result[2]
            }
        return None

class Submission:
    def __init__(self, db):
        self.db = db

    # Adds a new submission to the db
    def addSubmission(self, submission_time, submission_text, user_id, assignment_id):
        query = '''
        INSERT INTO SubmissionDetails (SubmissionTime, SubmissionText, UserID, AssignmentID)
        VALUES (?, ?, ?, ?)
        '''
        try:
            self.db.execute(query, (submission_time, submission_text, user_id, assignment_id))
            return True
        except Exception as e:
            print(f"Error adding submission: {e}")
            return False
        
    # Gets submissions based on assignment ID and/or user ID.
    # Returns submissions filtered by assignment, user, or all if no filters are provided.
    def getSubmissions(self, assignment_id=None, user_id=None):
        if assignment_id and user_id:
            query = '''
            SELECT SubmissionID, SubmissionText, SubmissionMark, SubmissionGrade, SubmissionTime
            FROM SubmissionDetails
            WHERE AssignmentID = ? AND UserID = ?
            '''
            return self.db.fetchone(query, (assignment_id, user_id))
        elif assignment_id:
            query = '''
            SELECT SubmissionID, SubmissionText, SubmissionMark, SubmissionGrade, SubmissionTime
            FROM SubmissionDetails
            WHERE AssignmentID = ?
            '''
            return self.db.fetchall(query, (assignment_id,))
        elif user_id:
            query = '''
            SELECT SubmissionID, SubmissionText, SubmissionMark, SubmissionGrade, SubmissionTime
            FROM SubmissionDetails
            WHERE UserID = ?
            '''
            return self.db.fetchall(query, (user_id,))
        else:
            # Fetches all submissions if no filters are provided
            query = '''
            SELECT SubmissionID, SubmissionText, SubmissionMark, SubmissionGrade, SubmissionTime
            FROM SubmissionDetails
            '''
            return self.db.fetchall(query)
    
    # Gets the total number of submissions for an assignment
    def getSubmissionCount(self, assignment_id):
        query = '''
        SELECT COUNT(DISTINCT SubmissionID)
        FROM SubmissionDetails
        WHERE AssignmentID = ?
        '''
        result = self.db.fetchone(query, (assignment_id,))
        return result[0] if result else 0
    
    # gets the latest submission time for an assignment
    def getLatestSubmissionTime(self, assignment_id):
        query = '''
        SELECT MAX(SubmissionTime)
        FROM SubmissionDetails
        WHERE AssignmentID = ?
        '''
        result = self.db.fetchone(query, (assignment_id,))
        return result[0] if result else None

    # Gets the data for an assignment, including student names and grades
    def getMarksheet(self, assignment_id):
        query = '''
        SELECT 
            UserData.UserID, 
            UserData.Forename || ' ' || UserData.Surname AS StudentName,
            SubmissionDetails.SubmissionText,
            SubmissionDetails.SubmissionMark,
            SubmissionDetails.SubmissionGrade,
            SubmissionDetails.SubmissionTime
        FROM UserData
        LEFT JOIN SubmissionDetails ON UserData.UserID = SubmissionDetails.UserID
        WHERE SubmissionDetails.AssignmentID = ?
        '''
        return self.db.fetchall(query, (assignment_id,))

    # Gets a submission, given a user and assignment
    def getUserSubmission(self, user_id, assignment_id):
        query = '''
        SELECT SubmissionText
        FROM SubmissionDetails
        WHERE AssignmentID = ? AND UserID = ?
        '''
        return self.db.fetchone(query, (assignment_id, user_id))
    
    # Gets all submissions for an assignment with student details
    def getSubmissionForAssignment(self, assignment_id):
        query = '''
        SELECT UserData.UserID, UserData.Forename || ' ' || UserData.Surname AS UserName,
               SubmissionDetails.SubmissionMark, SubmissionDetails.SubmissionGrade, 
               SubmissionDetails.SubmissionTime
        FROM SubmissionDetails
        JOIN UserData ON SubmissionDetails.UserID = UserData.UserID
        WHERE AssignmentID = ?
        '''
        return self.db.fetchall(query, (assignment_id,))
    
    # gets submissions made by a user for assignments in a class
    def getSubmissionsInClass(self, user_id, class_name):  
        query = '''
        SELECT AssignmentID, SubmissionMark, SubmissionGrade, SubmissionText, SubmissionTime
        FROM SubmissionDetails
        WHERE UserID = ? AND AssignmentID IN (
            SELECT AssignmentID FROM AssignmentData WHERE ClassName = ?
        )
        '''
        return self.db.fetchall(query, (user_id, class_name))
    
    # gets grades and marks for a user in a class
    def getGradesAndMarks(self, class_name, user_id):    
        query = '''
        SELECT AssignmentData.Title, SubmissionDetails.SubmissionMark, SubmissionDetails.SubmissionGrade
        FROM SubmissionDetails
        JOIN AssignmentData ON AssignmentData.AssignmentID = SubmissionDetails.AssignmentID
        WHERE AssignmentData.ClassName = ? AND SubmissionDetails.UserID = ?
        '''
        return self.db.fetchall(query, (class_name, user_id))

    # gets all submissions made by a user
    def getUserSubmissions(self, user_id):
        query = '''
        SELECT 
            AssignmentData.Title, 
            SubmissionDetails.SubmissionMark, 
            SubmissionDetails.SubmissionGrade, 
            SubmissionDetails.SubmissionText, 
            SubmissionDetails.SubmissionTime
        FROM SubmissionDetails
        JOIN AssignmentData ON AssignmentData.AssignmentID = SubmissionDetails.AssignmentID
        WHERE SubmissionDetails.UserID = ?
        ORDER BY SubmissionDetails.SubmissionTime ASC
        '''
        return self.db.fetchall(query, (user_id,))

    # gets all submissions for anm assignment, including student details
    def getAssignmentSubmissions(self, assignment_id):
        query = '''
        SELECT 
            UserData.UserID, 
            UserData.Forename || ' ' || UserData.Surname AS UserName,
            SubmissionDetails.SubmissionMark,
            SubmissionDetails.SubmissionGrade,
            SubmissionDetails.SubmissionTime
        FROM SubmissionDetails
        JOIN UserData ON SubmissionDetails.UserID = UserData.UserID
        WHERE SubmissionDetails.AssignmentID = ?
        '''
        return self.db.fetchall(query, (assignment_id,))
    
    # gets grades and marks for a user across all assignments
    def getUserGradeAndMarks(self, user_id):
        query = '''
        SELECT 
            AssignmentData.Title, 
            SubmissionDetails.SubmissionMark, 
            SubmissionDetails.SubmissionGrade, 
            SubmissionDetails.SubmissionTime
        FROM SubmissionDetails
        JOIN AssignmentData ON AssignmentData.AssignmentID = SubmissionDetails.AssignmentID
        WHERE SubmissionDetails.UserID = ?
        ORDER BY SubmissionDetails.SubmissionTime ASC
        '''
        return self.db.fetchall(query, (user_id,))

    # gets grades and marks for all submissions of an assignment
    def getAssignmentGradesAndMarks(self, assignment_id):
        query = '''
        SELECT 
            UserData.Forename || ' ' || UserData.Surname AS UserName,
            SubmissionDetails.SubmissionMark,
            SubmissionDetails.SubmissionGrade,
            SubmissionDetails.SubmissionTime
        FROM SubmissionDetails
        JOIN UserData ON SubmissionDetails.UserID = UserData.UserID
        WHERE SubmissionDetails.AssignmentID = ?
        ORDER BY SubmissionDetails.SubmissionTime ASC
        '''
        return self.db.fetchall(query, (assignment_id,))

    # gets submission details for a user and assignment
    def getSubmissionDetails(self, user_id, assignment_id):
        query = '''
        SELECT 
            SubmissionDetails.SubmissionText,
            SubmissionDetails.SubmissionMark,
            SubmissionDetails.SubmissionGrade
        FROM SubmissionDetails
        WHERE SubmissionDetails.UserID = ? AND SubmissionDetails.AssignmentID = ?
        '''
        return self.db.fetchone(query, (user_id, assignment_id))

    # Updates the grade and mark for a user's submission for anm assignment
    def updateSubmissionGradeAndMark(self, user_id, assignment_id, new_mark, new_grade):
        query = '''
        UPDATE SubmissionDetails
        SET SubmissionMark = ?, SubmissionGrade = ?
        WHERE UserID = ? AND AssignmentID = ?
        '''
        self.db.execute(query, (new_mark, new_grade, user_id, assignment_id))


class Sorting:
    #Takes a list of assignments to sort
    @staticmethod
    def merge_sort_assignments(assignments, key):
        # Base case: it is already sorted
        if len(assignments) <= 1:
            return assignments

        mid = len(assignments) // 2
        left = Sorting.merge_sort_assignments(assignments[:mid], key) 
        # Recursively sort the left half
        right = Sorting.merge_sort_assignments(assignments[mid:], key)
        # Recursively sort the right half
        
        #merge
        return Sorting._merge(left, right, key)

    @staticmethod
    def _merge(left, right, key):
        merged = []
        i = 0
        j = 0
        
        # Comparing elements from both lists and append the smaller one
        while i < len(left) and j < len(right):
            if left[i][key] <= right[j][key]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1

        merged.extend(left[i:])
        merged.extend(right[j:])

        return merged

    # reverse to maek descending
    @staticmethod
    def reverse_assignments(assignments):
        return assignments[::-1]

    @staticmethod
    def predict_grade(grades):
        num_grades = len(grades)
        if num_grades == 0:
            return None

        # Weight calculations for recent grades (higher weight for recent grades)
        weights = []
        for i in range(num_grades):
            if i >= num_grades - 10:
                weight = 1 / (1 + (num_grades - i - 1))
            else:
                weight = 1 / 11  # Constant weight for older grades
            weights.append(weight)

        # Anomaly detection so removing grades more than 2 standard deviations from the mean
        mean_grade = np.mean(grades)
        std_dev_grade = np.std(grades)
        used_grades = []
        filtered_weights = []

        for grade, weight in zip(grades, weights):
            if abs(grade - mean_grade) <= 2 * std_dev_grade:
                used_grades.append(grade)
                filtered_weights.append(weight)

        # Calculate weighted average
        if used_grades:
            weighted_sum = sum(grade * weight for grade, weight in zip(used_grades, filtered_weights))
            total_weight = sum(filtered_weights)
            return weighted_sum / total_weight
        return None

    @staticmethod 
    def validate_password(password):
        has_upper = False
        has_lower = False
        has_digit = False
        has_symbol = False
        symbols = "!@#$%^&*(),.?\":{}|<>"
        # Flags for password validity check

        if len(password) < 8:
            return False, "Password must be 8 characters or longer."

        for char in password:
            if char.isupper():
                has_upper = True
            elif char.islower():
                has_lower = True
            elif char.isdigit():
                has_digit = True
            elif char in symbols:
                has_symbol = True

        if not has_upper:
            return False, "Password must contain at least one uppercase letter."
        if not has_lower:
            return False, "Password must contain at least one lowercase letter."
        if not has_digit:
            return False, "Password must contain at least one number."
        if not has_symbol:
            return False, "Password must contain at least one symbol."
        return True, ""
        # error messages for when password is not up to spec