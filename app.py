from flask import redirect, url_for, Flask, render_template, flash, jsonify, json

from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm

from wtforms import StringField, EmailField, SubmitField, PasswordField, BooleanField, ValidationError, IntegerField
from wtforms.validators import DataRequired, EqualTo, Length
from wtforms.widgets import TextArea

from flask_migrate import Migrate

from flask_caching import Cache
import redis

from config import *

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DB_URI
app.config['CACHE_TYPE'] = CACHE_BACKEND
app.config['CACHE_DEFAULT_TIMEOUT'] = TIMEOUT
app.config['CACHE_REDIS_URL'] = REDIS_URL
app.json.sort_keys = SORT

cache = Cache(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Anime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    anidb_id = db.Column(db.Integer)
    myanimelist_id = db.Column(db.Integer)

class AnimeForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired()], widget=TextArea())
    anidb_id = IntegerField("AniDB ID", validators=[DataRequired()])
    myanimelist_id = IntegerField("MyAnimeList ID", validators=[DataRequired()])
    submit = SubmitField("Submit")

class SearchForm(FlaskForm):
    searched = StringField("Search", validators=[DataRequired()])
    submit = SubmitField("Submit")

@app.route("/")
def index():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found():
    return render_template('404.html'), 404

@app.route("/add-anime", methods=["GET", "POST"])
def anime():
    form = AnimeForm()

    if form.validate_on_submit():
        animu = Anime(
            title = form.title.data,
            description = form.description.data,
            anidb_id = form.anidb_id.data,
            myanimelist_id = form.myanimelist_id.data
        )

        db.session.add(animu)
        db.session.commit()

        cache.clear()

        flash("Anime adăugat cu succes!")

    print(f"Form validation failed: {form.errors}")
    flash("A avut loc o eroare. Reîncercați.", "error")

    return render_template("add_animu2.html", form=form)

@app.context_processor
def base():
    form = SearchForm()
    return dict(form=form)

@app.route("/search", methods=["POST"])
def search():
    form = SearchForm()

    if form.validate_on_submit():
        search_query = form.searched.data.strip().lower()
        cached_results = cache.get(search_query)

        if cached_results:
            return render_template("search.html", form = form, results = cached_results, search_query = search_query)

        if search_query.startswith("anidb="):
            anidb_id = search_query.replace("anidb=", "").strip()
            results = Anime.query.filter_by(anidb_id=anidb_id).all()

        elif search_query.startswith("mal="):
            mal_id = search_query.replace("mal=", "").strip()
            results = Anime.query.filter_by(myanimelist_id=mal_id).all()

        else:
            results = Anime.query.filter(Anime.title.ilike(f"%{search_query}")).all()

        cache.set(search_query, results)

        return render_template("search.html", form = form, results = results, search_query = search_query)

    return render_template("search.html", form = form, results = None)


@app.route('/anime/<int:id>/')
def post(id):
    anime = Anime.query.get_or_404(id)
    return render_template('anime.html', anime = anime)

@app.route("/anime/<int:id>/json", methods = ['GET'])
def json_anime(id):
    anime = Anime.query.get_or_404(id)
    return jsonify({'id': id, 'name': anime.title, 'description': anime.description})

@app.route('/anime/<int:id>/edit', methods=['GET', 'POST'])
def edit_anime(id):
    anime = Anime.query.get_or_404(id)
    form = AnimeForm()

    if form.validate_on_submit():

        anime.title = form.title.data
        anime.content = form.description.data
        anime.anidb_id = form.anidb_id.data
        anime.myanimelist_id = form.myanimelist_id.data

        db.session.add(anime)
        db.session.commit()

        flash(f'Anime-ul {anime.title} a fost actualizat')

        return redirect(url_for('post', id=anime.id))

    form.title.data = anime.title
    form.description.data = anime.description
    form.anidb_id.data = anime.anidb_id
    form.myanimelist_id.data = anime.myanimelist_id

    return render_template('edit.html', form=form)

if __name__ == "__main__":
    app.run(debug = True, port = 5000, threaded = True)