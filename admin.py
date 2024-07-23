from flask import Flask, render_template, request, redirect, url_for, flash, session,send_file
from flask_mail import Mail, Message
from pymongo import MongoClient
from itsdangerous import URLSafeTimedSerializer
import bcrypt
from datetime import datetime, date, timedelta,timezone
import socket 
import pymongo
from bson.objectid import ObjectId
from pdf_generator import main

# function from employee
from employee import employee_bp  # Import the employee blueprint


app = Flask(__name__)
app.secret_key = 'your_secret_key'


# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['hrms_db']
employees_collection = db['employees']
leave_requests_collection = db['leave_requests']
letter_requests_collection = db['letter_requests']

# Flask-Mail setup
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vaibhavgunjal283@gmail.com'
app.config['MAIL_PASSWORD'] = 'ffxa xfhj udon bbud'
app.config['MAIL_DEFAULT_SENDER'] = 'vaibhavgunjal283@gmail.com'
mail = Mail(app)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])



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
    # pending_leave_requests = list(leave_requests_collection.find({'approved': False}))
    # pending_letter_requests = list(letter_requests_collection.find({'approved': False}))

    return render_template('admin_dashboard.html', pending_employees=pending_employees)


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
        return redirect(url_for('employee.employee_dashboard'))
        
    return render_template('reset_password.html', token=token)

# # Approve leave request

# @app.route('/admin/approve_leave/<email>/<start_date>/<end_date>/<reason>', methods=['POST'])
# def approve_leave(email, start_date, end_date, reason):
#     if 'admin_email' not in session:
#         return redirect(url_for('admin_login'))
    
#     start_date = datetime.strptime(start_date, '%Y-%m-%d')
#     end_date = datetime.strptime(end_date, '%Y-%m-%d')

#     leave_request = {
#         'email': email,
#         'start_date': start_date,
#         'end_date': end_date,
#         'reason': reason
#     }

#     leave_requests_collection.update_one({
#         'email': email,
#         'start_date': start_date,
#         'end_date': end_date,
#         'reason': reason
#     }, {'$set': {'approved': True}})

#     send_leave_approval_email(leave_request)

#     flash(f'Leave request for {email} from {start_date} to {end_date} has been approved.', 'success')
#     return redirect(url_for('admin_dashboard'))


# # email send for aproval or disaproval of leave
# def send_leave_approval_email(leave_request):
#     employee = employees_collection.find_one({'email': leave_request['email']})
#     if not employee:
#         return 'Employee not found', 404

#     start_date = leave_request['start_date'].strftime('%Y-%m-%d')
#     end_date = leave_request['end_date'].strftime('%Y-%m-%d')

#     msg = Message(f'Leave Request Approved ({start_date} - {end_date})', recipients=[employee['email']])
#     msg.body = f"""Dear {employee['name']},

# Your leave request from {start_date} to {end_date} has been approved.

# Reason: {leave_request['reason']}

# Thank you,
# Absolute golbal pvt ltd.
# """
#     try:
#         mail.send(msg)
#         flash('Leave approval email sent to the employee.', 'success')
#     except socket.gaierror as e:
#         flash('Failed to send email. Network error: ' + str(e), 'danger')
#     except Exception as e:
#         flash('Failed to send email. Error: ' + str(e), 'danger')




# # disapprove the leave and there reasons

# def send_leave_disapproval_email(leave_request, reason):
#     employee = employees_collection.find_one({'email': leave_request['email']})
#     if not employee:
#         return 'Employee not found', 404

#     start_date = leave_request['start_date'].strftime('%Y-%m-%d')
#     end_date = leave_request['end_date'].strftime('%Y-%m-%d')

#     msg = Message(f'Leave Request Disapproved ({start_date} - {end_date})', recipients=[employee['email']])
#     msg.body = f"""Dear {employee['name']},

# Your leave request from {start_date} to {end_date} has been disapproved.

# Reason: {reason}

# Thank you,
# Absolute golbal pvt ltd.
# """
#     try:
#         mail.send(msg)
#         flash('Leave disapproval email sent to the employee.', 'success')
#     except socket.gaierror as e:
#         flash('Failed to send email. Network error: ' + str(e), 'danger')
#     except Exception as e:
#         flash('Failed to send email. Error: ' + str(e), 'danger')

# # route of leave disapprove 
# @app.route('/admin/disapprove_leave/<email>/<start_date>/<end_date>', methods=['GET', 'POST'])
# def disapprove_leave(email, start_date, end_date):
#     if 'admin_email' not in session:
#         return redirect(url_for('admin_login'))

#     start_date = datetime.strptime(start_date, '%Y-%m-%d')
#     end_date = datetime.strptime(end_date, '%Y-%m-%d')

#     leave_request = {
#         'email': email,
#         'start_date': start_date,
#         'end_date': end_date,
#     }

#     if request.method == 'POST':
#         reason = request.form['reason']
#         leave_requests_collection.update_one({
#             'email': email,
#             'start_date': start_date,
#             'end_date': end_date,
#         }, {'$set': {'approved': False, 'reason': reason}})

#         send_leave_disapproval_email(leave_request, reason)

#         flash(f'Leave request for {email} from {start_date} to {end_date} has been disapproved.', 'warning')
#         return redirect(url_for('admin_dashboard'))

#     return render_template('disapprove_leave.html', leave_request=leave_request)

# #  send_email_after aproval link to download
# def send_letter_email(recipient, letter_type, letter_file):
#     msg = Message(f'{letter_type.capitalize()} Letter', recipients=[recipient])
#     msg.body = 'Please find the attached letter.'
#     with app.open_resource(letter_file) as file:
#         msg.attach(letter_file, 'application/pdf', file.read())
#     mail.send(msg)

#     download_url = url_for('download_letter', letter_file=letter_file, _external=True)
#     msg.html = f'<p>Click <a href="{download_url}">here</a> to download your letter.</p>'

# #############################################################################################################
# #############################################################################################################

# # route for approve letter
# @app.route('/admin/approve_letter/<letter_id>', methods=['POST'])
# def approve_letter(letter_id):
#     if 'admin_email' not in session:
#         return redirect(url_for('admin_login'))

#     letter_request = letter_requests_collection.find_one({'_id': ObjectId(letter_id)})
#     if not letter_request:
#         flash('Letter request not found.', 'danger')
#         return redirect(url_for('admin_dashboard'))

#     # Generate the letter
#     recipient_name = letter_request['recipient_name']
#     company_name = letter_request['company_name']
#     reporting_p = letter_request['reporting_p']
#     joining_date = letter_request['joining_date']

#     main(recipient_name, company_name, reporting_p, joining_date)

#     # Update the letter request as approved
#     letter_requests_collection.update_one({'_id': ObjectId(letter_id)}, {'$set': {'approved': True}})

#     # Send the letter as an attachment via email
#     employee = employees_collection.find_one({'email': letter_request['email']})
#     send_letter_email(employee['email'], 'offer_letter', 'final_offer_letter.pdf')

#     flash('Letter request approved and sent to the employee.', 'success')
#     return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
        app.run(debug=True)