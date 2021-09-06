# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

import abc as _abc
from pathlib import Path
from dataclasses import dataclass as _dataclass


@_dataclass(init=False, frozen=True)
class StaticDataClass:
	"""Base for static (non-instantiable) classes."""

	def __init__(self):
		raise TypeError(f"<{self.__class__.__name__}> is non-instantiable data class")


class CustomHash(_abc.ABC):
	"""
	An ABC overriding what a concrete class is represented with
	when hashed / checked for equality.

	If used with dataclass, make sure it has `(eq=False, unsafe_hash=False)`.
	"""

	@property
	@_abc.abstractmethod
	def hash_id(self) -> tuple:
		"""
		The actual value the class instance is represented with
		when hashed / checked for equality.
		"""
		...

	def __eq__(self, other):
		return self.hash_id == (
			other.hash_id if isinstance(other, CustomHash) else other
		)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return hash(self.hash_id)


root_dir = Path(__file__).parent
