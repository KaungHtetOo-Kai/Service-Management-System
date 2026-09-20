import os
import sqlite3

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, jsonify, url_for
from flask_session import Session
from hashids import Hashids
from werkzeug.security import check_password_hash,generate_password_hash
from datetime import datetime

from helpers import generate_sequence_id, login_required,map_position, map_department, not_found

# Configure APP
app = Flask(__name__)
hashids = Hashids(salt="service-management-system", min_length=6)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///ServiceManagementSystem.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login", methods = ["GET", "POST"])
def login():

    # forget any user_id
    session.clear()
    if request.method == "POST":
        staff_id = request.form.get("staff_id")
        password = request.form.get("password")

        # validation(blank input)
        if not staff_id or not password:
            return jsonify({"status":"error" , "message":"Field must not be empty!!!"}),400
        
        user = db.execute(
            "SELECT * FROM employee WHERE staff_id = :staff_id AND active = 1",
            staff_id = staff_id
        )

        # for first time, user creation for employee table. 
        # comment everytime at normal use.
        # db.execute(
        #     "INSERT INTO employee (staff_id, hash, name, position, department, center_id) VALUES (:staff_id, :hash, :name, :position, :department, :center_id)",
        #     staff_id = staff_id,
        #     hash = generate_password_hash(password),
        #     name = staff_id,
        #     position = staff_id,
        #     department = staff_id,
        #     center_id = "SC-000"
        # )

        # validation(invalid staff_id)
        if len(user) != 1:
            return jsonify({"status": "error", "message": "Staff ID does not exit!!!"}), 400

        # validation(invalid password)
        if not check_password_hash(user[0]["hash"], password):
            return jsonify({"status": "error","message": "Password do not match!!!"}),400
        
        # log in user
        session["user_id"] = user[0]["id"]
        session["user_role"] = user[0]["position"]
        session["center_id"] = user[0]["center_id"]
        return jsonify({"status": "success", "message": "success","redirect": "/"}), 200

    # get method   
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/employee")
@login_required
def employee():
    # get total employee form database
    total_emp = db.execute(
        "SELECT position, COUNT(*) as count FROM employee WHERE active = '1' GROUP BY position"
    )

    # get service center name to inject at service_center search bar
    centers = db.execute(
        "SELECT center_id, name FROM service_centers WHERE active = 1"
    )

    # position and department fields are hard-coded from backend,
    # position values are department values are stored as a map in a method inside helper.py
    # if we want to add or edit the postion, backend implementation will be needed.
    # calculation of total employee
    total_MGR = 0
    total_ENG = 0
    total_REC = 0
    total_STR = 0

    total_count = sum(row['count'] for row in total_emp)
    for row in total_emp:
        position = row["position"]
        count = row["count"]

        if position == "1":
            total_MGR = count
        
        if position == "2":
            total_ENG = count
        
        if position == "3":
            total_REC = count

        if position == "4":
            total_STR = count
    
    return render_template("employee.html", total_count = total_count, total_MGR = total_MGR, total_ENG = total_ENG, total_REC = total_REC, total_STR = total_STR, centers = centers)

@app.route("/more_detail/")
@login_required
def more_detail():
    # 1. 'staff_id' to 'id' to exactly match JavaScript fetch URL (?id=...)
    staff_id = request.args.get('id')
    
    if not staff_id:
        return jsonify({"status": "error", "message": "Missing employee ID reference."}), 400

    # 2. Run the database query
    rows = db.execute(
        "SELECT staff_id, NRC, father_name, address, phone FROM employee WHERE staff_id = :staff_id",
        staff_id = staff_id
    )

    # 3. Verify if the employee actually exists in SQLite table
    if not rows:
        return jsonify({"status": "error", "message": f"Employee {staff_id} not found."}), 404

    # 4. Extract the first dictionary row element from the list
    employee_row = rows[0]

    # 5. Map the keys cleanly so they line up with JS showModal mapping keys
    formatted_employee = {
        "id": employee_row["staff_id"],
        "NRC": employee_row["NRC"],
        "phone": employee_row["phone"],
        "father_name": employee_row["father_name"],
        "address": employee_row["address"]
    }

    # 6. Changed "emp-data" string to the live formatted_employee object variable
    return jsonify({
        "status": "More Details", 
        "message": "", 
        "employee": formatted_employee
    }), 200


@app.route("/employee_create", methods = ["GET", "POST"])
@login_required
def employee_create():

    """ Create Employee """
    if request.method == "POST":
        # check which button was chcked
        action = request.form.get("action")

        # create button
        if action == "employee_create":
            staff_id = request.form.get("staff_id")
            hash = generate_password_hash(request.form.get("password"))
            name = request.form.get("name")
            position = request.form.get("position")
            department = request.form.get("department")
            center_id = request.form.get("center_id")
            NRC = request.form.get("NRC")
            father_name = request.form.get("father_name")
            address = request.form.get("address")
            phone = request.form.get("phone")

            # check the input empty
            if not staff_id or not hash or not name or not position or not department or not center_id:
                return jsonify({"status":"error","message":"Required values are missing. Check required fields again!!!"}),400

            
            # if position was edited form frontend somehow, throw exception
            if position is None:
                return jsonify({"status":"error","message":"Position values are invalid!!!"}),400

            # if department was edited form frontend somehow, throw exception
            if department is None:
                return jsonify({"status":"error","message":"Department values are invalid!!!"}),400

            # preventing not to insert other values than empty string if user does not input unrequired fields
            if not NRC:
                NRC = ""
            
            if not father_name:
                father_name = ""
            
            if not address:
                address = ""
            
            if not phone:
                phone = ""

            # update database and check unique staff_id validation
            try:
                db.execute(
                    "INSERT INTO employee (staff_id, hash, name, position, department, center_id, NRC, father_name, address, phone)" \
                    " VALUES (:staff_id, :hash, :name, :position, :department, :center_id, :NRC, :father_name, :address, :phone)",
                    staff_id = staff_id,
                    hash = hash,
                    name = name,
                    position = position,
                    department = department,
                    center_id = center_id,
                    NRC = NRC,
                    father_name = father_name,
                    address = address,
                    phone = phone
                    )
                
                return jsonify ({"status":"success","message":f"Employee'{staff_id}'was created"}),200
            
            except Exception as error:

                # catch error string
                error_msg = str(error).lower()

                # staff_id validation
                if "unique" in error_msg or "constraint" in error_msg:
                    return jsonify({"status": "error","message": "Staff_id is already exists"}),400
                
                # other unknown database error
                else:
                    return jsonify({"status": "error","message": "Unknown datatbase occured. Please contact Admin!!!"}),500

        # Handle cases where action is NOT "create"
        else:
            return jsonify({"status": "error", "message": f"Invalid form action: '{action}' submitted."}), 400

    # get method  
    else:
        centers = db.execute(
            "SELECT center_id, name from service_centers"
        )
        return render_template("employee_create.html", centers = centers)

@app.route("/search_employees/")
@login_required
def search_employees():
    """ Search employee """
    try:
        # 1. Grab pagination filters (Defaults to Page 1, Limit 10 items)
        page = int(request.args.get('page', 1))
        per_page = 10
        offset = (page - 1) * per_page

        # 2. Extract the 6 filtering text strings precisely as before
        staff_id = request.args.get('staff_id', '').strip()
        name = request.args.get('name', '').strip()
        position = request.args.get('position', '').strip()
        center_id = request.args.get('center_id', '').strip()
        department = request.args.get('department', '').strip()
        phone = request.args.get('phone', '').strip()
        active = request.args.get('active', '').strip()

        # 3. Define strict base JOIN query constraints matching active states
        base_joins = """
            FROM employee e 
            INNER JOIN service_centers s ON e.center_id = s.center_id 
            WHERE e.active = :active
        """
        
        # Build dynamic where condition filters dictionary
        where_clauses = ""
        params = {}
        params['active'] = active

        if staff_id:
            where_clauses += " AND e.staff_id = :staff_id"
            params['staff_id'] = staff_id
        if name:
            where_clauses += " AND e.name LIKE :name"
            params['name'] = f"%{name}%"
        if position:
            where_clauses += " AND e.position = :position"
            params['position'] = position
        if center_id:
            where_clauses += " AND e.center_id = :center_id"
            params['center_id'] = center_id
        if department:
            where_clauses += " AND e.department = :department"
            params['department'] = department
        if phone:
            where_clauses += " AND e.phone LIKE :phone"
            params['phone'] = f"%{phone}%"

        # 4. QUERY A: Calculate the total counts for the pagination metadata limits
        count_query = f"SELECT COUNT(*) as total {base_joins} {where_clauses}"
        count_result = db.execute(count_query, **params)
        
        # Extract the total counts safely out of result dictionary lists
        total_records = count_result[0]['total'] if isinstance(count_result, list) else count_result['total']
        
        # Derive math boundary requirements safely
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        # 5. QUERY B: Fetch only the targeted 10 rows matching page tracking boundaries
        data_query = f"""
            SELECT e.id, e.staff_id, e.name, e.position, e.center_id, s.name AS center_name, e.department, e.phone 
            {base_joins} {where_clauses} 
            LIMIT :limit OFFSET :offset
        """
        params['limit'] = per_page
        params['offset'] = offset
        rows = db.execute(data_query, **params)

        # Convert database row objects into a standard JSON-serializable list
        employees_list = []
        for row in rows:
            # --- BACKEND MAP RESOLUTION FIREWALL (SAFE & SECURE) ---
            # Call pre-existing helper functions passing the raw database values
            # This completely masks the digits 1, 2, 3, 4 from ever reaching the frontend
            readable_position = map_position(str(row["position"]))
            readable_department = map_department(str(row["department"]))

            employees_list.append({
                "id": row["id"],
                "staff_id": row["staff_id"],
                "name": row["name"],
                "center_id" : row["center_id"],
                "position": readable_position,       # Sends clean text "Manager" instead of "1"
                "center_name": row["center_name"],
                "department": readable_department,   # Sends clean text "Finance Department" instead of "3"
                "phone": row["phone"]
            })

        return jsonify({
            "status": "success",
            "employees": employees_list,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_records": total_records
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Query fault: {str(e)}"}), 500
    
@app.route("/employee_edit/", methods = ["GET", "POST"])
@login_required
def employee_edit():
    """ Edit employee """
    if request.method == "POST":
        action = request.form.get("action")
        id = request.args.get("id")
        staff_id = request.form.get("staff_id")

        emp = db.execute(
            "SELECT id FROM employee WHERE id = :id",
            id = id
        )

        if not emp:
            return not_found("/employee", "Employee")   

        # inactive action
        if action == "inactive":
            db.execute(
                "UPDATE employee SET active = 0 WHERE id = :id",
                id = id
            )

            # return success 
            return jsonify({
                "status": "success",
                "message": f"Staff_id {staff_id} profile status successfully modified to Inactive.",
                "redirect": "/employee"
            }), 200
        
        # edit_employee action
        if action == "edit":

            # get required data from frontend to validate
            old_password = request.form.get("old_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")
            position = request.form.get("position")
            department = request.form.get("department")
            center_id = request.form.get("center_id")

            # get employee data for database to validate
            row = db.execute(
                "SELECT * FROM employee WHERE id = :id",
                id = id
            )

            emp = row[0]

            # Staff_id Validation
            if session.get("user_id") == emp["id"]:
                return jsonify({
                    "status" : "error",
                    "message" : "Cannot edit your own status. Use Account page to edit",
                    "redirect": "/account"
                }), 400
            
            # Check for the admin account not to change postion, department and service center
            if "admin" in emp["staff_id"]:
                if position != "Admin" or department != "Admin":
                    return jsonify({
                        "status" : "error",
                        "message" : "Cannot edit position and department for Admin account",
                        "redirect": "/employee"
                    }), 400
            
            # position validation for admin (admin must be admin deapartment)
            if position == "0":
                department = "0"
            
            # password validation
            if old_password or new_password or confirm_password:
                if not check_password_hash(emp["hash"], old_password):
                    return jsonify({
                        "status" : "error",
                        "message" : "Old Password do not match",
                        "redirect": "/employee"
                    }), 400

                if old_password == new_password:
                    return jsonify({
                        "status" : "error",
                        "message" : "Old Password and New Password must not be same",
                        "redirect": "/employee"
                    }), 400

                if not str(new_password) == str(confirm_password):
                    return jsonify({
                        "status" : "error",
                        "message" : "New Password and Confirm Password do not match",
                        "redirect": "/employee"
                    }), 400
                
                if not new_password or not confirm_password:
                    return jsonify({
                        "status" : "error",
                        "message" : "New Password or Confirm Password must not be empty",
                        "redirect": "/employee"
                    }), 400

            # get the other fields to update the employee to database
            name = request.form.get("name")
            NRC = request.form.get("NRC")
            father_name = request.form.get("father_name")
            address = request.form.get("address")
            phone = request.form.get("phone")

            # preventing not to insert other values than empty string if user does not input unrequired fields
            if not NRC:
                NRC = ""
            
            if not father_name:
                father_name = ""
            
            if not address:
                address = ""
            
            if not phone:
                phone = ""

            try:
                # base query without password field
                query = "UPDATE employee SET name = :name, position = :position, department = :department, center_id = :center_id," \
                " NRC = :NRC, father_name = :father_name, address = :address, phone = :phone" 
                # base params without password field 
                # python dictonary for "Dictonary Unpacking" to insert the parameter.
                params = {
                    "name" : name,
                    "position" : position,
                    "department" : department,
                    "center_id" : center_id,
                    "NRC" : NRC,
                    "father_name" : father_name,
                    "address" : address,
                    "phone" : phone,
                    "id" : id
                }
                
                # update query and params with password
                if old_password and new_password and confirm_password:
                    query += ", hash = :hash"
                    params["hash"] = generate_password_hash(new_password)
                
                query += " WHERE id = :id"

                db.execute(query, **params)

            except Exception as e:
                return jsonify({
                    "status" : "error",
                    "message" : f"Unknown database error occured, Please contact Admin: {str(e)}"
                }), 400

            # return success 
            return jsonify({
                "status": "success",
                "message": f"Staff_id {staff_id} status was successfully updated.",
                "redirect": "/employee"
            }), 200

        # Handle cases where action is NOT "create"
        else:
            return jsonify({"status": "error", "message": f"Invalid form action: '{action}' submitted."}), 400   

    # get method   
    else:
        id = request.args.get("id")

        # if current user try to edit themselves, redirect to account page
        if id == str(session["user_id"]):
            return redirect(url_for('account'))

        employee = db.execute(
            "SELECT * FROM employee WHERE id = :id",
            id = id
        )

        if not employee:
            return not_found("/employee", "Employee")
            
        centers = db.execute(
            "SELECT center_id, name from service_centers"
            )

        current_emp = employee[0]
        return render_template("employee_edit.html", centers = centers, employee = current_emp)

@app.route('/verify_old_password', methods=['POST'])
def verify_old_password():
    # 1. Grab values from background javascript checking request
    typed_password = request.form.get("old_password")
    id = request.args.get("id")
    
    # 2. Query active logged-in employee record profile from SQLite
    user_row = db.execute("SELECT hash FROM employee WHERE id = :id", id=id)
    
    if not user_row:
        return jsonify({"valid": False}), 200

    # 3. Compare typed plaintext password with encrypted database hash string
    is_correct = check_password_hash(user_row[0]['hash'], typed_password)
    
    # 4. Return true or false as a clean JSON indicator
    return jsonify({"valid": is_correct}), 200
    
@app.route("/account")
@login_required
def account():
    return render_template("account.html")

@app.route("/service_center")
@login_required
def service_center():
    # to calcuate total centers
    centers = db.execute(
        "SELECT name,active FROM service_centers"
    )

    employee = db.execute(
        "SELECT COUNT(*) as count FROM employee WHERE active = 1"
    )

    total_active_emp = employee[0]["count"]

    total_centers = 0
    total_active_centers = 0
    for center in centers:

        if center["active"] == 1:
            total_active_centers += 1

        total_centers += 1

    return render_template("service_center.html", total_centers = total_centers, total_active_centers = total_active_centers, total_active_emp = total_active_emp)

@app.route('/search_centers/')
@login_required
def search_centers():
    try:
        # 1. Grab pagination filters (Defaults to Page 1, Limit 10 items)
        page = int(request.args.get('page', 1))
        per_page = 10
        offset = (page - 1) * per_page

        # 2. Extract service center input values sent by JS URLSearchParams
        center_id = request.args.get('center_id', '').strip()
        name = request.args.get('name', '').strip()
        manager = request.args.get('manager', '').strip() 
        address = request.args.get('address', '').strip()
        phone = request.args.get('phone', '').strip()
        active = request.args.get('active', '1').strip()

        # 3. Build dynamic where condition filters dictionary
        params = {}
        where_clauses = "WHERE 1=1"

        # Dynamic text filter parameter generation loops
        if active:
            where_clauses += " AND s.active = :active"
            params['active'] = int(active)
        if center_id:
            where_clauses += " AND s.center_id = :center_id"
            params['center_id'] = center_id
        if name:
            where_clauses += " AND s.name LIKE :name"
            params['name'] = f"%{name}%"
        if address:
            where_clauses += " AND s.address LIKE :address"
            params['address'] = f"%{address}%"
        if phone:
            where_clauses += " AND s.phone LIKE :phone"
            params['phone'] = f"%{phone}%"

        # 4. Filter by aggregated Manager names after group consolidation using HAVING
        if manager:
            where_clauses += " HAVING manager LIKE :manager"
            params['manager'] = f"%{manager}%"

        # 5. QUERY A: Calculate the total counts for the pagination metadata limits
        count_query = f"""
            SELECT COUNT(*) as total FROM (
                SELECT s.center_id
                FROM service_centers s
                LEFT JOIN employee e ON s.center_id = e.center_id AND e.position = '1' AND e.active = 1
                {where_clauses}
                GROUP BY s.center_id
                {f"HAVING IFNULL(GROUP_CONCAT(e.name, ', '), 'No Manager Assigned') LIKE :manager" if manager else ""}
            )
        """
        count_result = db.execute(count_query, **params)

        # 6. Extract the total counts safely out of result dictionary lists
        total_records = count_result[0]['total'] if isinstance(count_result, list) else count_result['total']
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        # 7. QUERY B: Fetch only the targeted 10 rows matching page tracking boundaries
        data_query = f"""
            SELECT 
                s.id,
                s.center_id, 
                s.name AS name, 
                s.address, 
                s.phone,
                IFNULL(GROUP_CONCAT(e.name, ', '), 'No Manager Assigned') AS manager
            FROM service_centers s
            LEFT JOIN employee e ON s.center_id = e.center_id AND e.position = '1' AND e.active = 1
            {where_clauses}
            GROUP BY s.center_id
            {f"HAVING manager_names LIKE :manager" if manager else ""}
            LIMIT :limit OFFSET :offset
        """

        params['limit'] = per_page
        params['offset'] = offset
        rows = db.execute(data_query, **params)

        return jsonify({
            "status": "success",
            "centers": list(rows),
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_records": total_records
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Query processing exception: {str(e)}"}), 500

@app.route("/service_center_create", methods = ["GET", "POST"])
@login_required
def service_center_create():
    """ Create Service center"""
    if request.method == "POST":
        action = request.form.get("action")

        # action submit
        if action == "service_center_create":
            center_id = request.form.get("center_id")
            name = request.form.get("name")
            address = request.form.get("address")
            phone = request.form.get("phone")

            if not address:
                address = ""
            
            if not phone:
                phone = ""

            try:
                db.execute(
                    "INSERT INTO service_centers (center_id, name, address, phone) VALUES (:center_id, :name, :address, :phone)",
                    center_id = center_id,
                    name = name,
                    address = address,
                    phone = phone
                )

                return jsonify ({"status":"success","message":f"Employee'{center_id}'was created"}),200

            except Exception as error:
                # catch error string
                    error_msg = str(error).lower()

                    # staff_id validation
                    if "unique" in error_msg or "constraint" in error_msg:
                        return jsonify({"status": "error","message": "Center_id is already exists"}),400
                    
                    # other unknown database error
                    else:
                        return jsonify({"status": "error","message": "Unknown datatbase occured. Please contact Admin!!!"}),500

        # Handle cases where action is NOT "create"
        else:
            return jsonify({"status": "error", "message": f"Invalid form action: '{action}' submitted."}), 400

    # get method
    else:
        return render_template("service_center_create.html")
    
@app.route("/service_center_details/", methods = ["POST", "GET"])
@login_required
def service_center_details():
    """Edit Center"""
    # post Method
    if request.method == "POST":
        id = request.args.get("id")

        if not id:
            return jsonify({"status": "error", "message": "Missing center ID reference."}), 400
        
        action = request.form.get("action")
        center_id = request.form.get("center_id")

        # inactive action
        if action == "inactive":

            # update database
            db.execute(
                "UPDATE service_centers SET active = 0 WHERE id = :id",
                id = id
            )

            # return success 
            return jsonify({
                "status": "success",
                "message": f"Center_id {center_id} profile status successfully modified to Inactive.",
                "redirect": "/service_center"
            }), 200

        # edit action
        if action == "edit":
            name = request.form.get("name")
            address = request.form.get("address")
            phone = request.form.get("phone")

            if not name:
                return jsonify({
                        "status" : "error",
                        "message" : "Center name does not empty",
                    }), 400

            # preventing not to insert other values than empty string if user does not input unrequired fields
            if not address:
                address = ""

            if not phone:
                phone = ""
            
            # update Database
            try:
                db.execute(
                    "UPDATE service_centers SET name = :name, address = :address, phone = :phone WHERE center_id = :center_id",
                    name = name,
                    address = address,
                    phone = phone,
                    center_id = center_id
                )

            except Exception as e:
                return jsonify({
                    "status" : "error",
                    "message" : f"Unknown database error occured, Please contact Admin: {str(e)}"
                }), 400

            # return success 
            return jsonify({
                "status": "success",
                "message": f"Center ID {center_id} status was successfully updated.",
                "redirect": "/service_center"
            }), 200

        # Handle cases where action is NOT "create"
        else:
            return jsonify({"status": "error", "message": f"Invalid form action: '{action}' submitted."}), 400

    # Get Method    
    else:
        id = request.args.get("id")

        center = db.execute(
            "SELECT * FROM service_centers WHERE id = :id",
            id = id
        )

        if not center:
            return not_found("/service_center", "Service Center")

        current_center = center[0]

        return render_template("service_center_details.html", center = current_center)
    
@app.route("/inventory_details", methods =["GET", "POST"])
@login_required
def inventory_details():
    if session["center_id"] == 'SC-000':
        centers = db.execute("SELECT center_id, name FROM service_centers")
    else:
        centers = db.execute(
            """SELECT e.center_id, s.name FROM employee e
            INNER JOIN service_centers s ON s.center_id = e.center_id WHERE e.id = :id""",
            id = session.get("user_id")
        )
    return render_template("inventory_details.html", centers = centers)

@app.route("/inventory_management")
@login_required
def inventory_management():
    return render_template("inventory_management.html")

@app.route("/create_inventory", methods =["POST"])
@login_required
def create_inventory():
    """Create Inventory"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON transaction parameters data."}), 400
    
    action = data.get('action')
    items_list = data.get('items', [])

    # check Duplicate Date form front-end
    duplicate = set()

    duplicate_code = set(item['code'] for item in items_list if item['code'] in duplicate or duplicate.add(item['code']))

    if len(duplicate_code) > 0:
        return jsonify({"status": "error", "message": f"Dulplicate items: {duplicate_code} found! Please Check your table!", "redirect": "/inventory_management"}), 400

    if action == "create_inventory":
        try:
            #  Open an atomic database tracking transaction scope block
            db.execute("BEGIN TRANSACTION")

            for item in items_list:
                # Loop out individual row values cleanly from the JSON payload arrays matrix
                code = item.get('code')
                name = item.get('name')
                model = item.get('model')
                price = item.get('price')

                # Execute your SQLite database INSERT loops here safely...
                db.execute(
                    "INSERT INTO spare_parts (code, name, model, price) VALUES ( :code, :name, :model, :price)", 
                code=code,
                name=name,
                model=model,
                price=price)

            db.execute("COMMIT")
            return jsonify({"status": "success", "message": f"Successfully Create {len(items_list)} new inventory item rows.", "redirect": "/inventory_management"}), 200

        except Exception as query_fault:
            return jsonify({"status": "error", "message": f"Database storage exception warning: {str(query_fault)}"}), 500

    else:    
        return jsonify({"status": "error", "message": f"Invalid form action: '{action}' submitted."}), 400
    
@app.route("/search_inventory/")
@login_required
def search_inventory():
    try:
        # 1. Grab pagination filters (Defaults to Page 1, Limit 10 items)
        page = int(request.args.get('page', 1))
        per_page = 15
        offset = (page - 1) * per_page

        # 2. Extract service center input values sent by JS URLSearchParams
        code = request.args.get('code', '').strip()
        name = request.args.get('name', '').strip()
        model = request.args.get('model', '').strip()
        center_id = request.args.get('center_id', '').strip() 
        active = request.args.get('active', '1').strip()
        in_stock = request.args.get('in_stock', '1').strip()

        # 3. Dynamic text filter parameter generation loops
        params = {}
        where_clauses = "WHERE 1=1"
        join_clause = ""

        if active:
            where_clauses += " AND active = :active"
            params['active'] = active
        if code:
            where_clauses += " AND s.code = :code"
            params['code'] = code
        if name:
            where_clauses += " AND name LIKE :name"
            params['name'] = f"%{name}%"
        if model:
            where_clauses += " AND model LIKE :model"
            params['model'] = f"%{model}%"
        if center_id and int(in_stock) == 1:
            join_clause += "INNER JOIN branch_inventory AS b ON s.code = b.code AND b.center_id = :center_id "
            params['center_id'] = center_id
        if center_id and int(in_stock) == 0:
            join_clause += "LEFT JOIN branch_inventory AS b ON s.code = b.code AND b.center_id = :center_id "
            params['center_id'] = center_id
        
        # 4. Count query
        count_query = f"SELECT count(*) as total FROM spare_parts AS s {join_clause} {where_clauses}"

        # 5. count result
        count_result = db.execute(count_query,**params)

        # 6. Extract the total counts safely out of result dictionary lists
        total_records = count_result[0]['total'] if isinstance(count_result, list) else count_result['total']
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        # 7. data Query
        data_query = f"SELECT s.*, b.quantity AS quantity FROM spare_parts AS s {join_clause} {where_clauses} LIMIT :limit OFFSET :offset"

        params['limit'] = per_page
        params['offset'] = offset
        rows = db.execute(data_query, **params)

        return jsonify({
            "status": "success",
            "inventory": list(rows),
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_records": total_records
            }
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": f"Query processing exception: {str(e)}"}), 500

@app.route("/purchase_order")
@login_required
def purchase_order():
    return render_template("purchase_order.html")

@app.route("/purchaser_order_create")
@login_required
def purchase_order_create():
    return render_template("purchase_order_create.html")

@app.route('/create_POID', methods=['GET'])
@login_required
def create_poid():
    # Reads the parameters directly out of the incoming URL arguments query string lines
    merchant_name = request.args.get('merchant', '').strip()

    if not merchant_name:
        return jsonify({"status": "error", "message": "Missing 'merchant' parameter in the request."}), 400

    po_id = generate_sequence_id(db, 'purchase_orders', 'po_id', 'PO')

    if not po_id.startswith('PO'):
        return jsonify({"status": "error", "message": f"Failed to generate a unique Purchase Order ID.{po_id}"}), 500

    try:
        db.execute(
            "INSERT INTO purchase_orders (po_id, merchant, created_by) VALUES (:po_id, :merchant, :created_by)",
            po_id=po_id,
            merchant=merchant_name,
            created_by=session["user_id"]
        )

    except Exception as e:
        return jsonify({"status": "error", "message": f"PO Database insertion error: {str(e)}"}), 500
    
    # return the generated Purchase Order ID as a JSON response
    return jsonify({"status": "success", "po_id": po_id})

@app.route("/save_POID", methods=['POST'])
@login_required
def save_poid():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON transaction parameters data."}), 400
    
    items_list = data.get('items', [])

    po_id = items_list[0].get('po_id') if items_list else None

    db_po_id = db.execute("SELECT po_id FROM purchase_orders ORDER BY created_at DESC LIMIT 1")[0]['po_id']

    if po_id != db_po_id:
        return jsonify({"status": "error", "message": f"Purchase Order ID mismatch. Expected: {db_po_id}, Received: {po_id}", "redirect": "/create_order"}), 400

    if not po_id:
        return jsonify({"status": "error", "message": "Missing Purchase Order ID parameter."}), 400

    if len(items_list) == 0:
        return jsonify({"status": "error", "message": "No items provided for the Purchase Order."}), 400

    try:
        # Open an atomic database tracking transaction scope block
        db.execute("BEGIN TRANSACTION")

        for item in items_list:
            code = item.get('code')
            qty_bought = item.get('qty_bought')

            unit_price = db.execute("SELECT price FROM spare_parts WHERE code = :code", code = code)[0]['price']
            total_price = unit_price*qty_bought

            db.execute(
                "INSERT INTO purchase_items (po_id, code, qty_bought, total_price) VALUES (:po_id, :code, :qty_bought, :total_price)", 
                po_id=po_id,
                code=code,
                qty_bought=qty_bought,
                total_price=total_price
            )

        db.execute("COMMIT")
        return jsonify({"status": "success", "message": f"Successfully saved {len(items_list)} items for Purchase Order '{po_id}'.","redirect": "/purchase_order"}), 200

    except Exception as query_fault:
        return jsonify({"status": "error", "message": f"Database storage exception warning: {str(query_fault)}"}), 500

@app.route("/update_POID", methods = ['POST'])
@login_required
def update_poid():

    # get json file
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Missing JSON transaction parameters data."}), 400

    items_list = data.get('items', [])

    if not items_list:
        return jsonify({"status": "error", "message": "The purchase Order that does not have items cannot be approved. PLEASE CANCEL THE ORDER!!!"}), 400

    # get POID from list
    po_id = items_list[0].get('po_id') if items_list else None
    status = items_list[0].get('status') if items_list else None

    # to validate PO data
    db_items_list = db.execute(
        "SELECT code, qty_bought, qty_received FROM purchase_items WHERE po_id = :po_id",
        po_id = po_id
    )

    db_status = db.execute(
        "SELECT status FROM purchase_orders WHERE po_id = :po_id",
        po_id = po_id
    )[0]["status"]

    if not db_status == status:
        return jsonify({"status": "error", "message": "Purchase Order ID Mismatch!!! Please reload the page"}), 400

    if not len(items_list) == len(db_items_list):
        return jsonify({"status": "error", "message": "Incoming item count Mismatch!!! Please reload the page"}), 400

    # store NOT match data
    qty_bought_mismatch_items = []
    qty_received_mismatch_items = []
    code_mismatch_items = []
    more_qty_items = []
    zero_qty_items = []

    for db_item in db_items_list:
        for item in items_list:
            if db_item.get("code") == item.get("code"):
                code_mismatch_items.append(item)
                if int(item.get("orderQuantity")) != int(db_item.get("qty_bought")):
                    qty_bought_mismatch_items.append(item)
                if int(db_item.get("qty_received")) != 0:
                    if int(item.get("orderQuantity")) != int(db_item.get("qty_received")):
                        qty_received_mismatch_items.append(item)
                if int(item.get("orderQuantity")) == 0:
                    zero_qty_items.append(item)
                if int(item.get("orderQuantity")) > int(db_item.get("qty_bought")):
                    more_qty_items.append(item)

    if len(db_items_list) != len(code_mismatch_items):
        return jsonify({"status": "error", "message": "Incoming items Mismatch!!! Please reload the page"}), 400

    if db_status == 'PENDING':

        if not (session["user_role"] == "0" or session["user_role"] == "1"):
            return jsonify({"status": "error", "message": "You do not permission to perform the action!!! Please reload the page.", "redirect": "/purchase_order"}), 400

        # not_match list have lenght, update the db
        if qty_bought_mismatch_items:
    
            if not (session["user_role"] == "0" or session["user_role"] == "1"):
                return jsonify({"status": "error", "message": "You do not permission to modify the items!!! Please reload the page.", "redirect": "/purchase_order"}), 400
            
            try:
                db.execute("BEGIN TRANSACTION")
                for item in qty_bought_mismatch_items:
                    item_code = item.get("code")
                    qty_bought = item.get("orderQuantity")
    
                    unit_price = db.execute("SELECT price FROM spare_parts WHERE code = :code", code = item_code)[0]['price']
                    total_price = int(unit_price) * int(qty_bought)
                    
                    db.execute(
                        "UPDATE purchase_items SET qty_bought = :qty_bought, total_price = :total_price WHERE po_id = :po_id AND code = :code",
                        qty_bought = qty_bought,
                        total_price = total_price,
                        po_id = po_id,
                        code = item_code   
                    )
    
                db.execute("COMMIT")
            except Exception as e:
                return jsonify({"status": "error", "message": f"Updating Not_match_approved_items Query processing exception: {str(e)}"}), 500
            
        # Update the status of the order
        try:

            # get current datetime to update
            now = datetime.now()
            updated_at = now.strftime("%Y-%m-%d %H:%M:%S")

            db.execute(
                "UPDATE purchase_orders SET status = :status, approved_by = :approved_by, updated_at = :updated_at WHERE po_id = :po_id",
                status = "APPROVED",
                approved_by = session["user_id"],
                po_id = po_id,
                updated_at = updated_at
            )

            return jsonify({"status": "success", "message": f"The Purchase Order ID: {po_id} had been APPROVED!!!", "redirect": "/purchase_order"}), 200

        except Exception as e:
            return jsonify({"status": "error", "message": f"Updating Approve Order Query processing exception: {str(e)}"}), 500

    if db_status == 'APPROVED':

        # check more_qty items and return false
        if more_qty_items:
            return jsonify({"status": "error", "message": "Received Items amount cannot be exceeded than Bought items amount!!!", "redirect": "/purchase_order"}), 500

        # check all items are zero or check user forget to click save items 
        if len(db_items_list) == len(zero_qty_items):
            return jsonify({"status": "error", "message": "Order cannot be saved when all received item amount are zero. Please receive items first or cancel the order!!!"}), 400

        # not_match list have lenght, update the db
        if qty_bought_mismatch_items:

            if not (session["user_role"] == "0" or session["user_role"] == "1"):
                return jsonify({"status": "error", "message": "You do not permission to modify the items!!! Please reload the page.", "redirect": "/purchase_order"}), 400 

            try:
                db.execute("BEGIN TRANSACTION")
                for item in qty_bought_mismatch_items:
                    item_code = item.get("code")
                    qty_received = item.get("orderQuantity")

                    unit_price = db.execute("SELECT price FROM spare_parts WHERE code = :code", code = item_code)[0]['price']
                    total_price = int(unit_price) * int(qty_received)
                    
                    db.execute(
                        "UPDATE purchase_items SET qty_received = :qty_received, total_price = :total_price WHERE po_id = :po_id AND code = :code",
                        qty_received = qty_received,
                        total_price = total_price,
                        po_id = po_id,
                        code = item_code   
                    )

                db.execute("COMMIT")
            except Exception as e:
                return jsonify({"status": "error", "message": f"Updating Not_match_received_items Query processing exception: {str(e)}"}), 500

        # Update the status of the order to approve
        try:

            # get current datetime to update
            now = datetime.now()
            updated_at = now.strftime("%Y-%m-%d %H:%M:%S")

            db.execute(
                "UPDATE purchase_orders SET status = :status, received_by = :received_by, updated_at = :updated_at WHERE po_id = :po_id",
                status = "RECEIVED",
                received_by = session["user_id"],
                po_id = po_id,
                updated_at = updated_at
            )

            for item in items_list:
                code = item.get("code")
                qty_received = item.get("orderQuantity")
                db.execute(
                    "UPDATE purchase_items SET qty_received = :qty_received WHERE po_id = :po_id AND code = :code",
                    qty_received = qty_received,
                    po_id = po_id,
                    code = code
                )

            return jsonify({"status": "success", "message": f"The Purchase Order ID: {po_id} had been RECEIVED!!!", "redirect": "/purchase_order"}), 200

        except Exception as e:
            return jsonify({"status": "error", "message": f"Updating Approve Order Query processing exception: {str(e)}"}), 500

    if db_status == 'RECEIVED':

        if qty_received_mismatch_items:
            return jsonify({"status": "error", "message": "Incoming items Mismatch!!! Please reload the page"}), 400

        if not (session["user_role"] == "0" or session["user_role"] == "1"):
            return jsonify({"status": "error", "message": "You do not permission to complete the order!!! Please reload the page.", "redirect": "/purchase_order"}), 400

        # update or insert branch_inventory and inventory_transactions
        try:

            db.execute("BEGIN TRANSACTION")

            for db_item in db_items_list:
                code = db_item.get("code")
                qty_received = db_item.get("qty_received")

                #update transcations table
                db.execute(
                    """INSERT INTO inventory_transactions ( code, center_id, qty_change, transaction_type, reference_id, staff_id) 
                    VALUES (:code, :center_id, :qty_change, :transaction_type, :reference_id, :staff_id)""",
                    code = code,
                    center_id = session.get("center_id"),
                    qty_change = qty_received,
                    transaction_type = "Purchase Order",
                    reference_id = po_id,
                    staff_id = session.get("user_id")
                )

                # update the branch_inventory table
                db.execute(
                    """INSERT INTO branch_inventory (code, center_id, quantity) VALUES (:code, :center_id, :quantity)
                    ON CONFLICT(code, center_id) DO UPDATE SET quantity = quantity + :quantity""",
                    code = code,
                    center_id = session.get("center_id"),
                    quantity = qty_received,
                )

            db.execute("COMMIT")        

        except Exception as e:
            return jsonify({"status": "error", "message": f"Updating Inventory Transaction Query processing exception: {str(e)}"}), 500 

        # Update the status of the order
        try:

            # get current datetime to update
            now = datetime.now()
            updated_at = now.strftime("%Y-%m-%d %H:%M:%S")

            db.execute(
                "UPDATE purchase_orders SET status = :status, completed_by = :completed_by, updated_at = :updated_at WHERE po_id = :po_id",
                status = "COMPLETED",
                completed_by = session["user_id"],
                po_id = po_id,
                updated_at = updated_at
            )

            return jsonify({"status": "success", "message": f"The Purchase Order ID: {po_id} had been COMPLETED!!!", "redirect": "/purchase_order"}), 200

        except Exception as e:
            return jsonify({"status": "error", "message": f"Updating Complete Order Query processing exception: {str(e)}"}), 500


@app.route("/cancel_POID", methods = ['POST'])
@login_required
def cancel_poid():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Missing JSON transaction parameters data."}), 400

    items_list = data.get('items', [])

    po_id = items_list[0].get('po_id') if items_list else None
    items_lenght = items_list[0].get('items_length') if items_list else None
    status = items_list[0].get('status') if items_list else None
    items = items_list[0].get('items') if items_list else None

    try:
        db_item_lenght = db.execute(
            "SELECT count(*) AS lenght FROM purchase_items WHERE po_id = :po_id",
            po_id = po_id
        )[0]["lenght"]

        db_items_list = db.execute(
            "SELECT code FROM purchase_items WHERE po_id = :po_id",
            po_id = po_id
        )

        db_status = db.execute(
            "SELECT status FROM purchase_orders WHERE po_id = :po_id",
            po_id = po_id
        )[0]['status']

        check_mismatch_items = []

        for db_item in db_items_list:
            for item in items:
                if db_item.get("code") == item.get("code"):
                    check_mismatch_items.append(item)

        if len(db_items_list) != len(check_mismatch_items):
            return jsonify({"status": "error", "message": "Purchase Order ITEM CODE Mismatch.", "redirect": "/purchase_order"}), 400

        if not items_lenght == db_item_lenght:
            return jsonify({"status": "error", "message": "Purchase Order LENGTH Mismatch.", "redirect": "/purchase_order"}), 400

        if not status == db_status:
            return jsonify({"status": "error", "message": "Purchase Order STATUS Mismatch.", "redirect": "/purchase_order"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": f"Validation Database exception warning: {str(e)}"}), 500

    try:

        # get current datetime to update
        now = datetime.now()
        updated_at = now.strftime("%Y-%m-%d %H:%M:%S")

        db.execute(
            "UPDATE purchase_orders SET status = :status, completed_by = :completed_by, updated_at = :updated_at WHERE po_id = :po_id",
            status = "CANCELLED",
            completed_by = session["user_id"],
            updated_at = updated_at,
            po_id = po_id
        )

        return jsonify({"status": "success", "message": f"The Purchase Order ID: {po_id} had been CANCELLED!!!", "redirect": "/purchase_order"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database storage exception warning: {str(e)}"}), 500

    
@app.route("/search_purchase_order/")
@login_required
def search_purchase_order():
    try:
        # 1. Grab pagination filters (Defaults to Page 1, Limit 10 items)
        page = int(request.args.get('page', 1))
        per_page = 10
        offset = (page - 1) * per_page

        # 2. Extract service center input values sent by JS URLSearchParams
        po_id = request.args.get('po_id', '').strip()
        merchant = request.args.get('merchant', '').strip() 
        created_name = request.args.get('created_name', '').strip()
        approved_name = request.args.get('approved_name', '').strip()
        status = request.args.get('status', 'all').strip()
        created_at = request.args.get('created_at', '').strip()

        # 3. Dynamic text filter parameter generation loops
        params = {}
        where_clauses = "WHERE 1=1"

        if po_id:
            where_clauses += " AND po_id = :po_id"
            params['po_id'] = po_id
        if merchant:
            where_clauses += " AND merchant LIKE :merchant"
            params['merchant'] = f"%{merchant}%"
        if status and status != 'all':
            where_clauses += " AND status LIKE :status"
            params['status'] = f"%{status.upper()}%"
        if created_name:
            where_clauses += " AND e1.name LIKE :created_name"
            params['created_name'] = f"%{created_name}%"
        if approved_name:
            where_clauses += " AND e2.name LIKE :approved_name"
            params['approved_name'] = f"%{approved_name}%"
        if created_at:
            where_clauses += " AND created_at >= :created_at AND created_at < DATE(:created_at, '+1 day')"
            params['created_at'] = created_at

        # 4. QUERY A: Calculate the total counts for the pagination metadata limits
        count_query = f"""
            SELECT COUNT(*) as total FROM purchase_orders p
            {where_clauses}"""

        # 5. Execute the count query with parameters
        count_result = db.execute(count_query, **params)

        # 6. Extract the total counts safely out of result dictionary lists
        total_records = count_result[0]['total'] if isinstance(count_result, list) else count_result['total']
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        center_id = session.get('center_id', '').strip()

        # 7. QUERY B: Fetch only the targeted rows matching page tracking boundaries
        data_query = f"""
            SELECT p.*, e1.name AS created_name, e2.name AS approved_name, e3.name AS completed_name
            FROM purchase_orders p 
            LEFT JOIN employee e1 ON p.created_by = e1.id
            LEFT JOIN employee e2 ON p.approved_by = e2.id 
            LEFT JOIN employee e3 ON p.completed_by = e3.id
            {where_clauses} ORDER BY p.created_at DESC LIMIT :limit OFFSET :offset"""

        params['limit'] = per_page
        params['offset'] = offset
        rows = db.execute(data_query, **params)

        # 8. Total cost calculation for each purchase order
        total_costs_db = db.execute("""
            SELECT po_id, SUM(total_price) AS total_cost
            FROM purchase_items
            GROUP BY po_id
        """)

        po_data = []
        for row in rows:
            total_cost = next((item['total_cost'] for item in total_costs_db if item['po_id'] == row['po_id']), 0)
            po_data.append({
                "po_id": row["po_id"],
                "merchant": row["merchant"],
                "status": row["status"],
                "created_name": row["created_name"],
                "approved_name": row["approved_name"],
                "completed_name": row.get("completed_name"),
                "created_at": row["created_at"],
                "approved_at": row.get("approved_at"),
                "updated_at": row.get("updated_at"),
                "total_cost": total_cost
            })

        return jsonify({
            "status": "success",
            "po_data": po_data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_records": total_records
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Query processing exception: {str(e)}"}), 500

@app.route("/purchase_order_details/", methods=["GET", "POST"])
@login_required
def purchase_order_details():
    po_id = request.args.get("po_id")

    # check PO_id exists in the database
    po_exists = db.execute("SELECT po_id FROM purchase_orders WHERE po_id = :po_id", po_id=po_id)

    if not po_exists:
        return not_found("/purchase_order", "Purchase Order Page")

    row = db.execute(
        "SELECT p.*, e1.name AS created_name, e2.name AS approved_name, e3.name AS received_name, e4.name AS completed_name "
        "FROM purchase_orders p "
        "LEFT JOIN employee e1 ON p.created_by = e1.id "
        "LEFT JOIN employee e2 ON p.approved_by = e2.id "
        "LEFT JOIN employee e3 ON p.received_by = e3.id "
        "LEFT JOIN employee e4 ON p.completed_by = e4.id "
        "WHERE p.po_id = :po_id",
        po_id=po_id
    )

    total_cost_row = db.execute(
        "SELECT SUM(total_price) AS total_cost FROM purchase_items WHERE po_id = :po_id",
        po_id=po_id
    )

    order = row[0] if row else None

    if total_cost_row and total_cost_row[0]['total_cost'] is not None:
        total_cost = f"{float(total_cost_row[0]['total_cost']):.2f}"
    else:
        total_cost = "0.00"

    return render_template("purchase_order_details.html", order=order, total_cost=total_cost)

@app.route("/search_po_items/")
@login_required
def search_po_items():
    try:
        # 1. Grab pagination filters (Defaults to Page 1, Limit 10 items)
        page = int(request.args.get('page', 1))
        per_page = 10
        offset = (page - 1) * per_page

        # 2. Extract service center input values sent by JS URLSearchParams
        po_id = request.args.get('po_id', '').strip()

        # 3. Dynamic text filter parameter generation loops
        params = {}
        where_clauses = "WHERE 1=1"

        if po_id:
            where_clauses += " AND po_id = :po_id"
            params['po_id'] = po_id

        # 4. Count query
        count_query = f"SELECT count(*) as total FROM purchase_items {where_clauses}"

        # 5. count result
        count_result = db.execute(count_query,**params)

        # 6. Extract the total counts safely out of result dictionary lists
        total_records = count_result[0]['total'] if isinstance(count_result, list) else count_result['total']
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        # 7. data Query
        data_query = f"""SELECT p.*, s.name as name, s.model as model, s.price as unit_price, bi.quantity as quantity FROM purchase_items p 
            LEFT JOIN spare_parts s ON p.code = s.code 
            LEFT JOIN branch_inventory bi ON bi.code = p.code AND bi.center_id = :center_id
            {where_clauses} LIMIT :limit OFFSET :offset"""

        params['limit'] = per_page
        params['offset'] = offset
        params['center_id'] = session.get('center_id', '').strip()
        rows = db.execute(data_query, **params)

        return jsonify({
            "status": "success",
            "po_items": list(rows),
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_records": total_records
            }
        }), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": f"Query processing exception: {str(e)}"}), 500

@app.route("/repair_ticket")
@login_required
def repair_tickets():

    if session["center_id"] == 'SC-000':
            centers = db.execute("SELECT center_id, name FROM service_centers")
    else:
        centers = db.execute(
            """SELECT e.center_id, s.name FROM employee e
            INNER JOIN service_centers s ON s.center_id = e.center_id WHERE e.id = :id""",
            id = session.get("user_id")
        ) 

    return render_template("repair_ticket.html", centers = centers)

@app.route("/repair_ticket_create", methods = ["POST", "GET"])
@login_required
def repair_ticket_create():
    if request.method == 'POST':

        # get values ready for database
        ticket_id = generate_sequence_id(db, 'repair_table', 'ticket_id', 'RP')
        customer_name = request.form.get('customer_name')
        phone = request.form.get("phone")
        dealer_info = request.form.get("dealer_info", "")
        model = request.form.get("model")
        imei = request.form.get("IMEI")
        purchase_date = request.form.get("purchase_date")
        physical_condition = request.form.get("physical_condition", "")
        accessories = request.form.get("accessories", "")
        cus_error = request.form.get("cus_error")
        error_details = request.form.get("error_detail")
        repair_by = request.form.get("engineer_name")

        params = {}

        # validation and adding params to insert database
        if ticket_id:
            params["ticket_id"] = ticket_id
        else:
            return jsonify({"status": "error", "message": "Ticket ID field is empty!!!"}), 400

        if customer_name:
            params["customer_name"] = customer_name
        else:
            return jsonify({"status": "error", "message": "Customer Name field is empty!!!"}), 400

        if phone:
            params["phone"] = phone
        else:
            return jsonify({"status": "error", "message": "Customer Phone field is empty!!!"}), 400

        if dealer_info:
            params["dealer_info"] = dealer_info
        else:
            params["dealer_info"] = ""

        if model:
            params["model"] = model
        else:
            return jsonify({"status": "error", "message": "Phone Model field is empty!!!"}), 400

        if imei:
            params["IMEI"] = imei
        else:
            return jsonify({"status": "error", "message": "IMEI field is empty!!!"}), 400

        if purchase_date:
            params["purchase_date"] = purchase_date
        else:
            return jsonify({"status": "error", "message": "Purchase Date field is empty!!!"}), 400

        if physical_condition:
            params["physical_condition"] = physical_condition
        else:
            params["physical_condition"] = ""

        if accessories:
            params["accessories"] = accessories
        else:
            params["accessories"] = ""

        if cus_error:
            params["cus_error"] = cus_error
        else:
            return jsonify({"status": "error", "message": "Customer Mentioned Issue field is empty!!!"}), 400

        if error_details:
            params["error_details"] = error_details
        else:
            return jsonify({"status": "error", "message": "Error details field is empty!!!"}), 400

        if repair_by:
            params["repair_by"] = repair_by
        else:
            return jsonify({"status": "error", "message": "Send to Enginner field is empty!!!"}), 400

        params["center_id"] = session.get('center_id')
        params['status'] = "Received"
        params["received_by"] = session.get("user_id")

        try:
            db.execute(
                """INSERT INTO repair_table (ticket_id, center_id, status, customer_name, phone, dealer_info, 
                model, IMEI, purchase_date, physical_condition, accessories, cus_error, error_details, received_by, repair_by)
                VALUES (:ticket_id, :center_id, :status, :customer_name, :phone, :dealer_info, :model, :IMEI, 
                :purchase_date, :physical_condition, :accessories, :cus_error, :error_details, :received_by, :repair_by)""",
                **params
            )

        except Exception as e:
            return jsonify({"status": "error", "message": f"Query processing exception: {str(e)}"}), 500

        return jsonify({"status": "success", "message": f"The Repair Ticket: {ticket_id} had been Created!!!", "redirect": "/repair_ticket"}), 200

    else:
        engineers = db.execute(
            "SELECT id, staff_id, name FROM employee WHERE center_id = :center_id AND position = :position",
            center_id = session.get("center_id"),
            position = "2"
        )
        return render_template("repair_ticket_create.html", engineers = engineers)

@app.route("/search_repair_tickets/")
@login_required
def search_repair_tickets():
    try:
        # 1. Grab pagination filters (Defaults to Page 1, Limit 10 items)
        page = int(request.args.get('page', 1))
        per_page = 10
        offset = (page - 1) * per_page

        # 2. Extract service center input values sent by JS URLSearchParams
        customer_name   = request.args.get('customer_name', '').strip()
        ticket_id       = request.args.get('repair_id', '').strip()
        center_id       = request.args.get('center_id', '').strip() 
        model           = request.args.get('model', '').strip()
        imei            = request.args.get('IMEI', '').strip()
        status          = request.args.get('status', 'all').strip()
        repair_by       = request.args.get('repairBy', '').strip()
        from_receive    = request.args.get('from_receive', '').strip()
        to_receive      = request.args.get('to_receive', '').strip() 
        from_repair     = request.args.get('from_repair', '').strip()
        to_repair       = request.args.get('to_repair', '').strip()
        from_complete   = request.args.get('from_complete', '').strip()
        to_complete     = request.args.get('to_complete', '').strip()

        # 3. Dynamic text filter parameter generation loops
        params = {}
        where_clauses = "WHERE 1=1"

        if customer_name:
            where_clauses += " AND customer_name LIKE :customer_name"
            params['customer_name'] = f"%{customer_name}%"

        if ticket_id:
            where_clauses += " AND ticket_id = :ticket_id"
            params['ticket_id'] = ticket_id

        if center_id and center_id != "all":
            if center_id != session.get('center_id'):
                if session.get('center_id') != "SC-000":
                    return jsonify({"status": "error", "message": "You do not have permission to perform this action!"}), 400
                else:
                    where_clauses += " AND r.center_id = :center_id"
                    params['center_id'] = center_id
            else:        
                where_clauses += " AND r.center_id = :center_id"
                params['center_id'] = center_id

        if model:
            where_clauses += " AND model LIKE :model"
            params['model'] = f"%{model}%"

        if imei:
            where_clauses += " AND IMEI LIKE :imei"
            params['imei'] = f"%{imei}%"

        if status and status != 'all':
            where_clauses += " AND status LIKE :status"
            params['status'] = f"%{status}%"

        if repair_by:
            where_clauses += " AND repair_by LIKE :repair_by"
            params['repair_by'] = f"%{repair_by}%" 

        if from_receive and not to_receive:
            where_clauses += " AND received_date >= :from_receive AND repair_date < DATE(:from_receive, '+1 day')"
            params['from_receive'] = from_receive

        if from_repair and to_receive:
            where_clauses += " AND received_date >= :from_receive AND repair_date < :to_receive"
            params['from_receive'] = from_receive
            params['to_receive'] = to_receive

        if from_repair and not to_repair:
            where_clauses += " AND repair_date >= :from_repair AND repair_date < DATE(:from_repair, '+1 day')"
            params['from_repair'] = from_receive
        
        if from_repair and to_repair:
            where_clauses += " AND repair_date >= :from_repair AND repair_date < :to_repair"
            params['from_repair'] = from_repair
            params['to_repair'] = to_repair

        if from_complete and not to_complete:
            where_clauses += " AND complete_date >= :from_complete AND complete_date < DATE(:from_complete, '+1 day')"
            params['from_complete'] = from_complete
        
        if from_complete and to_complete:
            where_clauses += " AND complete_date >= :from_complete AND complete_date < :to_complete"
            params['from_complete'] = from_complete
            params['to_complete'] = to_complete

        # 4. QUERY A: Calculate the total counts for the pagination metadata limits
        count_query = f"""
            SELECT COUNT(*) as total FROM repair_table AS r
            {where_clauses}"""

        # 5. Execute the count query with parameters
        count_result = db.execute(count_query, **params)

        # 6. Extract the total counts safely out of result dictionary lists
        total_records = count_result[0]['total'] if isinstance(count_result, list) else count_result['total']
        total_pages = max(1, (total_records + per_page - 1) // per_page)

        # 7. QUERY B: Fetch only the targeted rows matching page tracking boundaries
        data_query = f"""
            SELECT r.id AS id, ticket_id, customer_name, r.phone AS phone, model, IMEI, r.status AS status, received_date, sc.center_id AS center_id, sc.name AS center_name
            FROM repair_table AS r LEFT JOIN service_centers AS sc ON r.center_id = sc.center_id 
            {where_clauses} ORDER BY r.received_date DESC LIMIT :limit OFFSET :offset"""

        params['limit'] = per_page
        params['offset'] = offset

        rows = db.execute(data_query, **params)

        tickets = []
        for row in rows:
            tickets.append({
                "id": hashids.encode(row['id']),
                "ticket_id": row['ticket_id'],
                "customer_name": row['customer_name'],
                "phone": row['phone'],
                "model": row['model'],
                "imei": row['IMEI'],
                "status": row['status'],
                "received_date": row['received_date'],
                "center_id" : row['center_id'],
                "center_name" : row['center_name']
            })

         # calculate first date of the month
        now = datetime.now()
        first_datetime = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        card_params = {}
        card_params['first_datetime'] = first_datetime

        total_ticket_query = """
            SELECT count(*) as total_tickets FROM repair_table 
            WHERE received_date > :first_datetime"""

        open_tickets_query = """
            SELECT COUNT(julianday('now') - julianday(received_date)) AS total_open_tickets,
            IFNULL(MAX(ROUND(julianday('now') - julianday(received_date))), 0) AS max_days_to_complete 
            FROM repair_table WHERE status != 'Customer_Returned' AND received_date > :first_datetime"""
        
        open_tickets_7days_query = """
            SELECT COUNT(*) AS open_tickets_7days FROM repair_table 
            WHERE received_date > :first_datetime
            AND status != 'Customer_Returned'
            AND (julianday('now') - julianday(received_date)) > 7"""

        if center_id and center_id != "all":
            total_ticket_query += " AND center_id = :center_id"
            open_tickets_query += " AND center_id = :center_id"
            open_tickets_7days_query += " AND center_id = :center_id"
            card_params['center_id'] = center_id

        total_tickets = db.execute(total_ticket_query, **card_params)[0]['total_tickets']
        total_open_tickets = db.execute(open_tickets_query, **card_params)[0]['total_open_tickets']
        max_days_to_complete = db.execute(open_tickets_query, **card_params)[0]['max_days_to_complete']
        open_tickets_7days = db.execute(open_tickets_7days_query, **card_params)[0]['open_tickets_7days']

        print(max_days_to_complete,flush=True)

        return jsonify({
            "status": "success",
            "tickets": tickets,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_records": total_records
            },
            "statistic": {
                "total_tickets" : total_tickets,
                "total_open_tickets" : total_open_tickets,
                "max_days_to_complete" : max_days_to_complete,
                "open_tickets_7days" : open_tickets_7days
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Query processing exception: {str(e)}"}), 500

@app.route("/repair_tickets_details/", methods = ['GET','POST'])
@login_required
def repair_ticket_details():

    if request.method == 'POST':
        return_name = request.form.get("return_cus_name")
        return_phone = request.form.get("return_cus_phone")
        encode_id = request.form.get("ticket_id")
        decode_id = hashids.decode(encode_id)[0]
        remark = request.form.get("remark")

        if not return_name or not return_phone:
            return jsonify({"status": "error", "message": "Required Fields are missing! Please check the required fields or reload the page!"}), 500

        now = datetime.now()
        complete_date = now.strftime("%Y-%m-%d %H:%M:%S")
        
        params = {}
        base_query = """UPDATE repair_table SET return_name = :return_name, return_phone = :return_phone, 
        completed_by = :completed_by, complete_date = :complete_date, status = :status"""
        params['return_name'] = return_name
        params['return_phone'] = return_phone
        params['completed_by'] = session["user_id"]
        params['complete_date'] = complete_date
        params['status'] = 'Customer_Returned'

        if remark:
            base_query += ", remark = :remark"
            params['remark'] = remark

        base_query += " WHERE id = :id"
        params['id'] = decode_id

        db.execute(base_query, **params)

        return jsonify({
            "status": "success",
            "message": "The Repair Ticket had been Updated!!!",
            "redirect": "/repair_ticket"
        }), 200

    else:
        encode_id = request.args.get("ticket-id")
        decode_id = hashids.decode(encode_id)[0]

        rows = db.execute(
            """SELECT rp.*, e1.name AS received_name, e2.name AS repair_name, e3.name AS completed_name,
            e1.staff_id AS received_staff_id, e2.staff_id AS repair_staff_id, e3.staff_id AS completed_staff_id 
            FROM repair_table AS rp 
            LEFT JOIN employee AS e1 ON rp.received_by = e1.id
            LEFT JOIN employee AS e2 ON rp.repair_by = e2.id
            LEFT JOIN employee AS e3 ON rp.completed_by = e3.id
            WHERE rp.id = :id""",
            id=decode_id
        )

        ticket = rows[0]
        id = ticket.pop("id",None)

        inventory = db.execute(
            """SELECT rp.code AS code, sp.name, sp.model, sp.price FROM repair_inventory AS rp
            LEFT JOIN spare_parts AS sp ON rp.code = sp.code 
            WHERE ticket_id = :id""",
            id = decode_id
        )

        return render_template("repair_ticket_details.html", ticket=ticket, inventory=inventory)

@app.route("/update_ticket", methods = ['POST'])
@login_required
def update_ticket():
        # get json file
    data = request.get_json()
    items_list = data.get('items', [])

    if not items_list:
        return jsonify({"status": "error", "message": "Missing JSON transaction parameters data."}), 400
    
    encode_id = items_list[0].get('ticket_id')
    decode_id = hashids.decode(encode_id)[0]
    repair_code = items_list[0].get('repair_code')
    repair_details = items_list[0].get('repair_details')
    code = items_list[0].get('code')

    if not repair_code:
        return jsonify({"status": "error", "message": "Error Code is empty. Please add Error Code before submission."}), 400
    if repair_details == "0":
        return jsonify({"status": "error", "message": "Diagnosis details is empty. Please add Diagnosis details before submission."}), 400
    if repair_details == "1" and not code:
        return jsonify({"status": "error", "message": "Your Inventory table is empty. Please add at least one inventory item after 'Changed Sparepart' is chosen."}), 400
    if repair_details != "1" and code:
        return jsonify({"status": "error", "message": "There are inventories at your inventory table. You cannot choose inventory after choosing Diagnosis details other than 'Changed Sparparts'!"}), 400
        
    if code:
        duplicate = set()

        duplicate_code = set(item['code'] for item in items_list if item['code'] in duplicate or duplicate.add(item['code']))

        if len(duplicate_code) > 0:
            return jsonify({"status": "error", "message": "There are duplicate inventories at your inventory table."}), 400

    status = db.execute(
        "SELECT status FROM repair_table WHERE id = :id",
        id = decode_id
    )[0]['status']

    if code and status == 'Received':
        try:
            db.execute("BEGIN TRANSACTION")
            
            for item in items_list:
                code = item.get("code")

                #update transcations table
                db.execute(
                    """INSERT INTO inventory_transactions ( code, center_id, qty_change, transaction_type, reference_id, staff_id) 
                    VALUES (:code, :center_id, :qty_change, :transaction_type, :reference_id, :staff_id)""",
                    code = code,
                    center_id = session.get("center_id"),
                    qty_change = '-1',
                    transaction_type = "repair",
                    reference_id = decode_id,
                    staff_id = session.get("user_id")
                )

                # update the branch_inventory table
                db.execute(
                    """UPDATE branch_inventory SET quantity = quantity - :quantity
                    WHERE code = :code AND center_id = :center_id AND quantity >= 1""",
                    code = code,
                    center_id = session.get("center_id"),
                    quantity = '1',
                )
                db.execute(
                    "INSERT INTO repair_inventory (ticket_id, code) VALUES (:ticket_id, :code)",
                    ticket_id = decode_id,
                    code = code
                )

                db.execute("COMMIT")

            # get current datetime to update
            now = datetime.now()
            repair_date = now.strftime("%Y-%m-%d %H:%M:%S")
    
            db.execute(
                """UPDATE repair_table SET status = :status, repair_by = :repair_by, repair_date = :repair_date,
                repair_code = :repair_code, repair_details = :repair_details WHERE id = :id""",
                status = "Repair_completed",
                repair_by = session["user_id"],
                repair_date = repair_date,
                repair_code = repair_code,
                repair_details = repair_details,
                id = decode_id
            )
    
            return jsonify({"status": "success", "message": "The Repair ticket had been repaired!!!", "redirect": "/repair_ticket"}), 200


        except Exception as e:
            return jsonify({"status": "error", "message": f"Repair Inventory Query processing exception: {str(e)}"}), 500 
    
     