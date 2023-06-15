from abc import ABCMeta, abstractmethod
import interactions as ipy


class BaseExtension(ipy.Extension, metaclass=ABCMeta):
    ...
