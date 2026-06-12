import os

app_routes_content = """

@bp.route('/book/add', methods=['GET', 'POST'])
@check_roles('Администратор')
def add_book():
    genres = Genre.query.all()
    if request.method == 'POST':
        title = request.form.get('title')
        short_desc = request.form.get('short_desc')
        year = request.form.get('year')
        publisher = request.form.get('publisher')
        author = request.form.get('author')
        pages = request.form.get('pages')
        genre_ids = request.form.getlist('genres')
        cover_file = request.files.get('cover')

        if not all([title, short_desc, year, publisher, author, pages, genre_ids, cover_file]):
            flash('Все поля обязательны для заполнения', 'danger')
            return render_template('book/form.html', genres=genres, is_edit=False)
            
        short_desc_sanitized = sanitize_html(short_desc)

        try:
            new_book = Book(
                title=title,
                short_desc=short_desc_sanitized,
                year=year,
                publisher=publisher,
                author=author,
                pages=pages
            )
            
            for g_id in genre_ids:
                genre = Genre.query.get(g_id)
                if genre:
                    new_book.genres.append(genre)

            db.session.add(new_book)
            db.session.flush() # Получаем ID новой книги для обложки

            if cover_file:
                cover_content = cover_file.read()
                md5_hash = hashlib.md5(cover_content).hexdigest()
                
                # Проверка на существование такого же файла
                existing_cover = Cover.query.filter_by(md5_hash=md5_hash).first()
                if existing_cover:
                    filename = existing_cover.filename
                else:
                    ext = cover_file.filename.rsplit('.', 1)[1].lower() if '.' in cover_file.filename else 'jpg'
                    filename = f"{new_book.id}_{md5_hash}.{ext}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    with open(filepath, 'wb') as f:
                        f.write(cover_content)

                cover = Cover(
                    filename=filename,
                    mime_type=cover_file.mimetype,
                    md5_hash=md5_hash,
                    book_id=new_book.id
                )
                db.session.add(cover)

            db.session.commit()
            flash('Книга успешно добавлена!', 'success')
            return redirect(url_for('main.view_book', book_id=new_book.id))
        except Exception as e:
            db.session.rollback()
            flash(f'При сохранении данных возникла ошибка: {str(e)}', 'danger')
            return render_template('book/form.html', genres=genres, is_edit=False, form_data=request.form)

    return render_template('book/form.html', genres=genres, is_edit=False)


@bp.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@check_roles('Администратор', 'Модератор')
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    genres = Genre.query.all()
    
    if request.method == 'POST':
        book.title = request.form.get('title')
        book.short_desc = sanitize_html(request.form.get('short_desc'))
        book.year = request.form.get('year')
        book.publisher = request.form.get('publisher')
        book.author = request.form.get('author')
        book.pages = request.form.get('pages')
        genre_ids = request.form.getlist('genres')

        try:
            book.genres = []
            for g_id in genre_ids:
                genre = Genre.query.get(g_id)
                if genre:
                    book.genres.append(genre)

            db.session.commit()
            flash('Данные книги успешно обновлены!', 'success')
            return redirect(url_for('main.view_book', book_id=book.id))
        except Exception as e:
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')

    return render_template('book/form.html', book=book, genres=genres, is_edit=True)

@bp.route('/book/<int:book_id>/delete', methods=['POST'])
@check_roles('Администратор')
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    try:
        if book.cover:
            # Удаление файла обложки, если он больше никем не используется
            cover_md5 = book.cover.md5_hash
            same_covers_count = Cover.query.filter_by(md5_hash=cover_md5).count()
            if same_covers_count == 1:
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover.filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
        db.session.delete(book)
        db.session.commit()
        flash('Книга успешно удалена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
        
    return redirect(url_for('main.index'))

@bp.route('/book/<int:book_id>/review', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Пользователь уже оставлял рецензию?
    existing_review = Review.query.filter_by(book_id=book.id, user_id=current_user.id).first()
    if existing_review:
        flash('Вы уже оставляли рецензию на эту книгу', 'warning')
        return redirect(url_for('main.view_book', book_id=book.id))
        
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        text = request.form.get('text')
        
        if rating is None or not text:
            flash('Все поля обязательны для заполнения', 'danger')
        else:
            sanitized_text = sanitize_html(text)
            try:
                review = Review(book_id=book.id, user_id=current_user.id, rating=rating, text=sanitized_text)
                db.session.add(review)
                db.session.commit()
                flash('Рецензия успешно добавлена', 'success')
                return redirect(url_for('main.view_book', book_id=book.id))
            except Exception as e:
                db.session.rollback()
                flash('Ошибка при сохранении рецензии', 'danger')
                
    return render_template('book/review.html', book=book)

# Статистика (Вариант 4)
import csv
from io import StringIO
from flask import make_response

@bp.route('/statistics')
@check_roles('Администратор')
def statistics():
    # Журнал действий
    journal_page = request.args.get('journal_page', 1, type=int)
    journal_query = VisitLog.query.order_by(VisitLog.created_at.desc())
    journal_pagination = journal_query.paginate(page=journal_page, per_page=10, error_out=False)
    
    # Статистика просмотров
    stats_page = request.args.get('stats_page', 1, type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    stats_query = db.session.query(Book, func.count(VisitLog.id).label('views')).\
        join(VisitLog, VisitLog.book_id == Book.id).\
        filter(VisitLog.user_id.isnot(None))
        
    if date_from:
        stats_query = stats_query.filter(VisitLog.created_at >= date_from + ' 00:00:00')
    if date_to:
        stats_query = stats_query.filter(VisitLog.created_at <= date_to + ' 23:59:59')
        
    stats_query = stats_query.group_by(Book.id).order_by(func.count(VisitLog.id).desc())
    stats_pagination = stats_query.paginate(page=stats_page, per_page=10, error_out=False)
    
    return render_template('statistics/index.html', 
                           journal_pagination=journal_pagination,
                           stats_pagination=stats_pagination)

@bp.route('/statistics/export/journal')
@check_roles('Администратор')
def export_journal():
    logs = VisitLog.query.order_by(VisitLog.created_at.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['№', 'ФИО пользователя', 'Название книги', 'Дата и время просмотра'])
    
    for idx, log in enumerate(logs, 1):
        user_name = log.user.full_name if log.user else 'Неаутентифицированный пользователь'
        book_title = log.book.title
        dt = log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        cw.writerow([idx, user_name, book_title, dt])
        
    output = make_response(si.getvalue().encode('utf-8-sig'))
    output.headers["Content-Disposition"] = f"attachment; filename=journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@bp.route('/statistics/export/stats')
@check_roles('Администратор')
def export_stats():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    stats_query = db.session.query(Book, func.count(VisitLog.id).label('views')).\
        join(VisitLog, VisitLog.book_id == Book.id).\
        filter(VisitLog.user_id.isnot(None))
        
    if date_from:
        stats_query = stats_query.filter(VisitLog.created_at >= date_from + ' 00:00:00')
    if date_to:
        stats_query = stats_query.filter(VisitLog.created_at <= date_to + ' 23:59:59')
        
    stats = stats_query.group_by(Book.id).order_by(func.count(VisitLog.id).desc()).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['№', 'Название книги', 'Количество просмотров'])
    
    for idx, stat in enumerate(stats, 1):
        cw.writerow([idx, stat[0].title, stat.views])
        
    output = make_response(si.getvalue().encode('utf-8-sig'))
    output.headers["Content-Disposition"] = f"attachment; filename=stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
"""

with open(r"c:\Users\hasgh\Desktop\Разработка веб\Экзамен\app\routes.py", "a", encoding="utf-8") as f:
    f.write(app_routes_content)
