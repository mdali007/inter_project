from flask import Flask, request, render_template, send_from_directory, redirect, url_for
import os
app = Flask(__name__)

@app.route('/') 
def main(): 
    return render_template("index.html") 

@app.route('/upload', methods=['POST'])
def upload_videos():
    if 'videos[]' not in request.files:
        return 'No files uploaded', 400
        
    converted_video_paths = []  # Store paths of converted videos
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
        cmd = f'ffmpeg -i {temp_filepath} -f dash -seg_duration 10 -init_seg_name init.m4s -media_seg_name segment_$Number$.m4s {dash_filepath}'
        os.system(cmd)

        # Remove temporary video file
        os.remove(temp_filepath)
        
        # Append the path to the list
        converted_video_paths.append(dash_filepath)

    # Redirect to display_videos route and pass the list of paths
    return redirect(url_for('display_videos', converted_videos=converted_video_paths))

@app.route('/uploads/<path:filename>')
def serve_video(filename):
    return send_from_directory('uploads', filename)

@app.route('/upl')
def display_videos():
    converted_videos = request.args.getlist('converted_videos')
    return render_template("display.html", converted_videos=converted_videos)

if __name__ == '__main__':
    app.run(debug=True)
