from abc import ABC, abstractmethod


class Commitable(ABC):
    """Abstract base class for services that need to commit database sessions."""

    @abstractmethod
    async def commit_all(self) -> None:
        """Commit all active sessions in the service's repositories."""
        pass
