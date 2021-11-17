# encoding: utf-8
"""Service functions/classes working with built-in Enums."""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

from enum import *
from itertools import chain as _chain


_t_enum = _t.Type[Enum]
_t_enum_meta = _t.Type[EnumMeta]


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


def _enum_base(enum_cls: _t_enum) -> _t_enum:
	"""Extract base class the Enum was created from."""
	base_enums = [
		x for x in enum_cls.__bases__ if issubclass(x, Enum)
	]
	if not base_enums:
		base_enums = [
			x for x in enum_cls.__bases__ if isinstance(x, EnumMeta)
		]
	base_cls = base_enums[-1] if base_enums else Enum
	assert isinstance(base_cls, EnumMeta)
	# noinspection PyTypeChecker
	return base_cls


def _enum_base_meta(enum_cls: _t_enum) -> _t_enum_meta:
	"""Extract base meta-class the Enum was created from."""
	base_meta = None
	# noinspection PyBroadException
	try:
		base_meta = enum_cls.__class__
		ok = True
	except:
		ok = False
	if not base_meta:
		ok = False

	if not ok:
		base_metas = [
			x for x in enum_cls.__bases__ if issubclass(x, EnumMeta)
		]
		base_meta = base_metas[-1] if base_metas else EnumMeta

	assert issubclass(base_meta, EnumMeta)
	# noinspection PyTypeChecker
	return base_meta


def extend(*items, **kw_items):
	"""Decorator which adds extra members to Enum."""

	def decorator(enum_cls: _t_enum):
		base_cls = _enum_base(enum_cls)

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
		# noinspection PyArgumentList
		return base_cls(enum_cls.__name__, joined, **_enum_call_kwargs(enum_cls))

	return decorator


def map_all_cases(
	unknown=False,
	default: _t.Union[None, Enum, _t.Callable[[_t_enum], _t.Any]] = None,
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
	def default_f_for_unknown(cls: _t_enum_meta):
		return cls.Unknown

	def default_f_from_value(cls: _t_enum_meta):
		return default

	def decorator(enum_cls_orig: _t_enum):
		default_f: _t.Callable[[_t_enum_meta], Enum] = (
			default
			if callable(default) and not isinstance(default, EnumMeta)
			else default_f_from_value
		)
		if unknown and default is None:
			default_f = default_f_for_unknown

		class ModifiedMeta(_enum_base_meta(enum_cls_orig)):
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
				cls.__map_all_keys: _t.Dict[_t.Any, Enum] = dict(_chain(*all_mappings))
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

		class ModifiedBaseEnum(_enum_base(enum_cls_orig), metaclass=ModifiedMeta):
			pass

		joined = dict()
		if unknown:
			joined.update(Unknown=-1)
		for item in enum_cls_orig:
			joined[item.name] = item.value
		for k in joined.keys():
			if k.startswith('__'):
				joined.pop(k)

		return ModifiedBaseEnum(
			enum_cls_orig.__name__, joined, **_enum_call_kwargs(enum_cls_orig)
		)

	return decorator
