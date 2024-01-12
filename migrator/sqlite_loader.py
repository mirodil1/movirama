import json
import sqlite3
import typing
import uuid


class SQLiteLoader:
    SQLite_SQL = """
    WITH x as(
    SELECT m.id, group_concat(a.id) as actors_ids, group_concat(a.name) as
    actors_names
    FROM movies m
        LEFT JOIN movie_actors ma ON m.id = ma.movie_id
        LEFT JOIN actors a ON ma.actor_id = a.id
    GROUP BY m.id
    )
    SELECT m.id, genre, director, title, plot, imdb_rating, x.actors_ids, x.actors_names, 
        CASE
            WHEN m.writers = '' THEN '[{"id":"'||m.writer||'"}]'
            ELSE m.writers
        END AS writers
    FROM movies m
    LEFT JOIN x ON m.id = x.id
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
    
    def load_movies(self):
        for row in self.conn.execute(self.SQL):
            print(row)
