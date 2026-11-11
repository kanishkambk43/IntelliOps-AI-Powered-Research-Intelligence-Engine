#Any Python class that inherits from Base will automatically be turned into a real PostgreSQL table by SQLAlchemy.
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass