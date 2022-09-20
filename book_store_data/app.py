import os
import pickle

from flask import Flask, render_template, abort, url_for, request, flash, make_response
from werkzeug.utils import secure_filename, redirect
from flask_bootstrap import Bootstrap

from book import Book
from config import Config
from forms import BookForm

from flask import session
from forms import LoginForm


from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)

bootstrap = Bootstrap(app)

with open('all_books.bin', 'rb') as file:
    all_books = pickle.load(file)
    Book.max_id = len(all_books)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
@app.route('/about/')
def about():
    return render_template('about.html', title='О сайте')


@app.route('/books')
@app.route('/books/')
@app.route('/catalog')
@app.route('/catalog/')
@app.route('/books/index')
@app.route('/books/index/')
def books():
    # last_viewing_book_id = request.cookies.get('book_id')
    # last_viewing_book = all_books.get(int(last_viewing_book_id)))
    last_viewing_books_id = request.cookies.get('books_id')
    last_viewing_books = []
    if last_viewing_books_id:
        books_id = last_viewing_books_id[:-1].split(',')
        for book_id in books_id:
            last_viewing_books.append(all_books.get(int(book_id)))

    return render_template('books/index.html', books=all_books, title='Книги', last_viewing_books=last_viewing_books,
                           #last_viewing_book=last_viewing_book
                           )

def ensure_logged_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        username = session.get('username')
        if not (username and username in app.config['SUPER_USERS']):
            flash('Please, login to continue', 'warning')
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


@app.route('/login', methods=['GET', 'POST'])
@app.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data.lower() in app.config['SUPER_USERS']:
            if app.config['SUPER_USERS'][form.username.data.lower()] == form.password.data:
                print('bye')
                session['username'] = form.username.data.lower()
                flash('Login successful', 'success')
                return redirect(url_for('index'))
        flash('Login failed. Try again', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    session.pop('username', None)
    flash('You successfully logged out', 'success')
    return redirect(url_for('login'))

@app.route('/books/<int:id>')
@app.route('/books/<int:id>/')
def book(id):
    b = all_books.get(id)
    if not b:
        return abort(404)
    res = make_response(render_template(f'books/book.html', book=b, title=f'{b.name} - {b.author}'))
    last_viewing_books_id = request.cookies.get('books_id')
    if not last_viewing_books_id:
        last_viewing_books_id = ''
    else:
        books_id = last_viewing_books_id[:-1].split(',')
        if len(books_id) > 2:
            last_viewing_books_id = ','.join(books_id[1:]) + ','
        if str(id) in books_id:
            print(id, books_id, last_viewing_books_id)
            books_id.remove(str(id))
            last_viewing_books_id = ','.join(books_id) + ','

    last_viewing_books_id += str(id) + ','
    res.set_cookie('books_id', last_viewing_books_id)
    # res.set_cookie('book_id', str(id))
    return res


@app.route('/books/create', methods=['GET', 'POST'])
@app.route('/books/create/', methods=['GET', 'POST'])
@ensure_logged_in
def create_book():
    form = BookForm()
    if form.validate_on_submit():
        img_dir = os.path.join(os.path.dirname(app.instance_path), 'static', 'img')
        f = form.image.data
        filename = ''
        if f:
            filename = secure_filename(f.filename)
            f.save(os.path.join(img_dir, 'cover_' + filename))

        new_book = Book(name=form.name.data, author=form.author.data, price=float(round(form.price.data, 2)),
                        genre=form.genre.data, amount=form.amount.data, description=form.description.data,
                        filename=filename)
        all_books[new_book.id] = new_book
        with open('all_books.bin', 'wb') as file:
            pickle.dump(all_books, file)
        flash('Книга успешно добавлена.', 'success')
        return redirect(url_for('create_book'))
    return render_template('books/book_form.html', form=form, action_name='Создание')


@app.route('/books/<int:id>/edit', methods=['GET', 'POST'])
@app.route('/books/<int:id>/edit/', methods=['GET', 'POST'])
@ensure_logged_in
def edit_book(id):
    form = BookForm()

    editable_book = all_books.get(id)
    if not editable_book:
        return abort(404)

    if form.validate_on_submit():
        img_dir = os.path.join(os.path.dirname(app.instance_path), 'static', 'img')
        f = form.image.data
        filename = secure_filename(f.filename)
        if filename and filename != editable_book.filename:
            f.save(os.path.join(img_dir, 'cover_' + filename))

            old_file = os.path.join(img_dir, 'cover_' + editable_book.filename)
            editable_book.filename = filename
            if os.path.exists(old_file):
                os.remove(old_file)

        editable_book.name = form.name.data
        editable_book.author = form.author.data
        editable_book.genre = form.genre.data
        editable_book.price = float(round(form.price.data, 2))
        editable_book.description = form.description.data
        with open('all_books.bin', 'wb') as file:
            pickle.dump(all_books, file)
        flash('Книга успешно отредактирована.', 'success')
        return redirect(url_for('book', id=editable_book.id))

    form.name.data = editable_book.name
    form.genre.data = editable_book.genre
    form.image = editable_book.filename
    form.description.data = editable_book.description
    form.price.data = editable_book.price
    form.author.data = editable_book.author

    return render_template('books/book_form.html', form=form, file=editable_book.cover,
                           action_name='Редактирование', book_id=id)


@app.route('/books/<int:id>/remove', methods=['GET', 'POST'])
@app.route('/books/<int:id>/remove/', methods=['GET', 'POST'])
@ensure_logged_in
def remove_book(id):
    removable_book = all_books.get(id)
    if not removable_book:
        return abort(404)

    if request.method == 'POST':
        img_dir = os.path.join(os.path.dirname(app.instance_path), 'static', 'img')
        old_file = os.path.join(img_dir, 'cover_' + removable_book.filename)
        if os.path.exists(old_file):
            os.remove(old_file)
        del all_books[id]
        with open('all_books.bin', 'wb') as file:
            pickle.dump(all_books, file)
        flash('Книга успешно удалена.', 'success')
        return redirect(url_for('books'))

    return render_template('books/remove_book.html', book=removable_book)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug = True)
