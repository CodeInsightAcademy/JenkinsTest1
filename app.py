# imdb_recommendation_flask_app.py

import csv
from flask import Flask, render_template_string, request
from typing import List

# ---- Movie Class ----
class Movie:
    def __init__(self, title, genre, year, rating, director):
        self.title = title
        self.genre = genre.split(', ') if isinstance(genre, str) else genre
        self.year = int(year)
        self.rating = float(rating) if rating else 0.0
        self.director = director

    def __str__(self):
        return f"{self.title} ({self.year}) - {self.rating}"

# ---- Data Source ----
class CSVDataSource:
    def __init__(self, filepath):
        self.filepath = filepath

    def load_movies(self) -> List[Movie]:
        movies = []
        with open(self.filepath, encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['IMDB_Rating']:
                    movie = Movie(
                        title=row['Series_Title'],
                        genre=row['Genre'],
                        year=row['Released_Year'],
                        rating=row['IMDB_Rating'],
                        director=row['Director']
                    )
                    movies.append(movie)
        return movies

# ---- Repository ----
class MovieRepository:
    def __init__(self, data_source: CSVDataSource):
        self.movies = data_source.load_movies()

    def filter_by_genre_and_year(self, genre: str, start_year: int, end_year: int) -> List[Movie]:
        return [m for m in self.movies if genre in m.genre and start_year <= m.year <= end_year]

# ---- Recommendation Engine ----
class RecommendationEngine:
    def get_top_rated(self, movies: List[Movie], top_n: int = 5) -> List[Movie]:
        return sorted(movies, key=lambda m: m.rating, reverse=True)[:top_n]

# ---- Flask App ----
app = Flask(__name__)

csv_path = "imdb_top_1000.csv"  # Replace with your actual CSV path
data_source = CSVDataSource(csv_path)
repo = MovieRepository(data_source)
engine = RecommendationEngine()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>IMDb Movie Recommender</title>
</head>
<body>
    <h2>IMDb Movie Recommendation System</h2>
    <form method="POST">
        Genre: <input type="text" name="genre" required><br><br>
        Start Year: <input type="number" name="start_year" required><br><br>
        End Year: <input type="number" name="end_year" required><br><br>
        <input type="submit" value="Recommend">
    </form>

    {% if recommendations %}
        <h3>Top Movies:</h3>
        <ul>
        {% for movie in recommendations %}
            <li>{{ movie }}</li>
        {% endfor %}
        </ul>
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    recommendations = []
    if request.method == 'POST':
        genre = request.form['genre']
        start_year = int(request.form['start_year'])
        end_year = int(request.form['end_year'])

        filtered = repo.filter_by_genre_and_year(genre, start_year, end_year)
        recommendations = engine.get_top_rated(filtered)

    return render_template_string(HTML_TEMPLATE, recommendations=recommendations)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    # app.run(debug=True)
