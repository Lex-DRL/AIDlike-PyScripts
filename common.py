# encoding: utf-8
"""
Very generic stuff shared between modules.
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

import abc as _abc
from pathlib import Path
from dataclasses import dataclass as _dataclass


root_dir = Path(__file__).parent


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


_byte_kilo_sizes = ('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi')
_byte_yobi = 'Yi'
_byte_kilo_step = 1024.0


def human_bytes(
	size: _t.Union[int, float], size_in_bits=False, space=' ', suffix='B'
):
	"""Format bytes/bits size in a human-readable form."""

	def format_decimal(size_):
		return f'{size_:.3f}'.rstrip('0').rstrip('.')

	sign = -1 if size < 0 else 1
	size *= sign  # make absolute
	if size_in_bits:
		size = size / 8

	for unit in _byte_kilo_sizes:
		if size < _byte_kilo_step:
			return f'{format_decimal(size * sign)}{space}{unit}{suffix}'
		size /= _byte_kilo_step

	# We're in yobibytes.
	if size < _byte_kilo_step:
		return f'{format_decimal(size * sign)}{space}{_byte_yobi}{suffix}'

	# OK, it's ridiculous now, but we're _AT_LEAST_ in thousands of yobibytes.
	# Let's output in scientific notation.

	# The function can still crash if a user provided number so big that it utilizes
	# long math and can't be casted to a float. But if they deal with THAT order
	# of sizes, it would be the least of their problems.
	order = 0
	while size >= _byte_kilo_step:
		size /= _byte_kilo_step
		order += 3
	return f'{format_decimal(size * sign)}*10^{order}{space}{_byte_yobi}{suffix}'


def format_thousands(number: _t.Union[int, float, str], spacer="'"):
	"""Format a number, splitting thousands with spacer."""

	number_str = str(number).replace(',', '.').strip()
	sign = ''
	if number_str.startswith('-'):
		sign = '-'
		number_str = number_str.lstrip('-')

	if '.' in number_str:
		number_str = number_str.rstrip('0').rstrip('.')
	number_str = number_str.lstrip('0')

	if not number_str:
		return '0'

	reversed_pieces = list()
	while number_str:
		number_str, piece = number_str[:-3], number_str[-3:]
		reversed_pieces.append(piece)
	return sign + spacer.join(reversed(reversed_pieces))
