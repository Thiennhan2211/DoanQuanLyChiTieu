from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.categories import bp
from app.models import Category

@bp.route('/list')
@login_required
def list_categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_category():
    if request.method == 'POST':
        name = request.form.get('name')
        icon = request.form.get('icon')

        if not name:
            flash("Tên loại chi tiêu không được để trống!", "danger")
            return redirect(url_for('categories.new_category'))

        cat = Category(name=name, icon=icon)
        db.session.add(cat)
        db.session.commit()
        flash("Đã thêm loại chi tiêu mới!", "success")
        return redirect(url_for('categories.list_categories'))

    return render_template('new_category.html')

@bp.route('/delete/<int:cat_id>', methods=['POST'])
@login_required
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    flash("Đã xóa loại chi tiêu!", "success")
    return redirect(url_for('categories.list_categories'))
