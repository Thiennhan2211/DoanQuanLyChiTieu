from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from datetime import datetime


# ---------------- USER ----------------
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    avatar = db.Column(db.String(255), nullable=True)

    created_groups = db.relationship('Group', backref='creator', lazy=True)
    expenses = db.relationship('Expense', foreign_keys='Expense.user_id', backref='payer', lazy=True)
    created_expenses = db.relationship('Expense', foreign_keys='Expense.created_by', backref='creator_user', lazy=True)
    notifications = db.relationship('Notification', backref='recipient', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# ---------------- GROUP ----------------
GroupMember = db.Table(
    'group_member',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    limit_amount = db.Column(db.Float, default=0.0)

    members = db.relationship('User', secondary=GroupMember, backref=db.backref('groups', lazy='dynamic'))
    expenses = db.relationship('Expense', backref='group', lazy=True, cascade="all, delete-orphan")

    def total_amount(self):
        return sum(e.amount for e in self.expenses)

    def __repr__(self):
        return f'<Group {self.name}>'
    def calculate_balances(self):
        balances = {}
        for member in self.members:
            paid = sum(e.base_amount_vnd for e in self.expenses if e.user_id == member.id)
            owed = 0
            for e in self.expenses:
                for s in e.shares:
                    if s.user_id == member.id and not getattr(s, 'is_settled', False):
                        owed += s.share_amount
            balance = paid - owed
            balances[member.id] = {
                "user": member,
                "paid": paid,
                "owed": owed,
                "balance": balance
            }
        return balances


# ---------------- MEMBERSHIP ----------------
class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    role = db.Column(db.String(20), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- EXPENSE ----------------
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='VND')  
    base_amount_vnd = db.Column(db.Float, nullable=False, default=0.0)
    note = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shares = db.relationship('ExpenseShare', backref='expense', cascade="all, delete-orphan")
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    @property
    def amount_formatted(self):
        # Hiển thị số tiền theo đơn vị gốc
        amt = int(round(self.amount))
        return f"{amt:,}".replace(",", ".") + f" {self.currency}"
    
    @property
    def base_amount_vnd_formatted(self):
        return f"{int(round(self.base_amount_vnd)):,}".replace(",", ".") + " VNĐ"

    def __repr__(self):
        return f'<Expense {self.title}>'


# ---------------- FRIENDSHIP ----------------
class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- NOTIFICATION ----------------
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(50), default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(255))

    def __repr__(self):
        return f'<Notification {self.message}>'


# ---------------- MESSAGE ----------------
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.receiver_id}>'


#---------------- ExpenseShare ----------------
class ExpenseShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_settled = db.Column(db.Boolean, default=False)
    share_amount = db.Column(db.Float, nullable=False, default=0.0)
    share_percent = db.Column(db.Float, nullable=True)
    user = db.relationship('User')
# ---------------- CATEGORY ----------------
class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), nullable=True)  # Emoji hoặc FontAwesome

    # Một category có nhiều expense
    expenses = db.relationship('Expense', backref='category', lazy=True)