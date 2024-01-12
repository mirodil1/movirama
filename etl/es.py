import json
import logging
import sqlite3
from contextlib import contextmanager
from typing import List
from urllib.parse import urljoin

import requests

logger = logging.getLogger()


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """
    convert sqlite list to dict format
    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@contextmanager
def conn_context(db_path: str):
    """
    custom context manager for closing connection properly
    :param db_path: path to database
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    yield conn
    conn.close()


class ESLoader:
    """
    Load to Elasticsearch
    """
    def __init__(self, url: str) -> None:
        self.url = url

    def _get_es_bulk_query(self, rows: List[dict], index_name: str) -> List[str]:
        """
        Preparing bulk query to Elasticsearch
        """
        prepared_query = []
        for row in rows:
            prepared_query.extend([
                json.dumps({'index': {'_index': index_name, '_id': row['id']}}),
                json.dumps(row)
            ])
        return prepared_query
    
    def load_to_es(self, records: List[dict], index_name: str):
        """
        Sending a request to ES and analyzing data saving errors
        """
        prepared_query = self._get_es_bulk_query(records, index_name)
        str_query = '\n'.join(prepared_query) + '\n'
        response = requests.post(
            urljoin(self.url, '_bulk'),
            data=str_query,
            headers={'Content-Type': 'application/x-ndjson'},
            timeout=10
        )
        json_response = json.loads(response.content.decode())
        for item in json_response['items']:
            error_message = item['index'].get('error')
            if error_message:
                logger.error(error_message)


class ETL:
    SQL = """
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

    def __init__(self, conn: sqlite3.Connection, es_loader: ESLoader) -> None:
        self.es_loader = es_loader
        self.conn = conn
    
    def load_writers_names(self) -> dict:
        """
        Getting all writers
        """
        writers = {}
        for writer in self.conn.execute("""SELECT DISTINCT id, name FROM writers"""):
            writers[writer['id']] = writer
        return writers
    
    def _transform_row(self, row: dict, writers: dict) -> dict:
        """
        """
        movie_writers = []
        writers_set = set()
        for writer in json.loads(row['writers']):
            writer_id = writer['id']
            if writers[writer_id]['name'] != 'N/A' and writer_id not in writers_set:
                movie_writers.append(writers[writer_id])
                writers_set.add(writer_id)

        actors = []
        actors_names = []
        if row['actors_ids'] is not None and row['actors_names'] is not None:
            actors = [
                {'id': _id, 'name': name}
                for _id, name in zip(row['actors_ids'].split(','), row['actors_names'].split(','))
                if name != 'N/A'
            ]
            actors_names = [x for x in row['actors_names'].split(',') if x != 'N/A']

        return {
            'id': row['id'],
            'genre': row['genre'].replace(' ', '').split(','),
            'writers': movie_writers,
            'actors': actors,
            'actors_name': actors_names,
            'writers_names': [x['name'] for x in movie_writers],
            'imdb_rating': float(row['imdb_rating']) if row['imdb_rating'] != 'N/A' else None,
            'title': row['title'],
            'director': [x.strip() for x in row['director'].split(',')] if row['director'] != 'N/A' else None,
            'description': row['plot'] if row['plot'] != 'N/A' else None
        }

    def load(self, index_name: str):
        """
        Main ETL method
        """
        records = []
        writers = self.load_writers_names()

        for row in self.conn.execute(self.SQL):
            print(row)
            transformed_row = self._transform_row(row, writers)
            records.append(transformed_row)

        self.es_loader.load_to_es(records, index_name)

if __name__ == "__main__":
    # Database connection context manager
    with conn_context('db.sqlite') as conn:
        # Elasticsearch loader
        es_loader = ESLoader(url='http://localhost:9200')

        # ETL process
        etl = ETL(conn=conn, es_loader=es_loader)

        # Load data into Elasticsearch index
        etl.load(index_name='movies')
