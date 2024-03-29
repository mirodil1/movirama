from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from typing import List, Optional
from urllib.parse import urljoin

import requests
from flask import Flask, abort, jsonify, request
from flask_cors import CORS
from wtforms import Form, IntegerField, SelectField, StringField, validators

app = Flask(__name__)
CORS(app)

BASE_URL = 'http://elasticsearch:9200'


@dataclass
class Actor:
    id: int
    name: str

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name
        }


@dataclass
class Writer:
    id: int
    name: str

    def to_dict(self) -> dict:
        return {
            'id': int(self.id),
            'name': self.name
        }


@dataclass
class ShortMovie:
    id: str
    title: str
    imdb_rating: float

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'imdb_rating': float(self.imdb_rating)
        }


@dataclass
class Movie(ShortMovie):
    description: str
    genre: List[str]
    actors: List[Actor]
    writers: List[Writer]
    directors: List[str]

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            'description': self.description,
            'genre': self.genre,
            'actors': [actor.to_dict() for actor in self.actors],
            'writers': [writer.to_dict() for writer in self.actors],
            'directors': self.directors
        }


class SortOrder(Enum):
    ASC = 'asc'
    DESC = 'desc'


class SortField(Enum):
    ID = 'id'
    TITLE = 'title'
    IMDB_RATING = 'imdb_rating'


def get_movie_by_id(movie_id: str) -> Optional[Movie]:
    response = requests.get(
        url = urljoin(BASE_URL, f'movies/_doc/{movie_id}'),
        headers={'Content-Type': 'application/json'},
    )

    if not response.ok:
        response.raise_for_status()

    data = response.json()
    movie_raw = data['_source']
    movie = Movie(
        id=movie_raw['id'],
        title=movie_raw['title'],
        imdb_rating=movie_raw['imdb_rating'],
        genre=movie_raw['genre'],
        description=movie_raw['description'],
        actors=[Actor(*actors) for actors in movie_raw['actors']],
        writers=[Writer(*writers) for writers in movie_raw['writers']],
        directors=movie_raw['director']
    )
    return movie


def search_movies(
    *,
    search_query: Optional[str] = None,
    sort_order: SortOrder = SortOrder.ASC,
    sort: SortField = SortField.TITLE,
    page: int = 1,
    limit: int = 50
) -> List[ShortMovie]:
    sort_value = sort.value
    if sort_value == SortField.TITLE.value:
        sort_value = f'{SortField.TITLE.value}.raw'
    request_data = {
        'size': limit,
        'from': (page-1) * limit,
        # 'sort': [
        #     {
        #         sort_value: {
        #             'order': sort_order.value
        #         }
        #     }
        # ],
        '_source': ['id', 'title', 'imdb_rating'],
    }

    if search_query:
        request_data['query'] = {
            'multi_match': {
                'query': search_query,
                'fuzziness': 'auto',
                'fields': [
                    'title^5',
                    'descriptor^4',
                    'genre^3',
                    'actors_names^2',
                    'writers_names^2',
                    'director'
                ]
            }
        }
    
    response = requests.get(
        url=urljoin(BASE_URL, 'movies/_search'),
        json=request_data,
        headers={'Content-Type': 'application/json'}
    )
    if not response.ok:
        response.raise_for_status()

    data = response.json()
    result = data['hits']['hits']
    movies = []

    if result:
        for record in result:
            movie_raw = record['_source']
            movies.append(ShortMovie(
                id=movie_raw['id'],
                title=movie_raw['title'],
                imdb_rating=movie_raw['imdb_rating']
            ))
    return movies


@app.route('/api/movies/<movie_id>', methods=['GET'])
def movie_details(movie_id: str):
    movie = get_movie_by_id(movie_id)
    if movie is None:
        abort(HTTPStatus.NOT_FOUND)
    return jsonify(movie.to_dict())


class SearchMoviesValidator(Form):
    limit = IntegerField('Limit', [validators.NumberRange(min=0)], default=50)
    page = IntegerField('Page', [validators.NumberRange(min=1)], default=1)
    search = StringField('Search', default="")
    sort = SelectField(
        'Sort',
        choices=[
            (SortField.ID.value, SortField.ID.value),
            (SortField.TITLE.value, SortField.TITLE.value),
            (SortField.IMDB_RATING.value, SortField.IMDB_RATING.value)
        ],
        default=SortField.ID.value
    )
    sort_order = SelectField(
        choices=[
            (SortOrder.ASC.value, SortOrder.ASC.value),
            (SortOrder.DESC.value, SortOrder.DESC.value)
        ],
        default=SortOrder.ASC.value
    )


def validation_error_to_dict(errors: dict) -> List[dict]:
    validation_errors = []
    for field_name, field_errors in errors.items():
        for err in field_errors:
            validation_errors.append(
                {
                    'loc': [
                        'query',
                        field_name
                    ],
                    'msg': err
                }
            )
    return validation_errors


@app.route('/api/movies', methods=['GET'], strict_slashes=False)
def movies_list():
    form = SearchMoviesValidator(request.args)
    validation_errors = []
    if not form.validate():
        validation_errors = validation_error_to_dict(form.errors)
    if validation_errors:
        return jsonify(detail=validation_errors), HTTPStatus.UNPROCESSABLE_ENTITY

    movies = search_movies(
        search_query=form.search.data,
        sort_order=SortOrder(form.sort_order.data),
        sort=SortField(form.sort.data),
        page=form.page.data,
        limit=form.limit.data
    )

    return jsonify([movie.to_dict() for movie in movies])


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
