from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = './static/profile.pics'

MONGODB_URI = 'mongodb+srv://dhivy:sparta@cluster0.wxmqkbw.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(MONGODB_URI)
db = client.dbsparta_sweeterapp
SECRET_KEY = 'SPARTAA'
TOKEN_KEY = 'mytoken'

# MONGODB_URI = os.environ.get("MONGODB_URI")
# DB_NAME =  os.environ.get("DB_NAME")
# client = MongoClient(MONGODB_URI)
# db = client[DB_NAME]

@app.route("/")
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive, 
            SECRET_KEY, 
            algorithms=["HS256"]
            )

        # mengirimkan data user kembali ke client
        user_info = db.users.find_one({'username': payload.get('id')})
        return render_template("index.html", user_info=user_info)
    
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template("login.html", msg=msg)

@app.route("/user/<username>")
def user(username):
    # Mengambil informasi profil pengguna dan postingan
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # Jika ini adalah profil saya sendiri, True
        # Jika ini adalah profil orang lain, False
        status = username == payload["id"]  
        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template("user.html", user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "We could not find a user with that id/password combination",
            }
        )


@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    # Untuk mendaftar
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()

    # Menyimpan user ke database
    doc = {
        "username": username_receive,                               
        "password": password_hash,                                  
        "profile_name": username_receive,                           
        "profile_pic": "",                                          
        "profile_pic_real": "profile_pics/profile_placeholder.png", 
        "profile_info": ""                                          
    }
    db.users.insert_one(doc)
    return jsonify({"result": "success"})


@app.route("/sign_up/check_dup", methods=["POST"])
def check_dup():
    username_receive = request.form.get('username_give')
    exists = bool(db.users.find_one({'username': username_receive}))
    # print(user)
    # exists = bool(user)
    return jsonify({"result": "success", 'exists': exists})


@app.route("/update_profile", methods=["POST"])
def save_img():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # Update profil user di sini
        return jsonify({"result": "success", "msg": "Your profile has been updated"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

    # token_receive = request.cookies.get("mytoken")
    # try:
    #     payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
    #     # Buat post baru di sini
    #     return jsonify({"result": "success", "msg": "Posting successful!"})
    # except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
    #     return redirect(url_for("home"))

@app.route("/posting", methods=["POST"])
def posting():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(
            token_receive, 
            SECRET_KEY, 
            algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        comment_receive = request.form["comment_give"]
        date_receive = request.form["date_give"]

        # Menyimpan data ke dalam database
        doc = {
            "username": user_info["username"],
            "profile_name": user_info["profile_name"],
            "profile_pic_real": user_info["profile_pic_real"],
            "comment": comment_receive,
            "date": date_receive,
        }
        db.posts.insert_one(doc)
        return jsonify({"result": "success", "msg": "Posting successful!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/get_posts", methods=["GET"])
def get_posts():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # Mengambil daftar lengkap postingan
        posts = list(db.posts.find({}).sort("date", -1).limit(20))
        for post in posts:
            post["_id"] = str(post["_id"])
            post["count_heart"] = db.likes.count_documents({
                "post_id": post["_id"], 
                 "type": "heart"
                 })
            post["count_star"] = db.likes.count_documents({
                "post_id": post["_id"], 
                 "type": "star"
                 })
            post["count_thumbsup"] = db.likes.count_documents({
                "post_id": post["_id"], 
                 "type": "thumbsup"
                 })
            
            post["heart_by_me"] = bool(db.likes.find_one({
                "post_id": post["_id"], 
                "type": "heart", 
                "username": payload["id"]
                }))
            post["star_by_me"] = bool(db.likes.find_one({
                "post_id": post["_id"], 
                "type": "star", 
                "username": payload["id"]
                }))
            post["thumbsup_by_me"] = bool(db.likes.find_one({
                "post_id": post["_id"], 
                "type": "thumbsup", 
                "username": payload["id"]
                }))
        return jsonify(
            {
                "result": "success",
                "msg": "Successful fetched all posts",
                "posts": posts,
            }
        )
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/update_like", methods=["POST"])
def update_like():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(
            token_receive, 
            SECRET_KEY, 
            algorithms=["HS256"]
            )
        user_info = db.users.find_one({"username": payload.get("id")})
        post_id_receive = request.form.get["post_id_give"]
        type_receive = request.form.get["type_give"]
        action_receive = request.form.get["action_give"]
        doc = {
            "post_id": post_id_receive,
            "username": user_info.get["username"],
            "type": type_receive,
        }

        if action_receive == "like":
            db.likes.insert_one(doc)
        else:
            db.likes.delete_one(doc)

        count = db.likes.count_documents({
            "post_id": post_id_receive, 
            "type": type_receive
            })
        
        return jsonify({
            "result": "success", 
            "msg": "updated", 
            "count": count
            })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

@app.route('/secret', methods=['GET'])
def secret():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(
            token_receive, 
            SECRET_KEY, 
            algorithms=["HS256"]
            )
        user_info = db.users.find_one({'username': payload.get('id')})
        return render_template('secret.html', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)