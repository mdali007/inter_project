from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
import subprocess

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
db = SQLAlchemy(app)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255))

@app.route('/') 
def main(): 
    return render_template("index.html") 

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
        
        # Convert video to MPEG-DASH format using ffmpeg
        dash_filename = os.path.splitext(video.filename)[0] + '.mpd'
        dash_filepath = os.path.join('uploads', dash_filename)
        
        cmd = ['ffmpeg',
               '-i', temp_filepath,
               '-adaptation_sets', 'id=0,streams=v',
               '-strict', '-2',
               '-f', 'dash',
               dash_filepath]
        
        subprocess.Popen(cmd)

        # Remove temporary video file
        os.remove(temp_filepath)
        
        # Save path to database
        video_entry = Video(path=dash_filepath)
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
