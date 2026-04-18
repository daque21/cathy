<<<<<<< HEAD
from flask import Flask, request, jsonify, redirect, render_template, send_from_directory
from flask_cors import CORS
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)

UPLOAD_FOLDER = "uploaded_songs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

RECORDED_FOLDER = "recorded_audio_files"
os.makedirs(RECORDED_FOLDER, exist_ok=True)

FILES_FOLDER = "uploaded_files"
os.makedirs(FILES_FOLDER, exist_ok=True)

CORS(app)

# ✅ NEW DATABASE CONNECTION
def get_db_connection():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        sslmode="require"
    )

@app.route("/")
def home():
    return redirect("/register")

@app.route("/dashboard")
def dashboard_page():
    return render_template("sign_up.html")

@app.route("/register", methods=["POST", "GET"])
def register_account():
    db = get_db_connection()
    try:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        (user_count,) = cursor.fetchone()
        show_create_box = user_count == 0
        cursor.close()

        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO users (password_hash, created_at) VALUES (%s, NOW())",
                (data['password'],)
            )
            db.commit()
            cursor.close()
            return "SUCCESSFULLY CREATED"

    finally:
        db.close()

    return render_template("sign_up.html", show_create_box=show_create_box)

@app.route("/login", methods=["POST", "GET"])
def check_password():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        pw = data.get("password")

        db = get_db_connection()
        try:
            cursor = db.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE password_hash = %s",
                (pw,)
            )
            (count,) = cursor.fetchone()
            cursor.close()

            if count > 0:
                return "LOGIN SUCCESS"
            else:
                return "INVALID PASSWORD"
        finally:
            db.close()

    return render_template("sign_up.html")

@app.route('/upload-songs', methods=['GET', 'POST'])
def upload_songs():

    if request.method == 'POST':

        uploaded_file = request.files['song_file']
        file_name = request.form['file_name']
        file_type = request.form['file_type']

        if uploaded_file.filename != '':

            save_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(save_path)

            db = get_db_connection()
            try:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO vidsong
                    (file_name, file_path, file_type, added_at)
                    VALUES (%s,%s,%s,NOW())
                """,(file_name, save_path, file_type))
                db.commit()
                cursor.close()
            finally:
                db.close()

            return """
<script>
alert("Song uploaded successfully!");
window.location.href="/upload-songs";
</script>
"""

    db = get_db_connection()
    try:
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT file_name, file_path, file_type FROM vidsong ORDER BY added_at DESC")
        songs = cursor.fetchall()
        cursor.close()
    finally:
        db.close()

    return render_template("upload_songs.html", songs=songs)

@app.route('/uploaded_songs/<path:filename>')
def serve_song(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/saved-audio")
def saved_audio():
    db = get_db_connection()
    try:
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT audio_id, audio_name, audio_path, recorded_at FROM recorded_audio ORDER BY recorded_at DESC")
        audios = cursor.fetchall()
        cursor.close()
    finally:
        db.close()

    return render_template("saved-audio.html", audios=audios)

@app.route('/recorded_audio_files/<path:filename>')
def serve_recorded_audio(filename):
    return send_from_directory(RECORDED_FOLDER, filename)

@app.route("/save-recorded-audio", methods=["POST"])
def save_recorded_audio():
    if "audio_file" not in request.files:
        return "No file uploaded", 400

    audio_file = request.files["audio_file"]
    audio_name = request.form.get("audio_name", audio_file.filename)

    file_path = os.path.join(RECORDED_FOLDER, audio_file.filename)
    audio_file.save(file_path)

    db = get_db_connection()
    try:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO recorded_audio
            (audio_name, audio_path, recorded_at)
            VALUES (%s, %s, NOW())
        """, (audio_name, file_path))
        db.commit()
        cursor.close()
    finally:
        db.close()

    return "Audio saved successfully!"

@app.route('/files')
def files():
    db = get_db_connection()
    try:
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, file_name, file_path, upload_date FROM files ORDER BY upload_date DESC")
        files_list = cursor.fetchall()
        cursor.close()
    finally:
        db.close()

    return render_template('files.html', files=files_list)

@app.route("/upload-files", methods=["POST"])
def upload_files():
    if "fileUpload" not in request.files:
        return "No file uploaded", 400

    db = get_db_connection()
    try:
        files = request.files.getlist("fileUpload")

        for file in files:
            if file.filename == "":
                continue

            save_path = os.path.join(FILES_FOLDER, file.filename)
            file.save(save_path)

            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO files (file_name, file_path, upload_date)
                VALUES (%s, %s, NOW())
            """, (file.filename, save_path))
            db.commit()
            cursor.close()

        return "File(s) uploaded successfully!"
    finally:
        db.close()

@app.route('/folders')
def folders():
    return render_template('folders.html')

@app.route('/create-folder', methods=['POST'])
def create_folder():
    data = request.get_json()
    folder_name = data.get('folder_name')

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO folders (folder_name) VALUES (%s) RETURNING folder_id",
        (folder_name,)
    )
    folder_id = cursor.fetchone()[0]
    db.commit()

    folder_path = f"uploads/folder_{folder_id}"
    os.makedirs(folder_path, exist_ok=True)

    cursor.execute("""
        UPDATE folders SET folder_path = %s WHERE folder_id = %s
    """, (folder_path, folder_id))

    db.commit()
    cursor.close()
    db.close()

    return jsonify({
        "message": "Folder created",
        "folder_id": folder_id
    })

@app.route('/get-folders')
def get_folders():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT folder_id, folder_name FROM folders")
    folders = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(folders)

# (Remaining routes unchanged logic-wise — same pattern)
@app.route('/upload-file', methods=['POST'])
def upload_file():
    files = request.files.getlist('files')
    folder_id = request.form.get('folder_id')

    db = get_db_connection()
    cursor = db.cursor()

    for file in files:
        filename = file.filename

        # create folder directory
        folder_path = f"uploads/folder_{folder_id}"
        os.makedirs(folder_path, exist_ok=True)

        filepath = os.path.join(folder_path, filename)
        file.save(filepath)

        # SAVE SA DATABASE (IMPORTANT)
        cursor.execute("""
            INSERT INTO files (file_name, file_path, folder_id)
            VALUES (%s, %s, %s)
        """, (filename, filepath, folder_id))

    db.commit()

    cursor.close()
    db.close()

    return jsonify({"message": "Uploaded"})

@app.route('/folder/<int:folder_id>')
def open_folder(folder_id):
    return f"Folder ID: {folder_id}"
    
@app.route('/get-files/<int:folder_id>')
def get_files(folder_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT file_name,file_path FROM files WHERE folder_id = %s
    """, (folder_id,))

    files = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(files)
    
@app.route("/upload-file-to-folder", methods=["POST"])
def upload_file_to_folder():
    if "file" not in request.files:
        return jsonify({"message":"No file uploaded"}), 400

    file = request.files["file"]
    folder_id = request.form.get("folder_id")
    file_name = request.form.get("file_name")

    if not folder_id or not file_name:
        return jsonify({"message":"Missing folder or file name"}), 400

    folder_path = f"uploads/folder_{folder_id}"
    os.makedirs(folder_path, exist_ok=True)

    save_path = os.path.join(folder_path, file.filename)
    file.save(save_path)

    db = get_db_connection()
    cursor = db.cursor()

    # INSERT sa files table
    cursor.execute("""
        INSERT INTO files (file_name, file_path, folder_id)
        VALUES (%s, %s, %s)
    """, (file_name, save_path, folder_id))

    # UPDATE folders table para ma-save ang file_name
    cursor.execute("""
        UPDATE folders SET file_name = %s WHERE folder_id = %s
    """, (file_name, folder_id))

    db.commit()
    cursor.close()
    db.close()

    return jsonify({"message":"File uploaded and folder updated!"})
    
@app.route("/delete_audio/<int:audio_id>", methods=["POST"])
def delete_audio(audio_id):
    conn = get_db_connection()  # ✅ gamit imong existing connector
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    

    # Kuhaa ang audio file path
    cursor.execute(
        "SELECT audio_path FROM recorded_audio WHERE audio_id=%s",
        (audio_id,)
    )
    audio = cursor.fetchone()

    if audio:
        file_path = audio["audio_path"]

        # Delete actual file
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete sa database
        cursor.execute(
            "DELETE FROM recorded_audio WHERE audio_id=%s",
            (audio_id,)
        )
        conn.commit()

    cursor.close()
    conn.close()

    return redirect("/saved-audio")  # ✅ correct route

@app.route('/uploaded_files/<path:filename>')
def serve_uploaded_files(filename):
    return send_from_directory(FILES_FOLDER, filename)

@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory("uploads", filename)
    

import json
from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__, template_folder="templates")

# Temporary users
users = {
    "administrator": [{"username": "admin", "password": "123"}],
    "manager": [{"username": "manager1", "password": "123"}],
    "employee": [{"username": "employee1", "password": "123"}]
}

# Jobs file path
JOBS_FILE = "jobs.json"

# Load jobs from file
def load_jobs():
    try:
        with open(JOBS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Save jobs to file
def save_jobs(jobs):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f)

# Store logged in user info
logged_in_user = {"role": None, "username": None}

@app.route("/")
def home():
    return render_template("signup.html")  # or login page
@app.route("/logout", methods=["POST"])
def logout():
    logged_in_user["role"] = None
    logged_in_user["username"] = None
    return redirect(url_for("home"))

@app.route("/login/<role>", methods=["POST"])
def login(role):
    username = request.form.get("username")
    password = request.form.get("password")

    for user in users.get(role, []):
        if user["username"] == username and user["password"] == password:
            logged_in_user["role"] = role
            logged_in_user["username"] = username
            return redirect(url_for("dashboard"))
    
    return f"Invalid credentials for {role.capitalize()}."

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    role = logged_in_user["role"]
    if not role:
        return redirect(url_for("home"))

    jobs = load_jobs()  # load jobs from file

    if request.method == "POST":
        action = request.form.get("action")
        job_title = request.form.get("job_title")
        job_index = request.form.get("job_index")

        if action == "add" and role in ["administrator", "manager"]:
            jobs.append(job_title)
        elif action == "edit" and role in ["administrator", "manager"]:
            jobs[int(job_index)] = job_title
        elif action == "delete" and role == "administrator":
            jobs.pop(int(job_index))

        save_jobs(jobs)  # save updated jobs to file

    return render_template("dashboard.html", jobs=jobs, role=role)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))