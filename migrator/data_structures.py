from dataclasses import dataclass
from enum import Enum
from typing import List, Optional



class Person(Enum):
    DIRECTOR = 'director'
    ACTOR = 'actor'


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
class Genre:
    id: str
    name: str

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name
        }


@dataclass
class Movie(ShortMovie):
    id: str
    title: str
    imdb_rating: float
    description: str
    genre: List[str]
    actors: List[Actor]
    writers: List[Writer]
    directors: List[str]

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'imdb_rating': float(self.imdb_rating),
            'description': self.description,
            'genre': self.genre,
            'actors': [actor.to_dict() for actor in self.actors],
            'writers': [writer.to_dict() for writer in self.actors],
            'directors': self.directors,
        }