from app import create_app, db
from app.models import Role, User, Genre

app = create_app()

with app.app_context():
    db.create_all()
    
    # Создание ролей
    roles = [
        {'name': 'Администратор', 'description': 'Суперпользователь, имеет полный доступ к системе, в том числе к созданию и удалению книг'},
        {'name': 'Модератор', 'description': 'Может редактировать данные книг и производить модерацию рецензий'},
        {'name': 'Пользователь', 'description': 'Может оставлять рецензии'}
    ]

    for role_data in roles:
        if not Role.query.filter_by(name=role_data['name']).first():
            role = Role(name=role_data['name'], description=role_data['description'])
            db.session.add(role)

    # Создание админа
    admin_role = Role.query.filter_by(name='Администратор').first()
    if admin_role and not User.query.filter_by(login='admin').first():
        admin = User(
            login='admin',
            last_name='Админов',
            first_name='Админ',
            role_id=admin_role.id
        )
        admin.set_password('admin')
        db.session.add(admin)

    # Создание жанров (опционально, для удобства тестирования)
    genres = ['Фантастика', 'Роман', 'Детектив', 'Учебная литература', 'Сказка']
    for g_name in genres:
        if not Genre.query.filter_by(name=g_name).first():
            genre = Genre(name=g_name)
            db.session.add(genre)

    db.session.commit()
    print("Данные успешно добавлены!")
