# encoding: utf-8
"""Service functions/classes working with built-in Enums."""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

import abc as _abc
import enum as _enum
from itertools import chain as _chain


class _EnumMappedMeta(_abc.ABCMeta, _enum.EnumMeta):
	@_abc.abstractmethod
	def _unknown_member(cls) -> _t.Optional[_enum.Enum]:
		...

	def __members_map_various_cases(cls):
		try:
			return cls.__map_various_cases
		except AttributeError:
			pass

		all_mappings = (
			(
				(k, v), (k.lower(), v), (k.upper(), v),
			) for k, v in cls._member_map_.items()
			if not k.startswith('__')
		)
		cls.__map_various_cases = dict(_chain(*all_mappings))
		return cls.__map_various_cases

	def __getitem__(cls, name):
		# noinspection PyBroadException
		try:
			name = str(name)
		except:
			return cls._unknown_member()
		name = name.lower()
		mapping = cls.__members_map_various_cases()
		if name not in mapping:
			return cls._unknown_member()
		return mapping[name]


class EnumMapped(_enum.Enum, metaclass=_EnumMappedMeta):
	"""
	An Enum base class which also provides mapping from CamelCase, lowercase
	and UPPERCASE member names (assuming there's no cross-case clashes).
	"""
	pass


def enum_extend(*items, **kw_items):
	def wrapper(added_enum):
		joined = {}
		# for item in inherited_enum:
		# 	joined[item.name] = item.value
		for item in added_enum:
			joined[item.name] = item.value
		return _enum.Enum(added_enum.__name__, joined)
	return wrapper
