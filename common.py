# encoding: utf-8
"""
Very generic stuff shared between modules.
"""

__author__ = 'Lex Darlog (DRL)'

import abc as _abc
from dataclasses import dataclass as _dataclass
from pathlib import Path as _Path

from drl_typing import *

root_dir = _Path(__file__).parent


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


@_dataclass(init=False, frozen=True)
class StaticDataClass:
	"""Base for static (non-instantiable) classes."""

	def __init__(self):
		raise TypeError(f"<{self.__class__.__name__}> is non-instantiable data class")


class TrackingMeta(type):
	"""
	Meta-class which keeps track of all the classes inherited from it.

	Use it:

	*
		if the defined class doesn't use any other metaclasses, just do:

		``class MyClass(metaclass=TrackingMeta): pass``
	*
		otherwise (if you use other meta-class, even indirectly),
		you need to create a combined metaclass first (multiple
		inheritance, `TrackingMeta` being the last) and use it instead.
	*
		To use it with ABC, there are pre-defined `TrackingABCMeta` and
		`TrackingABC` classes.
	"""

	def __new__(mcs, *args, **kwargs):
		cls = super().__new__(mcs, *args, **kwargs)
		_t_track_set = _set[TrackingMeta]
		_t_track_hierarchy = _d[TrackingMeta, _t_track_set]

		try:
			children_dict: _t_track_hierarchy = mcs.__children_by_class
		except AttributeError:
			children_dict: _t_track_hierarchy = dict()
			mcs.__children_by_class = children_dict
		if cls not in children_dict:
			children_dict[cls]: _t_track_set = set()

		for predefined_class, c_set in children_dict.items():
			if issubclass(cls, predefined_class) and cls is not predefined_class:
				c_set.add(cls)

		return cls

	@property
	def _tracked_children(cls):
		return tuple(cls.__children_by_class[cls])

	@property
	def _whole_tracking(cls):
		_t_track_set = _tpl[TrackingMeta, ...]
		_t_track_hierarchy = _d[TrackingMeta, _t_track_set]
		res: _t_track_hierarchy = {
			k: tuple(v) for k, v in cls.__children_by_class.items()
		}
		return res


class TrackingABCMeta(_abc.ABCMeta, TrackingMeta):
	"""Abstract meta-class which keeps track of all the classes inherited from it."""
	pass


class TrackingABC(_abc.ABC, metaclass=TrackingABCMeta):
	"""Abstract base class which keeps track of all the classes inherited from it."""
	pass


_byte_kilo_sizes = ('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi')
_byte_yobi = 'Yi'
_byte_kilo_step = 1024.0


def human_bytes(
	size: _if, size_in_bits=False, space=' ', suffix='B'
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


def format_thousands(number: _u[_if, str], spacer="'"):
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


def decorators_combine(*decs, reverse=False):
	"""
	Combine multiple decorators to one::

		@outer
		@inner
		def my_func():
			pass

		# is the same as:
		@decorators_combine(inner, outer)
		def my_func():
			pass

		# or:
		def my_func():
			pass
		new_dec = decorators_combine(outer, inner, reverse=True)
		my_func = new_dec(my_func)

	:param reverse:
		if ``True``, reverses the order decorators are applied. I.e., you list them
		left-to-right as if you were typing them top-to-bottom.
		Normally, it's the other way around: decorators wrap each other as you put
		them on top of one another.
	"""
	def decorator(f):
		decs_seq = reversed(decs) if reverse else decs
		for dec in decs_seq:
			f = dec(f)
		return f
	return decorator
