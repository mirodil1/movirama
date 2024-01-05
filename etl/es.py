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
    custom context manager for closing connection
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
                json.dumps({'index': index_name, '_id': row['id']}),
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
    SELECT m.id, group_concat(a.id) as actors_ids, group_concat(a.name) as
    actors_names
    FROM movies m
        LEFT JOIN movie_actors ma ON m.id = ma.movie_id
        LEFT JOIN actors a ON ma.actor_id = a.id
    GROUP_BY m.id
    SELECT m.id, genre, director, title, plot, imdb_rating, x.actors, x.actor_names, 
        CASE
        WHEN m.writers = "THEN '[{"id":"'||m.writer||'"]'
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
        pass