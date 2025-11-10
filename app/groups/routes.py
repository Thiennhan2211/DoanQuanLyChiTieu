from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.groups import bp
from app.models import Group, User


@bp.route('/list')
@login_required
def group_list():
    groups = Group.query.filter(
        (Group.creator_id == current_user.id) | (Group.members.any(id=current_user.id))
    ).all()
    return render_template('groups.html', groups=groups)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def group_new():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Tên nhóm không được để trống.', 'danger')
            return redirect(url_for('groups.group_new'))

        new_group = Group(name=name, creator_id=current_user.id)
        new_group.members.append(current_user)
        db.session.add(new_group)
        db.session.commit()
        flash('Tạo nhóm mới thành công!', 'success')
        return redirect(url_for('groups.group_list'))

    return render_template('new_group.html')


@bp.route('/<int:group_id>/add_member', methods=['POST'])
@login_required
def add_member(group_id):
    group = Group.query.get_or_404(group_id)
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()

    if not user:
        flash('❌ Không tìm thấy người dùng với email này.', 'danger')
    elif user in group.members:
        flash('⚠️ Người này đã có trong nhóm rồi.', 'warning')
    else:
        group.members.append(user)
        db.session.commit()
        flash(f'✅ Đã thêm {user.username} vào nhóm {group.name}', 'success')

    return redirect(url_for('expenses.expense_list', group_id=group.id))


@bp.route('/<int:group_id>/remove_member/<int:user_id>', methods=['POST'])
@login_required
def remove_member(group_id, user_id):
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)

    if current_user.id != group.creator_id:
        flash("❌ Chỉ người tạo nhóm mới có thể xóa thành viên!", "danger")
        return redirect(url_for('expenses.expense_list', group_id=group_id))

    if user not in group.members:
        flash("Người dùng này không thuộc nhóm!", "warning")
    else:
        group.members.remove(user)
        db.session.commit()
        flash(f"Đã xóa {user.username} khỏi nhóm!", "success")

    return redirect(url_for('expenses.expense_list', group_id=group_id))


@bp.route('/delete/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    if group.creator_id != current_user.id:
        flash('Bạn không có quyền xóa nhóm này.', 'danger')
        return redirect(url_for('groups.group_list'))

    db.session.delete(group)
    db.session.commit()
    flash('Đã xóa nhóm thành công.', 'success')
    return redirect(url_for('groups.group_list'))
