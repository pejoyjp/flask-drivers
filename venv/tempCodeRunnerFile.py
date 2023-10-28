# @app.route("/listdrivers")
# def listdrivers():
#     connection = getCursor()
#     connection.execute("SELECT * FROM driver;")
#     driverList = connection.fetchall()
#     print(driverList)
#     return render_template("driverlist.html", driver_list = driverList)    
