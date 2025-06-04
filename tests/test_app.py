import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app import Movie, RecommendationEngine, MovieRepository

# Fake CSV data for testing
class FakeDataSource:
    def load_movies(self):
        return [
            Movie("Movie A", "Action, Drama", 2010, 8.1, "Director A"),
            Movie("Movie B", "Action, Comedy", 2015, 7.8, "Director B"),
            Movie("Movie C", "Drama", 2020, 9.0, "Director C"),
            Movie("Movie D", "Action", 2005, 6.5, "Director D"),
            Movie("Movie E", "Comedy", 2012, 7.2, "Director E"),
        ]

def test_movie_object():
    movie = Movie("Test Movie", "Thriller, Mystery", 2023, 8.5, "Test Director")
    assert movie.title == "Test Movie"
    assert "Thriller" in movie.genre
    assert movie.year == 2023
    assert movie.rating == 8.5
    assert str(movie) == "Test Movie (2023) - 8.5"

def test_movie_repository_filter():
    repo = MovieRepository(FakeDataSource())
    filtered = repo.filter_by_genre_and_year("Action", 2000, 2020)
    assert len(filtered) == 3
    assert all("Action" in m.genre for m in filtered)
    assert all(2000 <= m.year <= 2020 for m in filtered)

def test_recommendation_engine_top_rated():
    repo = MovieRepository(FakeDataSource())
    movies = repo.filter_by_genre_and_year("Drama", 2000, 2030)
    engine = RecommendationEngine()
    top = engine.get_top_rated(movies, top_n=2)
    assert len(top) == 2
    assert top[0].rating >= top[1].rating
