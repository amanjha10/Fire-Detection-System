from flask import Flask, request, send_from_directory, render_template,Response
import os
import requests
from subprocess import Popen
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from playsound import playsound
import cv2
import time
from yolov3 import detect



app = Flask(__name__)
def get_frame():
    folder_path = 'yolov3/runs/detect'
    subfolder = {f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))}
    latest_subfolder = max(subfolder, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))
    filename = predict_img.imgpath
    image_path = folder_path + '/' + latest_subfolder + '/' + filename
    video = cv2.VideoCapture(image_path)

    while True:
        success , image = video.read()
        if not success:
            break
        ret, jpeg = cv2.imencode('.jpg',image)
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n'+jpeg.tobytes()+b'\r\n\r\n')
        time.sleep(0.1)
@app.route("/video_feed")
def video_feed():
    return Response(get_frame(),
                    mimetype='multipart/x-mixed-replace;boundary=frame')

def get_public_ip():
    response = requests.get('https://api.ipify.org?format=json')
    data = response.json()
    ip_address = data.get('ip')
    return ip_address

def get_location(ip_address):
    url = f'https://ipapi.co/{ip_address}/json/'
    response = requests.get(url)
    data = response.json()

    # Extract the relevant location information
    city = data.get('city')
    region = data.get('region')
    country = data.get('country_name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    return city, region, country, latitude, longitude



# Email Configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'Your email address'
SMTP_PASSWORD = '*************'
SENDER_EMAIL = 'Your email address'
RECIPIENT_EMAIL = 'Reciever email address'

@app.route('/<path:filename>')
def display(filename):
    folder_path = 'yolov3/runs/detect'
    subfolder = {f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))}
    latest_subfolder = max(subfolder, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))
    directory = folder_path + '/' + latest_subfolder
    filename = predict_img.imgpath
    
    file_extension = filename.rsplit('.', 1)[1].lower()
    environ = request.environ
    if file_extension == "jpg":
        return send_from_directory(directory, filename)
    else:
        return "Invalid file format"

@app.route("/", methods=["GET", "POST"])
def predict_img():
    f = None  # Default value for 'f'
    detection_available = False  # Flag to track if detection is available

    if request.method == "POST":
        if 'file' in request.files:
            f = request.files['file']
            basepath = os.path.dirname(__file__)
            filepath = os.path.join(basepath, 'uploads', f.filename)
            print("Upload folder is", filepath)
            f.save(filepath)

            predict_img.imgpath = f.filename
            print("Printing predict image ::::", predict_img.imgpath)

            process = Popen(["python", "yolov3/detect.py", "--source", filepath, "--weights", "best.pt"], shell=True)
            process.wait()

            file_extension = f.filename.rsplit('.', 1)[1].lower()
            if file_extension == 'jpg':
                detection_available = True  # Set the flag to True if detection is available
            elif file_extension == "mp4":
                return video_feed()

    folder_path = 'yolov3/runs/detect'
    subfolder = {f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))}
    latest_subfolder = max(subfolder, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))

    image_path = folder_path + '/' + latest_subfolder + '/' + (f.filename if f else '')  # Use f.filename if f is not None

    if detection_available and os.path.isfile(image_path):
        ip_address = request.remote_addr
        send_email(image_path)  # Send email when detection is available
        play_siren()
        if 'file' in request.files:
            return render_template('detect.html', image_path=image_path, upload=filepath, video_feed=False)
        else:
            return render_template('detect.html', image_path=image_path, upload=filepath, video_feed=True)
    else:
        return render_template('index.html', no_detection=True)
def play_siren():
    siren_file = 'C:\\Users\\user\\OneDrive\\Desktop\\New folder (3)\\fire_alarm.mp3'
    playsound(siren_file)

def send_email(image_path):
     # Get the IP address of the request
    ip_address = get_public_ip()
    # ip_address = request.remote_addr
    
    # Get the location information
    city, region, country, latitude, longitude = get_location(ip_address)

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = 'Fire Detected'

    body = 'Fire has been detected!'
    msg.attach(MIMEText(body, 'plain'))

     # Add the location information to the email body
    location_text = f'Location: {city}, {region}, {country}\n'
    location_text += f'Latitude: {latitude}\n'
    location_text += f'Longitude: {longitude}\n'
    msg.attach(MIMEText(location_text, 'plain'))

    with open(image_path, 'rb') as f:
     img_data = f.read()
     image = MIMEImage(img_data, name=os.path.basename(image_path))
    msg.attach(image)


   


    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, text)
        server.quit()
        print("Email sent successfully")
   

    except Exception as e:
        print("Error occurred while sending email:", str(e))

if __name__ == "__main__":
    app.run(debug=True)
