from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt
import jwt
import datetime
from werkzeug.utils import secure_filename
from mysql.connector import Binary
import os  # Import the os module

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = 'yogeswari'

# Additional configuration for file upload to a separate database
db_config = {
   'host': 'localhost',
   'user': 'root',
   'password': 'newp',
   'database': 'data_base'
}

def connect_to_mysql():
   try:
      conn = mysql.connector.connect(**db_config)
      if conn.is_connected():
         print(f'Connected to MySQL database')
         return conn
   except Error as e:
      print(e)

def close_connection(conn):
   if conn.is_connected():
      conn.close()
      print('Connection to MySQL database closed')

def save_files_to_database(userid, file_names):
   try:
      conn = mysql.connector.connect(**db_config)
      print("Connected to MySQL")
      cursor = conn.cursor()

      for file_name in file_names:
         with open(file_name, 'rb') as file:
               image_data = file.read()
               # Insert each image separately
               cursor.execute('''
                  INSERT INTO i_mages (userid, image)
                  VALUES (%s, %s)
               ''', (userid, Binary(image_data)))
               conn.commit()


      flash('Files saved to the database successfully', 'success')

   except Error as e:
      flash(f'Error saving files to the database: {str(e)}', 'error')

   finally:
      cursor.close()
      close_connection(conn)



@app.route('/')
def index():
   return render_template('index.html')

@app.route('/signup', methods=['POST','GET'])
def signup():
   conn = connect_to_mysql()
   cursor = conn.cursor(dictionary=True)
   if request.method == 'POST':
      username = request.form['username']
      email = request.form['email']
      fullname = request.form['fullname']
      password = request.form['password']

      # Check if the username or email already exists
      cursor.execute("SELECT * FROM t_able WHERE username = %s OR email = %s", (username, email))
      existing_user = cursor.fetchone()
      if existing_user:
         close_connection(conn)
         error_message = 'Username or email already exists'
         return render_template('index.html', error_message=error_message)

      # Hash the password
      hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

      # Insert the new user into the database
      insert_query = "INSERT INTO t_able (username, email, fullname, password) VALUES (%s, %s, %s, %s)"
      user_data = (username, email, fullname, hashed_password)
      cursor.execute(insert_query, user_data)
      conn.commit()

      # Retrieve the userid of the newly signed up user
      cursor.execute("SELECT userid FROM t_able WHERE username = %s", (username,))
      new_user = cursor.fetchone()
      if new_user:
         session['userid'] = new_user['userid']

      close_connection(conn)
      return redirect(url_for('mult_image'))  # Redirect to the success route

   return render_template('index.html', error_message=None)

@app.route('/login', methods=['POST','GET'])
def login():
   conn = connect_to_mysql()
   cursor = conn.cursor(dictionary=True)

   username = request.form['username']
   password = request.form['password']

   # Query the user from the database
   cursor.execute("SELECT * FROM t_able WHERE username = %s", (username,))
   user = cursor.fetchone()

   if user and bcrypt.check_password_hash(user['password'], password):
      # Generate JWT token
      session['username'] = username
      session['userid'] = user['userid']
      close_connection(conn)
      return redirect(url_for('user_profile'))
   else:
      error_message = 'Invalid username or password'
      return render_template('index.html', error_message=error_message)


@app.route('/user_profile', methods=['GET'])
def user_profile():
   # session['username']=username
   # Check if user is logged in
   if 'username' not in session:
      return redirect(url_for('login'))  # Redirect to login page if user is not logged in

   # Retrieve logged-in user's details from database
   conn = connect_to_mysql()
   cursor = conn.cursor(dictionary=True)
   username = session['username']

   cursor.execute("SELECT * FROM t_able WHERE username = %s", (username,))
   user = cursor.fetchone()

   # Retrieve all images for the logged-in user
   userid = user['userid']
   cursor.execute("SELECT imageid, image FROM i_mages WHERE userid = %s", (userid,))
   images_data = cursor.fetchall()

   # Create a list to store the image file names
   image_files = []

# Get the current script's directory
   current_directory = os.path.dirname(__file__)
   # Specify the path to the 'static' folder relative to the script's directory
   static_folder_path = os.path.join(current_directory, 'static')
   # Save the image data to temporary files and store their filenames in the list
   for image_data in images_data:
      imageid = image_data['imageid']
      file_name = f'temp_{imageid}.jpg'
      file_path = os.path.join(static_folder_path, file_name)  # Use os.path.join to create the full path
      with open(file_path, 'wb') as file:
         file.write(image_data['image'])
      image_files.append(file_name)

   conn.close()

   # Render user profile template with user's details
   return render_template('profile.html', user=user, image_files=image_files)


# Route to serve the images from the temporary folder
@app.route('/uploads/<filename>')
def uploaded_file(filename):
   return send_file(os.path.join(app.root_path, 'static', filename))


@app.route('/upload_files', methods=['POST'])
def upload_files():
 # Retrieve userid from the session
   userid = session.get('userid')
   if not userid:
      flash('User not logged in', 'error')
      return redirect(url_for('login'))  
    
   image_files = request.files.getlist('image')

   if image_files:
      file_names = []

      for image_file in image_files:
         file_name = secure_filename(image_file.filename)
         image_file.save(file_name)
         file_names.append(file_name)

      save_files_to_database(userid, file_names)

      flash('Files uploaded and saved to the database successfully', 'success')

   return 'Files uploaded successfully'


@app.route('/mult_image')
def mult_image():
   return render_template('multImag.html')

@app.route('/video')
def video():
   return render_template('video.html')

if __name__ == '__main__':
   app.run(debug=True)