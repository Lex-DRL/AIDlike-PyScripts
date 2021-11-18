# encoding: utf-8
"""Service functions/classes working with built-in Enums."""

__author__ = 'Lex Darlog (DRL)'

from enum import *
from itertools import chain as _chain

from common import (
	remove_duplicates as _remove_duplicates,
)

from drl_typing import *


def _enum_call_kwargs(enum_cls: _t_enum):
	"""Extract optional arguments (for __call__) from an existing Enum class."""
	enum_kwargs = dict()
	try:
		enum_kwargs['module'] = enum_cls.__module__
	except:
		pass
	try:
		enum_kwargs['qualname'] = enum_cls.__qualname__
	except:
		pass
	return enum_kwargs


_t_enum_base = _u[_t_enum, type]
_t_enum_bases = _tpl[_t_enum_base, ...]


def _enum_bases(enum_cls: _t_enum) -> _t_enum_bases:
	"""
	Base classes for a given ``Enum``. If it doesn't inherit enything explicitly
	(uses only meta-class), the default ``Enum`` is used.
	"""
	default = (Enum, )
	try:
		res = enum_cls.__bases__
	except:
		res = default
	# keep only actual types:
	res = tuple(x for x in res if isinstance(x, type))

	if not any(issubclass(x, Enum) for x in res):
		# it doesn't inherit the built-in Enum, force it to be the first base class:
		res = tuple(*_chain(default, res))
	# remove duplicates:
	return tuple(_remove_duplicates(res))


def _enum_constructing_base_class(
	*out_enum_bases: _t_enum_base,
	out_meta: _t_enum_meta,
) -> _t_enum:
	"""
	Extract (or generate an intermediate) base ``Enum`` class used to create
	a decorated ``Enum``.
	"""
	base_first = out_enum_bases[0]

	if len(out_enum_bases) == 1:
		assert issubclass(base_first, Enum), (
			f"{base_first} is a single Enum base class "
			f"but doesn't inherit from Enum itself"
		)
		# The given enum_cls has only one base and it's an Enum.
		# Therefore (by definition) it's also an instance of EnumMeta.
		# However, enum_cls itself might use a different meta from it's base.
		# So we need to check for it:
		if out_meta == _enum_base_meta(base_first):
			# no need to define any intermediate classes:
			return base_first

	# unfortunately, we do need to define a constructing class...
	class ModifiedBaseEnum(*out_enum_bases, metaclass=out_meta):
		pass
	return ModifiedBaseEnum


def _enum_base_meta(enum_cls: _t_enum) -> _t_enum_meta:
	"""Extract base meta-class the Enum was created from."""
	# noinspection PyBroadException
	try:
		res = enum_cls.__class__
	except:
		res = None
	if not isinstance(res, type):
		res = EnumMeta

	if issubclass(res, EnumMeta):
		return res

	# Bad luck. We do have subclass, but it's not a child of EnumMeta.
	# we need to create a multi-inherited meta-class:
	bases = (EnumMeta, res)

	class MergedEnumMeta(*_remove_duplicates(bases)):
		pass
	MergedEnumMeta.__name__ = res.__name__
	return MergedEnumMeta


def extend(*items, **kw_items):
	"""Decorator which adds extra members to Enum."""

	def decorator(enum_cls: _t_enum) -> _t_enum:
		joined = dict(items)
		joined.update(kw_items)
		for k, v in items:
			if k not in kw_items:
				joined[k] = v
		for item in enum_cls:
			joined[item.name] = item.value
		for k in joined.keys():
			if k.startswith('__'):
				joined.pop(k)

		base_cls = _enum_constructing_base_class(
			*_enum_bases(enum_cls), out_meta=_enum_base_meta(enum_cls)
		)
		return base_cls(enum_cls.__name__, joined, **_enum_call_kwargs(enum_cls))

	return decorator


def map_all_cases(
	unknown=False,
	default: _u[None, Enum, _c[[_t_enum], _tA]] = None,
):
	"""
	Enum decorator which lets querying Enum members with `Enum['member_name']`
	using either ProperCase or also lowercase/UPPERCASE names
	(assuming there's no cross-case clashes between members).

	:param unknown:
		If `True`, the <Unknown> member added.
	:param default:
		The value to return when no such member is found.
	"""
	def default_f_for_unknown(cls: _t_enum):
		return cls.Unknown

	def default_f_from_value(cls: _t_enum):
		return default

	def decorator(enum_cls: _t_enum) -> _t_enum:
		default_f: _c[[_t_enum], Enum] = (
			default
			if callable(default) and not isinstance(default, EnumMeta)
			else default_f_from_value
		)
		if unknown and default is None:
			default_f = default_f_for_unknown

		base_meta = _enum_base_meta(enum_cls)

		class ModifiedMeta(base_meta):
			def __members_map_all_keys(cls):
				try:
					return cls.__map_all_keys
				except AttributeError:
					pass

				all_mappings = (
					(
						(k, v), (k.lower(), v), (k.upper(), v), (v.value, v), (v, v),
					) for k, v in cls._member_map_.items()
					if not k.startswith('__')
				)
				cls.__map_all_keys: _d[_tA, Enum] = dict(_chain(*all_mappings))
				return cls.__map_all_keys

			def __getitem__(cls, key):
				is_str = isinstance(key, str)
				if is_str:
					key = key.strip()

				mapping = cls.__members_map_all_keys()
				if key in mapping:
					return mapping[key]

				# noinspection PyBroadException
				if is_str:
					# string given, but it might actually be a JSON representing int:
					try:
						key = int(key)
					except:
						return default_f(cls)
				else:
					# ... or the opposite, some fancy type representing str:
					try:
						key = str(key)
					except:
						return default_f(cls)
					key = key.strip()

				if key in mapping:
					return mapping[key]
				return default_f(cls)
		ModifiedMeta.__name__ = base_meta.__name__

		joined = dict()
		if unknown:
			joined.update(Unknown=-1)
		for item in enum_cls:
			joined[item.name] = item.value
		for k in joined.keys():
			if k.startswith('__'):
				joined.pop(k)

		base_cls = _enum_constructing_base_class(
			*_enum_bases(enum_cls), out_meta=ModifiedMeta
		)
		return base_cls(
			enum_cls.__name__, joined, **_enum_call_kwargs(enum_cls)
		)

	return decorator
