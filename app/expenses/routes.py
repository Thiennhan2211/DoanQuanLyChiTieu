from flask import render_template, request, redirect, url_for, flash, Response, send_file, current_app
from flask_login import login_required, current_user
from app import db
from app.expenses import bp
from app.models import Expense, Group, Notification, User, ExpenseShare
from io import BytesIO
from datetime import datetime, date
from openpyxl import Workbook
from sqlalchemy import func
from app.utils.exchange_rate import get_exchange_rate


def get_exchange_rate_to_vnd(currency):
    """
    Trả về tỷ giá 1 <currency> = X VND (cố định)
    Ví dụ: 1 USD = 25,000 VND
    """
    fixed_rates = {
        "VND": 1.0,
        "USD": 25000.0,
        "EUR": 27000.0,
        "JPY": 170.0,
        "KRW": 20.0,
        "SGD": 18000.0,
        "THB": 700.0
    }

    cur = (currency or "VND").upper()
    return fixed_rates.get(cur, 1.0)  


@bp.route('/<int:group_id>/list')
@login_required
def expense_list(group_id):
    group = Group.query.get_or_404(group_id)

    q = Expense.query.filter_by(group_id=group_id)
    _from = request.args.get('from')
    _to = request.args.get('to')
    user_id = request.args.get('user_id')

    if _from:
        try:
            from_dt = datetime.strptime(_from, '%Y-%m-%d')
            q = q.filter(Expense.date >= from_dt)
        except:
            pass
    if _to:
        try:
            to_dt = datetime.strptime(_to, '%Y-%m-%d')
            q = q.filter(Expense.date <= to_dt)
        except:
            pass
    if user_id:
        try:
            uid = int(user_id)
            q = q.filter_by(user_id=uid)
        except:
            pass

    expenses = q.order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)

    # 🔹 Tính tổng chi / nợ từng thành viên
    member_balances = group.calculate_balances()

    # 🔹 Tính toán gợi ý nợ nần (settlement)
    debt_suggestions = []
    creditors = []  # người được nhận (balance > 0)
    debtors = []    # người nợ (balance < 0)

    for member in group.members:
        bal = member_balances[member.id]["balance"]
        if bal > 0:
            creditors.append({"user": member, "amount": bal})
        elif bal < 0:
            debtors.append({"user": member, "amount": -bal})

    # 🔄 Thuật toán cân bằng nợ
    creditors.sort(key=lambda x: x["amount"], reverse=True)
    debtors.sort(key=lambda x: x["amount"], reverse=True)

    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        amount = min(debtor["amount"], creditor["amount"])
        debt_suggestions.append({
            "from": debtor["user"],
            "to": creditor["user"],
            "amount": amount
        })
        debtor["amount"] -= amount
        creditor["amount"] -= amount
        if debtor["amount"] == 0:
            i += 1
        if creditor["amount"] == 0:
            j += 1

    return render_template(
        'expenses.html',
        group=group,
        expenses=expenses,
        total=total,
        member_balances=member_balances,
        debt_suggestions=debt_suggestions
    )

@bp.route('/<int:group_id>/new', methods=['GET', 'POST'])
@login_required
def expense_new(group_id):
    from app.models import Category
    group = Group.query.get_or_404(group_id)
    members = group.members
    categories = Category.query.all()
    shares = []

    if request.method == 'POST':
        title = request.form.get('title') or 'Không tên'
        amount = float(request.form['amount'])
        payer_id = int(request.form.get('payer_id'))
        split_type = request.form.get('split_type', 'equal')
        notes = request.form.get('note', '')
        currency = request.form['currency']

        rate = get_exchange_rate(currency, "VND")
        base_amount_vnd = round(amount * rate, 2)
        category_id = request.form.get('category_id')

        expense = Expense(
            title=title,
            amount=amount,
            currency=currency,
            base_amount_vnd=amount * rate,
            note=notes,
            user_id=payer_id,
            created_by=current_user.id,
            group_id=group_id,
            category_id=category_id if category_id else None
        )
        db.session.add(expense)
        db.session.flush()  # để có ID

        selected_members = request.form.getlist('member_ids')

        if not selected_members:
            flash('Vui lòng chọn ít nhất một thành viên để chia.', 'danger')
            db.session.rollback()
            return redirect(url_for('expenses.expense_new', group_id=group_id))
        
        shares = []
        if split_type == 'equal':
            per_person_vnd = round(expense.base_amount_vnd / len(selected_members), 2)
            for mid in selected_members:
                shares.append(ExpenseShare(expense_id=expense.id, user_id=int(mid), share_amount=per_person_vnd))
        else:
            total_percent = 0
            for mid in selected_members:
                percent = float(request.form.get(f'percent_{mid}', 0))
                total_percent += percent
                share_amount_vnd = round(expense.base_amount_vnd * percent / 100, 2)
                shares.append(ExpenseShare(
                    expense_id=expense.id,
                    user_id=int(mid),
                    share_amount=share_amount_vnd,
                    share_percent=percent
                ))
            if round(total_percent) != 100:
                flash('Tổng phần trăm chia phải bằng 100%', 'danger')
                db.session.rollback()
                return redirect(url_for('expenses.expense_new', group_id=group_id))
        db.session.add_all(shares)

    # 🟢 GỬI THÔNG BÁO cho các thành viên khác
        for member in group.members:
            if member.id != current_user.id:
                notif = Notification(
                    user_id=member.id,
                    message=f"{current_user.username} đã thêm chi tiêu mới: {title} ({expense.amount_formatted})",
                    link=url_for('expenses.expense_detail', expense_id=expense.id),
                    type="expense"
                )
                db.session.add(notif)

        db.session.commit()
        flash('Thêm chi tiêu thành công và thông báo đã được gửi!', 'success')
        return redirect(url_for('expenses.expense_list', group_id=group_id))
    return render_template('new_expense.html', group=group, members=members, categories=categories)


@bp.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if expense.created_by != current_user.id and expense.user_id != current_user.id:
        flash('Bạn không có quyền xóa chi tiêu này.', 'danger')
        return redirect(url_for('expenses.expense_list', group_id=expense.group_id))

    group_id = expense.group_id
    db.session.delete(expense)
    db.session.commit()
    flash('Xóa chi tiêu thành công!', 'success')
    return redirect(url_for('expenses.expense_list', group_id=group_id))

# export excel
@bp.route('/<int:group_id>/export')
@login_required
def export_expenses(group_id):
    group = Group.query.get_or_404(group_id)
    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.date).all()

    wb = Workbook()
    ws = wb.active
    ws.title = f"Group_{group_id}_expenses"
    ws.append(["Tên chi tiêu", "Số tiền", "Ngày tạo", "Ghi chú", "Người trả"])

    for e in expenses:
        payer = User.query.get(e.user_id)
        payer_name = payer.username if payer else ""
        ws.append([e.title, int(round(e.amount)), e.currency, int(round(e.base_amount_vnd)), e.date.strftime('%Y-%m-%d'), e.note or "", payer_name])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    filename = f"group_{group_id}_expenses.xlsx"
    return send_file(bio, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@bp.route('/detail/<int:expense_id>')
@login_required
def expense_detail(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    shares = ExpenseShare.query.filter_by(expense_id=expense.id).all()

    # Thêm dòng này để lấy group
    group = expense.group  

    return render_template(
        'expense_detail.html',
        expense=expense,
        shares=shares,
        group=group   # truyền thêm group vào template
    )

@bp.route('/remind_payment/<int:to_user_id>', methods=['POST'])
@login_required
def remind_payment(to_user_id):
    # Không cho người nợ gửi nhắc chính họ
    if current_user.id == to_user_id:
        flash('❌ Bạn không thể gửi nhắc thanh toán cho chính mình.', 'danger')
        return redirect(request.referrer or url_for('groups.group_list'))
    
    bank_name = request.form.get('bank_name')
    bank_account = request.form.get('bank_account')
    to_user = User.query.get_or_404(to_user_id)

    message = (
        f"Số tài khoản: {bank_account} - Ngân hàng: {bank_name}. "
        f"{current_user.username} đã nhắc bạn thanh toán khoản nợ 💸."
    )

    notif = Notification(
        user_id=to_user.id,
        message=message,
        type='payment_reminder',
        created_at=datetime.utcnow()
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'✅ Đã gửi nhắc thanh toán cho {to_user.username}', 'success')
    return redirect(request.referrer or url_for('groups.group_list'))


@bp.route('/settle_debt/<int:from_user_id>/<int:to_user_id>/<int:group_id>', methods=['POST'])
@login_required
def settle_debt(from_user_id, to_user_id, group_id):
    group = Group.query.get_or_404(group_id)

    if current_user.id not in [from_user_id, to_user_id]:
        flash("❌ Bạn không có quyền xác nhận thanh toán này.", "danger")
        return redirect(url_for('expenses.expense_list', group_id=group_id))
    # ✅ Tìm các ExpenseShare mà from_user nợ trong group này
    shares = ExpenseShare.query.join(Expense).filter(
        Expense.group_id == group_id,
        ExpenseShare.user_id == from_user_id,
        ExpenseShare.is_settled == False
    ).all()

    if not shares:
        flash("⚠️ Không tìm thấy khoản nợ cần xác nhận.", "warning")
        return redirect(url_for('expenses.expense_list', group_id=group_id))

    # ✅ Đánh dấu là đã thanh toán
    for s in shares:
        s.is_settled = True

    db.session.commit()

    # Gửi thông báo cho người nợ
    notif = Notification(
        user_id=from_user_id,
        message=f"{current_user.username} đã xác nhận bạn đã thanh toán khoản nợ 💰.",
        type="payment_confirmed",
        created_at=datetime.utcnow()
    )
    db.session.add(notif)
    db.session.commit()

    flash(f'✅ Đã xác nhận {User.query.get(from_user_id).username} đã thanh toán!', 'success')
    return redirect(url_for('expenses.expense_list', group_id=group_id))

@bp.route('/get_rate/<string:currency>')
@login_required
def get_rate(currency):
    rate = get_exchange_rate_to_vnd(currency.upper())
    # trả về tỷ giá 1 <currency> = rate VND
    return {"rate": rate}
@bp.route('/update/<int:expense_id>', methods=['POST'])
@login_required
def update_expense(expense_id):
    from app import db
    from app.models import Expense, ExpenseShare

    expense = Expense.query.get_or_404(expense_id)

    # Cập nhật loại tiền tệ
    new_currency = request.form.get('currency')
    if new_currency:
        expense.currency = new_currency

    # Cập nhật danh sách chia tiền
    selected_user_ids = request.form.getlist('selected_users')
    all_shares = ExpenseShare.query.filter_by(expense_id=expense.id).all()
    for share in all_shares:
        share.is_active = str(share.user_id) in selected_user_ids

    db.session.commit()
    flash('Cập nhật chi tiết chi tiêu thành công!', 'success')
    return redirect(url_for('expenses.expense_detail', expense_id=expense.id))

@bp.route('/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).limit(10).all()
    return render_template('notifications_list.html', notifications=notifications)

