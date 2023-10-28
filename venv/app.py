from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from mysql.connector import FieldType
import connect

app = Flask(__name__, template_folder="templates")

dbconn = None
connection = None

def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user=connect.dbuser, \
    password=connect.dbpass, host=connect.dbhost, \
    database=connect.dbname, autocommit=True)
    dbconn = connection.cursor()
    return dbconn


@app.route("/")
def listdrivers():
    connection = getCursor()
    search_query = request.args.get("search")
    sql_query = """
    SELECT driver.driver_id, first_name, surname, model, drive_class, age 
    FROM driver 
    LEFT JOIN car ON driver.car = car.car_num 
    {}
    ORDER BY surname, first_name;
    """
    if search_query:
        connection.execute(sql_query.format("WHERE CONCAT(first_name, ' ', surname) LIKE %s"), ("%" + search_query + "%",))
    else:
        connection.execute(sql_query.format(""))
    driverList = connection.fetchall()
    return render_template("user/driverlist.html", driver_list=driverList)

@app.route("/admin")
def admin():
    cursor = getCursor()
    search_query = request.args.get("search")
    sql_query = """
    SELECT d.driver_id, d.first_name, d.surname, d.age, 
           c.first_name AS caregiver_first_name, c.surname AS caregiver_surname
    FROM driver d
    LEFT JOIN driver c ON d.caregiver = c.driver_id
    WHERE d.age < 18
    ORDER BY d.age DESC, d.surname;
    """
    cursor.execute(sql_query)
    junior_drivers = cursor.fetchall()
    if search_query:
        junior_drivers = [driver for driver in junior_drivers if search_query.lower() in driver['first_name'].lower() or search_query.lower() in driver['surname'].lower()]
    return render_template("admin/admin.html", junior_drivers=junior_drivers, search_query=search_query)

@app.route("/edit_runs", methods=["GET", "POST"])
def edit_runs():
    cursor = getCursor()

    cursor.execute("SELECT driver_id, first_name, surname FROM driver ORDER BY age DESC, surname;")
    junior_drivers = cursor.fetchall()

    cursor.execute("SELECT course_id, name FROM course;")
    courses = cursor.fetchall()

    if request.method == "GET":
        return render_template("admin/edit_runs.html", junior_drivers=junior_drivers, courses=courses)

    elif request.method == "POST":
        driver_id = request.form.get("driver_id")
        course_id = request.form.get("course_id")
        run_num = request.form.get("run_num")

        if driver_id:
        
            cursor.execute("""
                SELECT seconds, cones, wd
                FROM run
                WHERE dr_id = %s AND crs_id = %s AND run_num = %s
            """, (driver_id, course_id, run_num))
            run_details = cursor.fetchone()

            existing_seconds, existing_cones, existing_wd = run_details

            seconds = request.form.get("seconds", existing_seconds)
            cones = request.form.get("cones", existing_cones)
            wd = 1 if request.form.get("wd") else 0  

            sql_query = """
                UPDATE run
                SET seconds = %s, cones = %s, wd = %s
                WHERE dr_id = %s AND crs_id = %s AND run_num = %s
            """
            cursor.execute(sql_query, (seconds, cones, wd, driver_id, course_id, run_num))
            connection.commit()

    

        else:
            return "Please select a driver or a course"

        return redirect("/edit_runs")

@app.route("/add_driver", methods=["GET", "POST"])
def add_driver():
    global connection
    cursor = getCursor()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        surname = request.form.get("surname")
        car_num = request.form.get("car_num")
    
        age = request.form.get("age")
        caregiver = request.form.get("caregiver")
        date_of_birth = request.form.get("date_of_birth")
     

        print(first_name,surname,car_num,age,caregiver,date_of_birth )
        
    
        cursor.execute("""
            INSERT INTO driver (first_name, surname, age, car, caregiver) VALUES (%s, %s, %s, %s, %s);
        """, (first_name, surname, age, car_num, caregiver))

        return redirect("/admin")
        

    elif request.method == "GET":
        cursor.execute("SELECT car_num, model FROM car;")
        cars = cursor.fetchall()
        cursor.execute("SELECT driver_id, CONCAT(first_name, ' ', surname) AS full_name FROM driver WHERE age < 18;")
        caregivers = cursor.fetchall()
        return render_template("admin/add_driver.html", cars=cars, caregivers=caregivers)



@app.route("/results")
def results():
    cursor = getCursor()  

    sql_query = """
        SELECT 
            d.driver_id, 
            d.first_name, 
            d.surname, 
            c.model, 
            d.age,
            SUM(CASE WHEN r.crs_id = 'A' THEN r.seconds ELSE NULL END) as course1,
            SUM(CASE WHEN r.crs_id = 'B' THEN r.seconds ELSE NULL END) as course2,
            SUM(CASE WHEN r.crs_id = 'C' THEN r.seconds ELSE NULL END) as course3,
            SUM(CASE WHEN r.crs_id = 'D' THEN r.seconds ELSE NULL END) as course4,
            SUM(CASE WHEN r.crs_id = 'E' THEN r.seconds ELSE NULL END) as course5,
            SUM(CASE WHEN r.crs_id = 'F' THEN r.seconds ELSE NULL END) as course6,
            SUM(r.seconds) as overall,
            CASE 
                WHEN SUM(CASE WHEN r.crs_id IN ('A', 'B', 'C', 'D', 'E', 'F') THEN 1 ELSE 0 END) = 6 THEN 1
                ELSE 0
            END AS is_qualified
        FROM driver d
        JOIN car c ON d.car = c.car_num
        LEFT JOIN run r ON d.driver_id = r.dr_id
        GROUP BY d.driver_id, d.first_name, d.surname, c.model, d.age
        ORDER BY is_qualified DESC, overall DESC;

    """
    
    cursor.execute(sql_query)
    results = cursor.fetchall()
    
    cursor.close() 

    return render_template("user/results.html", results=results, rank_to_medal=rank_to_medal)





@app.route("/listcourses")
def listcourses():
    connection = getCursor()
    connection.execute("SELECT * FROM course;")
    courseList = connection.fetchall()
    return render_template("user/listcourse.html", course_list=courseList)

@app.route("/driverdetails/<int:driver_id>")
def show_driver_details(driver_id):
    connection = getCursor()
    connection.execute("SELECT * FROM driver WHERE driver_id = %s", (driver_id,))
    driver = connection.fetchone()
    connection.execute("SELECT SUM(seconds) FROM run WHERE dr_id = %s", (driver_id,))
    total_runtime = connection.fetchone()[0]
    connection.execute("SELECT crs_id, run_num, seconds, cones, wd FROM run WHERE dr_id = %s", (driver_id,))
    run_info = connection.fetchall()
    return render_template("user/driverDetails.html", driver=driver, runtime=total_runtime, run_info=run_info)


@app.route("/graph")
def showgraph():
    cursor = getCursor()
    
    sql_query = """
        SELECT 
            d.driver_id, 
            CONCAT(d.driver_id, ' ', d.first_name, ' ', d.surname) AS driver_name, 
            SUM(r.seconds) as overall
        FROM driver d
        JOIN run r ON d.driver_id = r.dr_id
        GROUP BY d.driver_id, d.driver_id, d.first_name, d.surname
        ORDER BY overall DESC
        LIMIT 5;
    """
    
    cursor.execute(sql_query)
    top_drivers = cursor.fetchall()
    
    bestDriverList = [driver[1] for driver in top_drivers]
    resultsList = [driver[2] for driver in top_drivers]
    
    return render_template("top5graph.html", name_list=bestDriverList, value_list=resultsList)

def rank_to_medal(index):
    medals = {1: "🏆", 2: "🥈", 3: "🥉"}
    return medals.get(index, str(index))


if __name__ == '__main__':
    app.run()

