from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from celery import Celery
from celery.result import AsyncResult
import subprocess

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
db = SQLAlchemy(app)

# Define the base directory
basedir = os.path.abspath(os.path.dirname(__file__))

# Celery configuration
celery = Celery(app.import_name,
                broker='sqla+sqlite:///' + os.path.join(basedir, 'celery.db'),
                backend='db+sqlite:///' + os.path.join(basedir, 'celery_results.db'))


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255))
    task_id = db.Column(db.String(255))  # Add a column to store Celery task ID
    # db.create_all()

@app.route('/') 
def main(): 
    return render_template("index.html") 

@celery.task(bind=True)
def convert_video(self, temp_filepath, dash_filepath):
    # cmd = ['ffmpeg',
    #        '-i', temp_filepath,
    #        '-adaptation_sets', 'id=0,streams=v',
    #        '-strict', '-2',
    #        '-f', 'dash',
    #        dash_filepath]
    cmd = ["ffmpeg",
            "-i", temp_filepath,
            "-map", "0:v",
            "-map", "0:a",
            "-adaptation_sets", "id=0,streams=v", "id=1,streams=a"
            "-strict", "-2",
            "-f", "dash",
            dash_filepath]
    
# ffmpeg -i /Users/mdali/Downloads/python/int_project/uploads/WhatsApp\ Video\ 2024-04-20\ at\ 12.23.52\ AM.mp4 -adaptation_sets id=0 streams=v -strict -2 -f dash /Users/mdali/Downloads/python/int_project/uploads/output.mpd

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    if process.returncode == 0:
        return {'status': 'completed', 'output': output.decode('utf-8')}
    else:
        return {'status': 'failed', 'output': error.decode('utf-8')}

@app.route('/upload', methods=['POST'])
def upload_videos():
    if 'videos[]' not in request.files:
        return 'No files uploaded', 400
    
    videos = request.files.getlist('videos[]')
    for video in videos:
        # Ensure uploads directory exists
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        
        # Save uploaded video temporarily
        temp_filepath = f'uploads/{video.filename}'
        video.save(temp_filepath)
        
        # Convert video to MPEG-DASH format using Celery task
        dash_filename = os.path.splitext(video.filename)[0] + '.mpd'
        print(dash_filename)
        dash_filepath = os.path.join('uploads', dash_filename)
        print(dash_filepath)
        
        task = convert_video.delay(temp_filepath, dash_filepath)
        
        # Save path and task ID to database
        video_entry = Video(path=dash_filepath, task_id=task.id)
        db.session.add(video_entry)
        db.session.commit()

    return redirect(url_for('display_videos'))

@app.route('/uploads/<path:filename>')
def serve_video(filename):
    return send_from_directory('uploads', filename)

@app.route('/upl')
def display_videos():
    videos = Video.query.all()
    return render_template("display.html", videos=videos)

@app.route('/status/<task_id>')
def task_status(task_id):
    task = AsyncResult(task_id, app=celery)
    return jsonify({'status': task.state, 'output': task.result})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
