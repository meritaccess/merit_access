from abc import ABC, abstractmethod


class ServiceControllerABC(ABC):
    """
    Manages the Apache2 service.
    """

    @abstractmethod
    def start(self) -> None:
        """
        Abstract method to start the service.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Abstract method to stop the service.
        """
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """
        Abstract method to check if the service is active.
        """
        pass

    @abstractmethod
    def reload(self) -> None:
        """
        Abstract method to reload the service.
        """
        pass

    @abstractmethod
    def restart(self) -> None:
        """
        Abstract method to restart the service.
        """
        pass

    def __str__(self) -> str:
        return "ServiceControllerABC"

    def __repr__(self) -> str:
        return "ServiceControllerABC"
