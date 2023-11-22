from flask import Flask, render_template, request, Response,flash,url_for,redirect
import cv2
import numpy as np
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash

import os
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 16 bytes to generate a 32-character hexadecimal string

# MongoDB Configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/UserDB'
mongo = PyMongo(app)

# User collection in MongoDB
users_collection = mongo.db.users

# Define the upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check if a file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def Cloak(background):
    net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
    classes = []
    with open("coco.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]

    # Start webcam
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # YOLO object detection
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(net.getUnconnectedOutLayersNames())

        # Post-process YOLO output
        class_ids = []
        confidences = []
        boxes = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5 and class_id == 0:  # Class ID 0 corresponds to 'person' in COCO dataset
                    # YOLO returns bounding box coordinates as a fraction of the image size
                    center_x = int(detection[0] * frame.shape[1])
                    center_y = int(detection[1] * frame.shape[0])
                    width = int(detection[2] * frame.shape[1])
                    height = int(detection[3] * frame.shape[0])

                    # Rectangle coordinates
                    x = int(center_x - width / 2)
                    y = int(center_y - height / 2)

                    boxes.append([x, y, width, height])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # Apply cloaking effect
        red_mask = np.zeros_like(frame[:, :, 0])
        for box in boxes:
            x, y, width, height = box
            red_mask[y:y + height, x:x + width] = 255

        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=2)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_DILATE, np.ones((3, 3), np.uint8), iterations=1)

        part1 = cv2.bitwise_and(background, background, mask=red_mask)
        red_free = cv2.bitwise_not(red_mask)
        part2 = cv2.bitwise_and(frame, frame, mask=red_free)
        final_output = cv2.add(part1, part2)

        # Display the final output
        cv2.imshow("Cloak", final_output)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        if users_collection.find_one({'username': username}):
            flash('Username already exists. Choose a different one.', 'error')
            return redirect(url_for('signup'))

        # Hash the password
        hashed_password = generate_password_hash(password, method='sha256')

        # Insert user into the database
        users_collection.insert_one({'username': username, 'password': hashed_password})
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Retrieve user from the database
        user = users_collection.find_one({'username': username})

        # Check if the user exists and the password is correct
        if user and check_password_hash(user['password'], password):
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        # Save the uploaded file to the server
        filename = secrets.token_hex(8) + '.' + file.filename.rsplit('.', 1)[1].lower()
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('File uploaded successfully!', 'success')
        return redirect(url_for('cloak', filename=filename))

    flash('Invalid file format', 'error')
    return redirect(request.url)

@app.route('/cloak/<filename>')
def cloak(filename):
    background = cv2.imread(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    Cloak(background)
    return render_template('cloak.html')

if __name__ == "__main__":
    app.run(debug=True)
