import os
import sys
import cx_Oracle 
from flask import Flask, render_template, request, session, redirect, flash, url_for
from datetime import datetime
cx_Oracle.init_oracle_client(lib_dir=r"C:\oracle\instantclient_23_6")
conStr='user1/user1@localhost:1521/XE'


connection = cx_Oracle.connect(conStr)
cur=connection.cursor()

def valid_login(Matric_ID,password):
    sqlFetch = "select stud_name from gpstud where gpstud.mat_id="+Matric_ID+" AND pass_stud='"+password+"'"
    cur.execute(sqlFetch)
    user = cur.fetchone()
    if user is None:
        return False
    else:
        return user[0]
    
def Register(name,Matric_id,password):
    
    cur.callproc('StudReg',[name,Matric_id,password])
    connection.commit()
    
def AppointmentSubmit(Matric_ID,appt_date,docID):
    cur.callproc('setappointment',[Matric_ID,appt_date,docID])
    
    connection.commit()
    
def docLogin(Doc_ID,Password):
    validity = cur.callfunc('DocLogin', cx_Oracle.NUMBER, [Doc_ID, Password])
    return validity

def docName(doc_id):
    query='select doc_name from gpdoc where doc_id='+doc_id
    cur.execute(query)
    user = cur.fetchone()
    return user[0]
    
def TableQuery(mat_id):
    query = """
    SELECT a.APPT_ID, s.STUD_NAME, d.DOC_NAME, TO_CHAR(a.APPTDATE, 'DD-MON-YY') AS APPTDATE
    FROM gpappt a
    JOIN gpstud s ON a.MAT_ID = s.MAT_ID
    JOIN gpapptdoc ad ON a.APPT_ID = ad.APPT_ID
    JOIN gpdoc d ON ad.DOC_ID = d.DOC_ID
    WHERE a.MAT_ID = :mat_id
    """
    
    # Executing the query with the mat_id as a parameter
    cur.execute(query, mat_id=mat_id)
    
    # Fetching all results
    results = cur.fetchall()
    connection.commit()
    return results

def TableQuery_doc(doc_id):
    query = """
    SELECT a.APPT_ID, s.STUD_NAME, d.DOC_NAME, TO_CHAR(a.APPTDATE, 'DD-MON-YY') AS APPTDATE
    FROM gpappt a
    JOIN gpstud s ON a.MAT_ID = s.MAT_ID
    JOIN gpapptdoc ad ON a.APPT_ID = ad.APPT_ID
    JOIN gpdoc d ON ad.DOC_ID = d.DOC_ID
    WHERE d.DOC_ID = :doc_id
    """
    
    # Executing the query with the doc_id as a parameter
    cur.execute(query, doc_id=doc_id)
    
    # Fetching all results
    results = cur.fetchall()
    connection.commit()
    return results
    



connection.commit()




app = Flask(__name__, static_folder='static',template_folder='templates')
app.secret_key = 'wow'

@app.route("/")
@app.route('/login', methods=['POST','GET','Registration','Doc_Login'])
def home():

    if request.method=='GET':
        return render_template("index.html")
    if request.method=='Doc_Login':
        return render_template('Doc_login.html')
    if request.method == 'POST':
        if valid_login(request.form['Matric_ID'], request.form['password'])==False:
           return "Error"
        else:
            session['name'] ="Welcome,"+valid_login(request.form['Matric_ID'], request.form['password'])
            session['Matric_ID']=request.form['Matric_ID']
            username = session['name']
            return render_template('UserPage.html',username=username)
    
        
        
@app.route('/register', methods=['POST'])
def register():
   
    
    Register(request.form['name'],int(request.form['Matric_ID']),request.form['password'])
    flash('You have succesfully registered!', 'success')
    return render_template("index.html")

@app.route('/view-table', methods=['POST'])
def view():
    Matric_ID = session.get('Matric_ID')  
    
    
    if Matric_ID is None:
        print("Matric_ID is not available in the session!")
        return "Error: Matric_ID not set in the session."

    rows = TableQuery(Matric_ID)  # Fetch the rows using TableQuery
    
    if not rows:
        print("No rows returned from the database!")
        return "No appointments found for this student."
    
    return render_template("Table.html", rows=rows)  # Pass rows to the template

@app.route('/view-table_doc', methods=['GET', 'POST'])
def view_table_doc():
    # Retrieve Doc_ID from the session
    Doc_ID = session.get('Doc_ID')
    
    # Check if Doc_ID is available in the session
    if Doc_ID is None:
        print("Doc_ID is not available in the session!")
        return "Error: Doc_ID not set in the session."
    
    # Fetch the rows using TableQuery, now based on Doc_ID
    rows = TableQuery_doc(Doc_ID)
    
    # Handle the case where no rows are returned
    if not rows:
        print("No rows returned from the database!")
        return "No appointments found for this doctor."
    
    # Pass rows to the template for rendering
    return render_template("Table_doc.html", rows=rows)

@app.route('/delete_appointment/<int:appt_id>', methods=['POST'])
def delete_appointment(appt_id):
    cursor = connection.cursor()
    cursor.callproc('deleteappt', [appt_id])
    connection.commit()
   
    
    cursor.close()
    return redirect(url_for('view_table_doc'))

@app.route('/appt',methods=['POST'] )
def appt():
    appt_date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    Matric_ID=session['Matric_ID']
    AppointmentSubmit(int(Matric_ID),appt_date,int(request.form['doc_id']))
    
    username = session['name']
    return render_template('UserPage.html',username=username)

@app.route('/doc_login', methods=['GET', 'POST'])
def doc_login():
    if request.method == 'GET':
        return render_template("Doc_login.html")  # Render the doctor login page

    if request.method == 'POST':
        doc_id = request.form['Doc_Id']
        password = request.form['password']
        
        if docLogin(doc_id, password):  # Validate doctor login
            session['Doc_ID'] = doc_id
            session['name'] = "Welcome, " + docName(doc_id)
            username = session['name']
            return render_template('UserPage_doc.html', username=username)
        else:
            return "Error: Invalid Doctor Credentials"


@app.route('/doctor_dashboard')
def doctor_dashboard():
    doc_id = session.get('Doc_ID')
    username = session['name']
    if not doc_id:
        return redirect('/doc_login')  # Redirect to login if not logged in

    # Fetch clock-in and clock-out dates
    try:
        cur.execute("""
            SELECT leave_date, return_date
            FROM (
                SELECT leave_date, return_date
                FROM gpclockinout
                WHERE doc_id = :doc_id
                ORDER BY leave_date DESC
            ) WHERE ROWNUM = 1
        """, {'doc_id': doc_id})
        result = cur.fetchone()

        clock_in_date = result[0].strftime('%Y-%m-%d') if result and result[0] else "Not clocked in yet"
        clock_out_date = result[1].strftime('%Y-%m-%d') if result and result[1] else "Not clocked out yet"

        return render_template('UserPage_doc.html', username=username,clock_in=clock_in_date, clock_out=clock_out_date)
    except cx_Oracle.DatabaseError as e:
        return f"Error fetching clock-in/out data: {str(e)}"

@app.route('/clockout', methods=['POST'])
def clock_out():
    doc_id = session.get('Doc_ID')  # Get the logged-in doctor's ID
    if not doc_id:
        return "Error: Doctor not logged in!"

    current_date = datetime.now().date()  # Get the current date

    
    cur.callproc('clockinout', [doc_id, None, current_date])
    connection.commit()
        

    return redirect('/doctor_dashboard')

    

@app.route('/clockin', methods=['POST'])
def clock_in():
    doc_id = session.get('Doc_ID')  # Get the logged-in doctor's ID
    if not doc_id:
        return "Error: Doctor not logged in!"

    current_date = datetime.now().date()  # Get the current date

    
        # Call the `clockinout` procedure to clock in
    cur.callproc('clockinout', [doc_id, current_date, None])
    connection.commit()
       

    return redirect('/doctor_dashboard')
    
    
   

if __name__ == "__main__":
    app.run(debug=True)