import sqlite3

db_path = 'nea.db'
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS AssignmentData (
    AssignmentID    INTEGER PRIMARY KEY AUTOINCREMENT,
    Title           VARCHAR(50) NOT NULL,
    Task            TEXT NOT NULL,
    ClassName       VARCHAR(50) NOT NULL,
    FOREIGN KEY (ClassName) REFERENCES ClassContent(ClassName)
);              
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ClassContent (
    ClassName   VARCHAR(50) NOT NULL,
    UserID      INTEGER,
    FOREIGN KEY (UserID) REFERENCES UserData(UserID),
    PRIMARY KEY(ClassName, UserID)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS UserData (
    UserID          INTEGER PRIMARY KEY AUTOINCREMENT,
    Email           VARCHAR(320) NOT NULL,
    Forename        VARCHAR(50) NOT NULL,
    Surname         VARCHAR(50) NOT NULL,
    Password        VARCHAR(300) NOT NULL,
    Type            BOOLEAN NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS SubmissionDetails (
    SubmissionID    INTEGER PRIMARY KEY AUTOINCREMENT,
    SubmissionTime  DATE NOT NULL,
    SubmissionText  TEXT NOT NULL,
    SubmissionGrade CHAR(1),
    SubmissionMark  INTEGER,         
    UserID          INTEGER,
    AssignmentID    INTEGER,
    FOREIGN KEY (AssignmentID) REFERENCES AssignmentData(AssignmentID),     
    FOREIGN KEY (UserID) REFERENCES UserData(UserID)        
);
""")

connection.commit()
connection.close()
print(f"Database {db_path} has successfully been created!")