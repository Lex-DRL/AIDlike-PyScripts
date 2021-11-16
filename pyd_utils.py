# encoding: utf-8
"""Service functions/classes working with `pydantic` package."""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

from dataclasses import dataclass as _dataclass

from pydantic import (
	validator as _validator,
)

T = _t.TypeVar('T')


def v_func(
	*fields: str,
	pre: bool = False,
	each_item: bool = False,
	always: bool = False,
	check_fields: bool = True,
	whole: bool = None,
	**kwargs
):
	"""Wrapper for default validator that pre-defines `allow_reuse=True`."""
	kwargs_out = dict(allow_reuse=True)
	kwargs_out.update(
		pre=pre, each_item=each_item, always=always,
		check_fields=check_fields, whole=whole,
	)
	kwargs_out.update(kwargs)
	return _validator(*fields, **kwargs_out)


@_dataclass(init=False)
class _ValidatorBaseFuncClass:
	"""
	A base validator-funcs-containing class. It's attributes:

	*
		are defined in class (not in init) and define functions to be wrapped by
		the actual validator (they're expected to be later decorated with it).
		I.e. used as: `pydantic.validator('field_name', allow_reuse=True)(Class.validator_func)`
	*
		when called from class **instance**, the class constructor itself takes
		validator args and replaces all the instance attribs with the fully build
		validator factories.
		I.e. used as: `Class('field_name').validator_func`
	"""
	def __init__(
		self, *fields: str,
		pre: bool = False,
		each_item: bool = False,
		always: bool = False,
		check_fields: bool = True,
		whole: bool = None,
		**kwargs
	):
		super(_ValidatorBaseFuncClass, self).__init__()
		kwargs_out = dict()
		kwargs_out.update(
			pre=pre, each_item=each_item, always=always,
			check_fields=check_fields, whole=whole,
		)
		kwargs_out.update(kwargs)
		self._validator_fields = fields
		self._validator_kwargs = kwargs_out

		# wrap all the class attributes with the actual validator:
		self.__dict__.update({
			k: v_func(*fields, **kwargs_out)(cls_v)
			for k, cls_v in self.__class__.__dict__.items()
			if not k.startswith('_')
		})


# for some reason, python complains if the next few functions are defined as methods.
# Therefore, define them here as regular functions
# and re-assign them to class later:

def _if_not_value(default_val: T) -> _t.Callable[[_t.Any], T]:
	"""
	General `IfNot` validator. Uses a specified `default_val`
	if given value equals to `False`.
	"""
	def wrapper(v):
		return v or default_val
	return wrapper


def _if_not_value_factory(default_f: _t.Callable[[], T]) -> _t.Callable[[_t.Any], T]:
	"""
	General `IfNot` validator for any complex types. Calls a specified `default_f`
	factory to create a value if given value equals to `False`.
	"""
	def wrapper(v):
		return v or default_f()
	return wrapper


class ValidatorsIfNot(_ValidatorBaseFuncClass):
	"""
	Validators which don't throw an error on type mismatch if the
	given value equals to `False`, and output some default value instead.

	When called from instance (not class itself), all the methods are
	ready-to-use validators and validator args are passed to the class init.
	"""

	value = _if_not_value
	value_factory = _if_not_value_factory

	none = value(None)
	bool = value(False)
	bool_1 = value(True)
	str = value('')
	int = value(0)

	list = value_factory(list)
	tuple = value_factory(tuple)
	dict = value_factory(dict)
	set = value_factory(set)
