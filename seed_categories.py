from app import create_app, db
from app.models import Category

app = create_app()

with app.app_context():
    categories = [
        {"name": "Ăn uống", "icon": "🍔"},
        {"name": "Đi lại", "icon": "🚗"},
        {"name": "Mua sắm", "icon": "🛍️"},
        {"name": "Giải trí", "icon": "🎮"},
        {"name": "Hóa đơn", "icon": "💡"},
        {"name": "Khác", "icon": "📌"},
    ]

    for c in categories:
        exists = Category.query.filter_by(name=c["name"]).first()
        if not exists:
            new_cate = Category(name=c["name"], icon=c["icon"])
            db.session.add(new_cate)

    db.session.commit()
    print("✅ Đã thêm dữ liệu Category vào database!")
