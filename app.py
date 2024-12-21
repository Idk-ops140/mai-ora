from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///maiora.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    blocked_until = db.Column(db.DateTime, nullable=True)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    article_code = db.Column(db.String(10), unique=True, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user is None:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('User already exists')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            if user.blocked_until and user.blocked_until > datetime.utcnow():
                flash(f'You are blocked until {user.blocked_until}')
            else:
                login_user(user)
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    articles = Article.query.filter_by(author_id=current_user.id).all()
    return render_template('dashboard.html', articles=articles)

@app.route('/article/new', methods=['GET', 'POST'])
@login_required
def new_article():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if contains_forbidden_keywords(content):
            block_user()
            flash('You used forbidden keywords. You are blocked for 5 days.')
            return redirect(url_for('dashboard'))
        article_code = generate_article_code()
        article = Article(title=title, content=content, author_id=current_user.id, article_code=article_code)
        db.session.add(article)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('new_article.html')

@app.route('/article/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_article(id):
    article = Article.query.get_or_404(id)
    if request.method == 'POST':
        if article.author_id != current_user.id:
            flash('You are not authorized to edit this article')
            return redirect(url_for('dashboard'))
        article.title = request.form['title']
        article.content = request.form['content']
        if contains_forbidden_keywords(article.content):
            block_user()
            flash('You used forbidden keywords. You are blocked for 5 days.')
            return redirect(url_for('dashboard'))
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', article=article)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    articles = Article.query.filter(Article.content.contains(query) | Article.title.contains(query)).all()
    return render_template('search_results.html', articles=articles)

def contains_forbidden_keywords(content):
    forbidden_keywords = ['badword1', 'badword2']  # Add more forbidden keywords
    return any(keyword in content for keyword in forbidden_keywords)

def block_user():
    current_user.blocked_until = datetime.utcnow() + timedelta(days=5)
    db.session.commit()

def generate_article_code():
    import random, string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
