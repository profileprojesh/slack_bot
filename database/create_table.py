import json
import psycopg2
from database.db import Db

db = Db()
cur = db.connect()


def create_daily_survey_table():

    query="""
        CREATE TABLE daily_survey(
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            question_id SERIAL NOT NULL,
            answer VARCHAR(50) NOT NULL,
            answered_datetime TIMESTAMP DEFAULT current_timestamp,
            CONSTRAINT fk_question FOREIGN KEY(question_id) REFERENCES question(id) ON DELETE CASCADE
        );
        """
        
    try:
        y=cur.execute(query)
        db.commit()
        print("Daily survey created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


def create_leave_table():

    query="""
        CREATE TABLE employee_leave (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            leave_start_date DATE NOT NULL,
            leave_end_date DATE NOT NULL,
            remarks VARCHAR(300),
            leave_days INT NOT NULL,
            UNIQUE (user_id, leave_start_date)
        );
        """
        
    try:
        y=cur.execute(query)
        db.commit()
        print("Employee leave created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


def create_question_table():
    query = """
        CREATE TABLE question (
            id SERIAL PRIMARY KEY,
            text VARCHAR(255) UNIQUE NOT NULL,
            type VARCHAR(50) NOT NULL,
            action_id VARCHAR(50) NOT NULL,
            option JSON
        );
        """
    try:
        y=cur.execute(query)
        db.commit()
        print("Question table Created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


def insert_question():
    option_json = {
            "0": "No",
            "1": "Yes",
            "2": "Maybe",
        }
    questions = [
        ("Will you be working from home, today?", "radio_buttons", "radio_buttons-action", json.dumps(option_json)),
        ("Are you Fine today?", "radio_buttons", "radio_buttons-fine", json.dumps(option_json)),
    ]
    query = """INSERT INTO question (text, type, action_id, option)
                VALUES(%s,%s,%s,%s) RETURNING id;"""
    x = cur.executemany(query, questions)
    db.commit()
    print("Questions added")
    

if __name__ =="__main__":
    create_question_table()
    create_daily_survey_table()
    insert_question()
    create_leave_table()