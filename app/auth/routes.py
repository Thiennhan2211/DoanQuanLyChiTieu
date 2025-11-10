from flask import render_template, redirect, url_for, flash, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.auth import bp
from app.models import User, Friendship, Notification

# ------------------ ĐĂNG NHẬP ------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Đăng nhập thành công!')
            return redirect(url_for('index'))
        else:
            flash('Sai email hoặc mật khẩu.')
    return render_template('login.html')


# ------------------ ĐĂNG KÝ ------------------
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Kiểm tra xem email đã tồn tại chưa
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email đã tồn tại! Vui lòng đăng nhập hoặc dùng email khác.')
            return redirect(url_for('auth.register'))

        # Tạo user mới
        user = User(username=username, email=email,
                    password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('Đăng ký thành công! Hãy đăng nhập.')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')


# ------------------ ĐĂNG XUẤT ------------------
@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# ------------------ TRANG PROFILE CỦA BẢN THÂN ------------------
@bp.route('/profile')
@login_required
def profile():
    friends = User.query.join(Friendship, Friendship.friend_id == User.id)\
                        .filter(Friendship.user_id == current_user.id, Friendship.status == 'accepted').all()
    return render_template('profile.html', user=current_user, friends=friends)


# ------------------ TÌM KIẾM NGƯỜI DÙNG ------------------
@bp.route('/search_friends', methods=['GET'])
@login_required
def search_friends():
    query = request.args.get('q', '').strip()
    results = []

    if query:
        results = User.query.filter(
            (User.username.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%"))
        ).all()

    return render_template('search_friends.html', query=query, results=results)


@bp.route('/notifications_data')
@login_required
def notifications_data():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()

    notif_list = []
    for n in notifications:
        notif_list.append({
            "id": n.id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%d/%m/%Y %H:%M"),
            "link": n.link or "#"
        })

    return jsonify(notif_list)