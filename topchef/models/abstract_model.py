import abc
from uuid import UUID
from typing import TypeVar
from sqlalchemy.orm import Session
from topchef.storage import DocumentStorage


class AbstractModel(object, metaclass=abc.ABCMeta):
    """
    Base class for a model class that can be written to multiple storage
    media. This class is capable of checking its own consistency
    """
    T = TypeVar('T')

    @abc.abstractmethod
    def write(self, session: Session, storage: DocumentStorage) -> None:
        """

        Write this object to persistent storage, taking ALL storage media
        from one consistent state to another
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, session: Session, storage: DocumentStorage) -> None:
        """
        Clear the instance from all resources
        """

    @classmethod
    @abc.abstractmethod
    def from_storage(
            cls,
            model_id: UUID,
            db_session: Session,
            storage: DocumentStorage
    ) -> T:
        """

        :return: The class, built from the required storage media
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def __eq__(self, other: T) -> bool:
        """
        Check that the id of both models is correct

        :param other: The other model to compare
        :return:
        """