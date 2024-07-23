from datetime import datetime, timedelta, date, timezone
from io import BytesIO
from jinja2 import Template
from weasyprint import HTML
import tempfile
import os
from datetime import datetime

from flask import (
    Flask, Blueprint, render_template, request, redirect, 
    url_for, flash, session, send_file, make_response
)
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from bson.errors import InvalidId
from bson.tz_util import utc

import bcrypt
import socket

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from pdf_generator import main

def convert_to_mongodb_compatible(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, ObjectId):
        return str(obj)
    return obj

app = Flask(__name__)
app.secret_key = 'your_secret_key'



# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['hrms_db']
employees_collection = db['employees']
leave_requests_collection = db['leave_requests']
letter_requests_collection = db['letter_requests']
attendance_collection = db['attendance_request']
salary_slip_collection = db['salary_slip_collection']

# Flask-Mail setup
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vaibhavgunjal283@gmail.com'
app.config['MAIL_PASSWORD'] = 'avwm cxbw yuwe gdkk'
app.config['MAIL_DEFAULT_SENDER'] = 'vaibhavgunjal283@gmail.com'
mail = Mail(app)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

@app.route('/employee dashboard', methods=['GET', 'POST'])
def employee_dashboard():
    return render_template('index_1.html')


# Employee registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        position = request.form['position']
        date_of_joining = request.form['date_of_joining']
        
        # Check if email already exists
        if employees_collection.find_one({'email': email}):
            flash('Email already registered. Please use a different email.', 'error')
            return redirect(url_for('register'))

        employees_collection.insert_one({
            'name': name,
            'email': email,
            'position': position,
            'date_of_joining': date_of_joining,
            'role': 'employee',
            'approved': False
        })
        flash('Registration successful. Awaiting admin approval.', 'success')
        return redirect(url_for('register'))
    return render_template('register.html')


# login employee
@app.route('/', methods=['GET', 'POST'])
def login():
    

    print("Login route accessed")  # Check if this prints in the console
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Debugging: print email and password
        print(f"Email: {email}, Password: {password}")
        
        employee = employees_collection.find_one({'email': email, 'role': 'employee', 'approved': True})
        
        # Debugging: check if employee exists
        if employee:
            print(f"Employee found: {employee}")
        else:
            print("Employee not found or not approved")

        if employee and bcrypt.checkpw(password.encode('utf-8'), employee['password']):
            session['email'] = email
            # Debugging: print session email
            print(f"Session email set: {session['email']}")
            flash('You have logged in successfully!', 'success')

            return redirect(url_for('employee_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            # Debugging: invalid login attempt
            print("Invalid email or password")
    
    return render_template('login.html')



# Leave application

@app.route('/leave', methods=['GET', 'POST'])
def leave():
    if 'email' not in session:
        flash('Please login first to access the leave form.', 'warning')
        return redirect(url_for('login'))

    email = session['email']
    leave_requests = list(leave_requests_collection.find({'email': email}))

    # Calculate total days used
    total_days_used = sum((req['end_date'] - req['start_date']).days + 1 
                          for req in leave_requests if req['approved'])

    # Calculate total leaves remaining for the year
    total_leaves_per_year = 24  #  24 leaves per year
    total_leaves_remaining = total_leaves_per_year - total_days_used

    # Calculate leaves used and remaining for the current month
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year

    days_used_this_month = sum(
        (min(req['end_date'], current_date) - max(req['start_date'], current_date.replace(day=1))).days + 1
        for req in leave_requests
        if req['approved'] and req['start_date'].year == current_year 
        and req['start_date'].month <= current_month 
        and req['end_date'].month >= current_month
    )

    

    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        reason = request.form['reason']

        days_requested = (end_date - start_date).days + 1

        print(f"Total leaves remaining: {total_leaves_remaining}")
        print(f"Days requested: {days_requested}")

        if days_requested > total_leaves_remaining:
            flash('You have exceeded your annual leave limit.', 'error')
        

        else:
            leave_requests_collection.insert_one({
                'email': email,
                'start_date': start_date,
                'end_date': end_date,
                'reason': reason,
                'approved': False
            })
            flash('Leave request submitted. Awaiting admin approval.', 'success')

        return redirect(url_for('employee_dashboard'))

    return render_template('leave.html',
                           total_leaves_remaining=total_leaves_remaining,
                           leave_requests=leave_requests)



@app.route('/employee/weekly_attendance', methods=['GET', 'POST'])
def employee_weekly_attendance():
    if 'email' not in session:
        return redirect(url_for('login'))

    employee_email = session['email']

    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    else:
        # Default to current week
        start_date = datetime.now() - timedelta(days=datetime.now().weekday())

    end_date = start_date + timedelta(days=6)

    # Convert dates to string format for query
    start_date_str = start_date.strftime('%Y-%m-%dT00:00:00')
    end_date_str = end_date.strftime('%Y-%m-%dT23:59:59')

    # Query the database for the employee's attendance records for the week
    weekly_attendance = list(attendance_collection.find({
        'email': employee_email,
        'date': {
            '$gte': start_date_str,
            '$lte': end_date_str
        }
    }).sort('date', 1))

    print(f"Query parameters: email={employee_email}, start_date={start_date_str}, end_date={end_date_str}")
    print(f"Query results: {weekly_attendance}")

    # Calculate total hours worked for the week
    total_hours = sum(float(record.get('hours_worked', 0)) for record in weekly_attendance)

    # Format the attendance records for display
    formatted_attendance = []
    for record in weekly_attendance:
        formatted_attendance.append({
            'date': datetime.strptime(record['date'], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d'),
            'present': 'Yes' if record.get('present', False) else 'No',
            'login_time': record.get('login_time', '-'),
            'logout_time': record.get('logout_time', '-'),
            'hours_worked': float(record.get('hours_worked', 0))
        })

    # If no records found, flash a message
    if not formatted_attendance:
        flash('No attendance records found for the selected week.', 'info')

    return render_template('employee_weekly_attendance.html', 
                           weekly_attendance=formatted_attendance,
                           start_date=start_date,
                           end_date=end_date,
                           total_hours=total_hours)
# route to drop down list
@app.route('/list-document',methods = ['GET', 'POST'])
def document_1():
    if 'email' not in session:
        flash('Please login first to access the document form.', 'warning')
        return redirect(url_for('employee_dashboard'))
    
    if request.method == 'POST':
        document_type = request.form['document-type']
        # Process the selected document type
        # For example, you can redirect to different routes based on the document type
        if document_type == 'letter':
            return redirect(url_for('documents'))
        elif document_type == 'salary_slip':
            return redirect(url_for('salary_slip'))
        elif document_type == 'report':
            return redirect(url_for('report'))
        # Add more conditions for other document types

    # If it's a GET request, render the HTML template
    return render_template('document_1.html')

# letter request
@app.route('/list-document/letter', methods=['GET', 'POST'])
def documents():
    if 'email' not in session:
        flash('Please login first to access the document form.', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        recipient_name = request.form['recipient_name']
        company_name = request.form['company_name']
        reporting_p = request.form['reporting_p']
        joining_date = request.form['joining_date']

        letter_requests_collection.insert_one({
            'email': session['email'],
            'recipient_name': recipient_name,
            'company_name': company_name,
            'reporting_p': reporting_p,
            'joining_date': joining_date,
            'letter_type': 'offer_letter',
            'approved': False,
            'generated_at': datetime.now(timezone.utc)
        })
        flash('Letter request submitted. Awaiting admin approval.', 'success')
        return redirect(url_for('letter_success'))  # Redirect to the success page
    return render_template('index1.html')

@app.route('/letter_success', methods=['GET'])
def letter_success():
    if 'email' not in session:
        return redirect(url_for('employee_dashboard'))
    return render_template('letter_success.html')
@app.route('/salary_slip', methods=['GET', 'POST'])
def salary_slip():
    if 'email' not in session:
        flash('Please login first to access the document form.', 'warning')
        return redirect(url_for('login'))
    
    # Fetch employee data from the database
    employee = employees_collection.find_one({'email': session['email']})
    if not employee:
        flash('Employee data not found.', 'error')
        return redirect(url_for('employee_dashboard'))

    if request.method == 'POST':
        employeeName = employee['name']
        employeeId = str(employee['_id'])  # Assuming _id is used as employee ID
        gross_salary = request.form['grossSalary']
        month = request.form['month']
        days_attended = request.form['daysAttended']

        # Convert month format
        month_date = datetime.strptime(month, '%Y-%m')
        formatted_month = month_date.strftime('%B - %Y')

        salary_slip_collection.insert_one({
            'email': session['email'],
            'employeeName': employeeName,
            'employeeId': employeeId,
            'grossSalary': gross_salary,
            'month': formatted_month,
            'dateOfJoining': employee['date_of_joining'],
            'designation': employee['position'],
            'daysAttended': days_attended,
            'letter_type': 'salary_slip',
            'approved': False,
            'generated_at': datetime.now(timezone.utc)
        })
        flash('Salary slip request submitted. Awaiting admin approval.', 'success')
        return redirect(url_for('letter_success'))
    
    return render_template('salarysliprequest.html', employee=employee)

@app.route('/logout')
def logout():
    if 'email' in session:
        session.pop('email', None)
        flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))



# ##################################################################################################################################################################


# Admin login    
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin = employees_collection.find_one({'email': email, 'role': 'admin'})
        if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password']):
            session['admin_email'] = email
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('admin_login.html')

# Admin dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    pending_employees = list(employees_collection.find({'approved': False}))
    pending_leave_requests = list(leave_requests_collection.find({'approved': False}))
    pending_letter_requests = list(letter_requests_collection.find({'approved': False}))
    pending_salary_slip_requests = list(salary_slip_collection.find({'approved': False}))

    all_employees = list(employees_collection.find({'approved': True}))
    
    return render_template('admin_dashboard.html', 
                           pending_employees=pending_employees,
                           pending_leave_requests=pending_leave_requests, 
                           pending_letter_requests=pending_letter_requests,
                           pending_salary_slip_requests=pending_salary_slip_requests,
                           all_employees=all_employees)


## Approve employee registration
@app.route('/admin/approve_employee/<email>', methods=['POST'])
def approve_employee(email):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    employees_collection.update_one({'email': email}, {'$set': {'approved': True}})
    send_login_credentials(email)
    flash(f'Employee with email {email} has been approved.', 'success')
    return redirect(url_for('admin_dashboard'))



# email sending process for employee regestration

def generate_reset_token(email):
    return serializer.dumps(email, salt='password-reset-salt')

def send_login_credentials(email):
    employee = employees_collection.find_one({'email': email})
    if not employee:
        return 'Employee not found', 404

    token = generate_reset_token(email)
    reset_url = url_for('reset_password', token=token, _external=True)

    msg = Message('Login Credentials', recipients=[email])
    msg.body = f"""Dear {employee['name']},

Your registration has been approved. Click the link below to set your password and access your account:

{reset_url}

If you did not request this email, please ignore it.

Thank you,
Absolute golbal pvt ltd.
"""
    try:
        mail.send(msg)
        flash('Login credentials sent to the employee.', 'success')
    except socket.gaierror as e:
        flash('Failed to send email. Network error: ' + str(e), 'danger')
    except Exception as e:
        flash('Failed to send email. Error: ' + str(e), 'danger')

# reset password with link
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form['password']
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        employees_collection.update_one({'email': email}, {'$set': {'password': hashed_password}})
        flash('Your password has been updated!', 'success')
        
        # Create a new session for the employee
        session['email'] = email
        
        # Redirect to employee dashboard after password reset
        return redirect(url_for('employee_dashboard'))
        
    return render_template('reset_password.html', token=token)

# Approve leave request

@app.route('/admin/approve_leave/<email>/<start_date>/<end_date>/<reason>', methods=['POST'])
def approve_leave(email, start_date, end_date, reason):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    leave_request = {
        'email': email,
        'start_date': start_date,
        'end_date': end_date,
        'reason': reason
    }

    leave_requests_collection.update_one({
        'email': email,
        'start_date': start_date,
        'end_date': end_date,
        'reason': reason
    }, {'$set': {'approved': True}})

    send_leave_approval_email(leave_request)

    return redirect(url_for('admin_dashboard'))


# email send for aproval or disaproval of leave
def send_leave_approval_email(leave_request):
    employee = employees_collection.find_one({'email': leave_request['email']})
    if not employee:
        return 'Employee not found', 404

    start_date = leave_request['start_date'].strftime('%Y-%m-%d')
    end_date = leave_request['end_date'].strftime('%Y-%m-%d')

    msg = Message(f'Leave Request Approved ({start_date} - {end_date})', recipients=[employee['email']])
    msg.body = f"""Dear {employee['name']},

Your leave request from {start_date} to {end_date} has been approved.

Reason: {leave_request['reason']}

Thank you,
Absolute golbal pvt ltd.
"""
    try:
        mail.send(msg)
        flash('Leave approval email sent to the employee.', 'success')
    except socket.gaierror as e:
        flash('Failed to send email. Network error: ' + str(e), 'danger')
    except Exception as e:
        flash('Failed to send email. Error: ' + str(e), 'danger')




# disapprove the leave and there reasons

def send_leave_disapproval_email(leave_request, reason):
    employee = employees_collection.find_one({'email': leave_request['email']})
    if not employee:
        return 'Employee not found', 404

    start_date = leave_request['start_date'].strftime('%Y-%m-%d')
    end_date = leave_request['end_date'].strftime('%Y-%m-%d')

    msg = Message(f'Leave Request Disapproved ({start_date} - {end_date})', recipients=[employee['email']])
    msg.body = f"""Dear {employee['name']},

Your leave request from {start_date} to {end_date} has been disapproved.

Reason: {reason}

Thank you,
Absolute golbal pvt ltd.
"""
    try:
        mail.send(msg)
        flash('Leave disapproval email sent to the employee.', 'success')
    except socket.gaierror as e:
        flash('Failed to send email. Network error: ' + str(e), 'danger')
    except Exception as e:
        flash('Failed to send email. Error: ' + str(e), 'danger')

# route of leave disapprove 
@app.route('/admin/disapprove_leave/<email>/<start_date>/<end_date>', methods=['GET', 'POST'])
def disapprove_leave(email, start_date, end_date):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))

    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    leave_request = {
        'email': email,
        'start_date': start_date,
        'end_date': end_date,
    }

    if request.method == 'POST':
        reason = request.form['reason']
        leave_requests_collection.update_one({
            'email': email,
            'start_date': start_date,
            'end_date': end_date,
        }, {'$set': {'approved': False, 'reason': reason}})

        send_leave_disapproval_email(leave_request, reason)

        return redirect(url_for('admin_dashboard'))

    return render_template('disapprove_leave.html', leave_request=leave_request)


@app.route('/download/<letter_file>')
def download_letter(letter_file):
    try:
        return send_file(letter_file, as_attachment=True)
    except Exception as e:
        return str(e)




def send_letter_email(recipient, letter_type, letter_file):
    # Generate a formal subject line
    subject = f'{letter_type.capitalize()} Letter from Absolute Global PVT Ltd.'

    # Create the plain text body of the email
    plain_body = f"""
Dear Dear {recipient},
We are pleased to inform you that your {letter_type} request has been approved. Please find the attached {letter_type} for your records.

If you have any questions or need further assistance, please do not hesitate to contact us.

Best regards,
Absolute Global PVT Ltd
"""

    # Create the HTML body of the email
    download_url = url_for('download_letter', letter_file=letter_file, _external=True)
    html_body = f"""
<p>Dear {recipient},</p>

<p>We are pleased to inform you that your {letter_type} request has been approved. Please find the attached {letter_type} for your records.</p>

<p>If you have any questions or need further assistance, please do not hesitate to contact us.</p>

<p>Best regards,<br>
Absolute Global PVT Ltd
</p>

<p>Click <a href="{download_url}">here</a> to download your letter.</p>
"""

    # Create the email message
    msg = Message(subject, recipients=[recipient])
    msg.body = plain_body
    msg.html = html_body

    # Attach the PDF letter
    with app.open_resource(letter_file) as file:
        msg.attach(letter_file, 'application/pdf', file.read())

    # Send the email
    mail.send(msg)




# #############################################################################################################
# #############################################################################################################

# # route for approve letter
@app.route('/admin/approve_letter/<letter_id>', methods=['POST'])
def approve_letter(letter_id):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))

    letter_request = letter_requests_collection.find_one({'_id': ObjectId(letter_id)})
    if not letter_request:
        flash('Letter request not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Generate the letter
    recipient_name = letter_request['recipient_name']
    company_name = letter_request['company_name']
    reporting_p = letter_request['reporting_p']
    joining_date = letter_request['joining_date']

    main(recipient_name, company_name, reporting_p, joining_date)

    # Update the letter request as approved
    letter_requests_collection.update_one({'_id': ObjectId(letter_id)}, {'$set': {'approved': True}})

    # Send the letter as an attachment via email
    employee = employees_collection.find_one({'email': letter_request['email']})
    send_letter_email(employee['email'], 'offer_letter', 'final_offer_letter.pdf')

    flash('Letter request approved and sent to the employee.', 'success')
    return redirect(url_for('admin_dashboard'))


from datetime import datetime, timedelta

@app.route('/admin/fill_attendance', methods=['GET', 'POST'])
def fill_attendance():
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        attendance_date = datetime.strptime(request.form['attendance_date'], '%Y-%m-%d')
        all_employees = list(employees_collection.find({'approved': True}))
        
        for employee in all_employees:
            email = employee['email']
            present = request.form.get(f'present_{email}') == '1'
            login_time = request.form.get(f'login_{email}')
            logout_time = request.form.get(f'logout_{email}')
            
            # Calculate hours worked
            hours_worked = 0
            if present and login_time and logout_time:
                login_datetime = datetime.strptime(login_time, '%H:%M')
                logout_datetime = datetime.strptime(logout_time, '%H:%M')
                
                # Handle case where logout is on the next day
                if logout_datetime < login_datetime:
                    logout_datetime += timedelta(days=1)
                
                time_difference = logout_datetime - login_datetime
                hours_worked = round(time_difference.total_seconds() / 3600, 2)  # Convert to hours and round to 2 decimal places
            
            attendance_data = {
                'email': email,
                'date': attendance_date,
                'present': present,
                'login_time': login_time,
                'logout_time': logout_time,
                'hours_worked': hours_worked
            }
            
            # Convert all values to MongoDB-compatible format
            attendance_data = {k: convert_to_mongodb_compatible(v) for k, v in attendance_data.items()}
            
            attendance_collection.insert_one(attendance_data)
        
        flash('Attendance submitted successfully', 'success')
        return redirect(url_for('admin_dashboard'))
    
    all_employees = list(employees_collection.find({'approved': True}))
    return render_template('fill_attendance.html', all_employees=all_employees)



@app.route('/admin/download_attendance_pdf', methods=['POST'])
def download_attendance_pdf():
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))

    attendance_date_str = request.form['attendance_date']
    attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d')

    # Create a date range for the entire day
    start_of_day = attendance_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    # Convert to UTC for MongoDB query
    start_of_day_utc = start_of_day.replace(tzinfo=utc)
    end_of_day_utc = end_of_day.replace(tzinfo=utc)

    attendance_records = list(attendance_collection.find({
        'date': {
            '$gte': start_of_day_utc.strftime("%Y-%m-%dT%H:%M:%S"),
            '$lt': end_of_day_utc.strftime("%Y-%m-%dT%H:%M:%S")
        }
    }))

    # Prepare data for PDF
    data = [['Employee Name', 'Present', 'Login Time', 'Logout Time', 'Hours Worked']]
    for record in attendance_records:
        employee = employees_collection.find_one({'email': record['email']})
        data.append([
            employee['name'] if employee else record['email'],
            'Present' if record['present'] else 'Absent',
            record.get('login_time', '-'),
            record.get('logout_time', '-'),
            record.get('hours_worked', '-')
        ])

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Create table
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(t)
    doc.build(elements)

    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_{attendance_date_str}.pdf'
    return response




@app.route('/admin/view_attendance', methods=['GET', 'POST'])
def view_attendance():
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        attendance_date_str = request.form['attendance_date']
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d')

        # Create a date range for the entire day
        start_of_day = attendance_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        # Convert to UTC for MongoDB query
        start_of_day_utc = start_of_day.replace(tzinfo=utc)
        end_of_day_utc = end_of_day.replace(tzinfo=utc)

        try:
            attendance_records = list(attendance_collection.find({
                'date': {
                    '$gte': start_of_day_utc.strftime("%Y-%m-%dT%H:%M:%S"),
                    '$lt': end_of_day_utc.strftime("%Y-%m-%dT%H:%M:%S")
                }
            }))

            attendance_data = []
            for record in attendance_records:
                employee = employees_collection.find_one({'email': record['email']})
                attendance_data.append({
                    'name': employee['name'] if employee else record['email'],
                    'present': 'Present' if record['present'] else 'Absent',
                    'login_time': record.get('login_time', '-'),
                    'logout_time': record.get('logout_time', '-'),
                    'hours_worked': record.get('hours_worked', '-')
                })

            return render_template('view_attendance.html',
                                   attendance_date=attendance_date_str,
                                   attendance_data=attendance_data)
        except Exception as e:
            print(f"Error: {e}")
            return render_template('view_attendance.html', error="An error occurred while fetching attendance data.")

    return render_template('view_attendance.html')







def calculate_salary_components(gross_salary):
    basic_salary = round(0.5 * gross_salary)
    hra = round(0.5 * basic_salary)
    special_allowance = round(0.1 * basic_salary)
    conveyance = gross_salary - basic_salary - hra - special_allowance
    professional_tax = 200 
    
    total_income = basic_salary + hra + special_allowance + conveyance
    total_deduction = professional_tax
    net_salary = total_income - total_deduction

    return {
        'basic_salary': basic_salary,
        'hra': hra,
        'special_allowance': special_allowance,
        'conveyance': conveyance,
        'professional_tax': professional_tax,
        'total_income': total_income,
        'total_deduction': total_deduction,
        'net_salary': net_salary
    }

def generate_salary_slip(salary_slip_request):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, 'templates', 'salary_slip_template.html')
    with open(template_path, 'r') as file:
        template_str = file.read()

    template = Template(template_str)

    gross_salary = float(salary_slip_request.get('grossSalary', 0))
    salary_components = calculate_salary_components(gross_salary)

    data = {
        'month': salary_slip_request.get('month', ''),
        'employee_name': salary_slip_request.get('employeeName', ''),
        'employee_id': salary_slip_request.get('employeeId', ''),
        'date_of_joining': salary_slip_request.get('dateOfJoining', 'N/A'),
        'designation': salary_slip_request.get('designation', 'N/A'),
        'total_working_days': salary_slip_request.get('totalWorkingDays', '30'),
        'days_attended': salary_slip_request.get('daysAttended', '30'),
        'basic_salary': salary_components['basic_salary'],
        'special_allowance': salary_components['special_allowance'],
        'hra': salary_components['hra'],
        'tiffin_allowance': 0,
        'conveyance': salary_components['conveyance'],
        'assistant_allowance': 0,
        'medical_allowance': 0,
        'pf': 0,
        'professional_tax': salary_components['professional_tax'],
        'tds': 0,
        'total_income': salary_components['total_income'],
        'total_deduction': salary_components['total_deduction'],
        'net_salary': salary_components['net_salary']
    }

    rendered_html = template.render(data)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        HTML(string=rendered_html, base_url='.').write_pdf(tmp.name)

    return tmp.name


@app.route('/admin/approve_salary_slip/<request_id>', methods=['POST'])
def approve_salary_slip(request_id):
    if 'admin_email' not in session:
        return redirect(url_for('admin_login'))

    try:
        salary_slip_request = salary_slip_collection.find_one({'_id': ObjectId(request_id)})
        if not salary_slip_request:
            flash('Salary slip request not found.', 'danger')
            return redirect(url_for('admin_dashboard'))

        required_fields = ['grossSalary', 'month', 'employeeName', 'employeeId', 'email']
        for field in required_fields:
            if field not in salary_slip_request:
                flash(f'Missing required field: {field}', 'danger')
                return redirect(url_for('admin_dashboard'))

        pdf_path = generate_salary_slip(salary_slip_request)

        salary_slip_collection.update_one({'_id': ObjectId(request_id)}, {'$set': {'approved': True}})

        send_salary_slip_email(salary_slip_request, pdf_path)

        os.unlink(pdf_path)

        flash('Salary slip request approved and sent to the employee.', 'success')
    except KeyError as e:
        flash(f'Error: Missing key in salary slip request: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Error approving salary slip request: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))

def send_salary_slip_email(salary_slip_request, pdf_path):
    employee_email = salary_slip_request['email']
    employee_name = salary_slip_request['employeeName']
    month = salary_slip_request['month']

    subject = f'Salary Slip for {month}'
    body = f"""
    Dear {employee_name},

    Your salary slip for {month} has been generated and is attached to this email.

    If you have any questions, please contact the HR department.

    Best regards,
    Absolute Global PVT Ltd
    """

    msg = Message(subject, recipients=[employee_email])
    msg.body = body

    with open(pdf_path, 'rb') as file:
        msg.attach('salary_slip.pdf', 'application/pdf', file.read())

    mail.send(msg)

@app.route('/admin/logout')
def admin_logout():
    if 'admin_email' in session:
        session.pop('admin_email', None)
        flash('You have been logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
        app.run(debug=True)















