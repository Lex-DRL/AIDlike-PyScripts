# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import abc as _abc
from dataclasses import dataclass as _dataclass
from datetime import datetime as _dt
from itertools import chain as _chain
import json as _json
from pathlib import Path as _Path

from pydantic import (
	BaseModel as _BaseModel,
	Field as _Field,
	validator as _v,
	ValidationError as _ValidError,
)
from pydantic.dataclasses import dataclass as _pyd_dataclass

from common import (
	StaticDataClass as _StaticDataClass,
	TrackingABC as _TrackingABC,
	abc_method_assert as _abc_assert,
)
import drl_enum as _enum
from drl_pydantic import ValidatorsIfNot as _vNot


from drl_typing import *


module_dir = _Path(__file__).parent


class ProxyID(_NT):
	"""Essential (identifier) data for proxy. Used as key in `ProxyPool`."""
	domain: str
	port: int


@_enum.map_all_cases(unknown=True)
class Anonymity(_enum.Enum):
	Unknown = None
	Transparent = 0
	Anonymous = 1
	Elite = 2


@_dataclass
class UpTime:
	n_used: int = 0
	n_ok: int = 0

	@property
	def success_rate(self):
		return 1.0 if (self.n_used == 0) else (self.n_ok / self.n_used)

	def update(self, success: bool = True):
		self.n_used += 1
		self.n_used += success


_abc_assert_abstract_data = _abc_assert(lambda: _AbstractProxyData)


class ProxyCompareError(TypeError):
	def __init__(self, a, operation: str, b):
		super(ProxyCompareError, self).__init__(
			f"Wrong comparison: {a!r} {operation}, {b!r}"
		)
		self.a = a
		self.b = b
		self.operation = operation


class _AbstractProxyData(_abc.ABC, _BaseModel):
	"""
	Root base class for all the *ProxyData classes. Basically, should contain
	everything known about a specific proxy except for it's url (acting as id)."""

	@_abc_assert_abstract_data
	@_abc.abstractmethod
	def __eq__(self, other) -> bool:
		"""Whether two proxies are equivalent (and probably need merging)."""
		...

	def __ne__(self, other) -> bool:
		"""Whether one of the proxies is clearly better than the other one."""
		return not self.__eq__(other)

	@_abc_assert_abstract_data
	@_abc.abstractmethod
	def __lt__(self, other) -> bool:
		"""Whether this proxy is worse than some other one."""
		...

	def __le__(self, other):
		raise ProxyCompareError(self, '<=', other)

	@_abc_assert_abstract_data
	@_abc.abstractmethod
	def __gt__(self, other) -> bool:
		"""Whether this proxy is better than some other one."""
		...

	def __ge__(self, other) -> bool:
		raise ProxyCompareError(self, '>=', other)


_abc_assert_specific_data = _abc_assert(lambda: _SpecificPoolProxyData)


class _SpecificPoolProxyData(_AbstractProxyData):
	"""Base class for each concrete pool's underlying data."""

	# noinspection PyUnreachableCode
	@_abc_assert_specific_data
	@_abc.abstractmethod
	def as_standard(self):
		"""Represent specific pool data as standard key-value pair for proxy."""
		raise TypeError(
			f"{self.__class__.__name__}.as_standard() must be overridden for "
			f"and called from concrete child classes."
		)
		# noinspection PyTypeChecker
		k: ProxyID = None
		# noinspection PyTypeChecker
		v: ProxyData = None
		return k, v


class ProxyData(_AbstractProxyData):
	"""
	Proxy data in standard form.

	Additionally, may contain ``_SpecificPoolProxyData`` *(proxy info
	taken from a specific pool)* linked as ``raw_data``.
	"""

	proto: _u[None, _l_str, _tpl_str] = None
	country: str = None
	city: str = None
	last_worked: _o[_dt] = None
	uptime_total: UpTime = UpTime()
	uptime_when_worked: UpTime = UpTime()
	reported_speed: int = 0
	anon: Anonymity = Anonymity.Unknown

	raw_data: _o[_SpecificPoolProxyData] = None

	_v_proto = _vNot('proto', pre=True).none
	_v_country = _vNot('country', pre=True).none
	_v_city = _vNot('city', pre=True).none
	_v_last_worked = _vNot('last_worked', pre=True).none

	_v_uptime_total = _vNot('uptime_total', pre=True).value_factory(UpTime)
	_v_uptime_when_worked = _vNot('uptime_when_worked', pre=True).value_factory(UpTime)
	_v_reported_speed = _vNot('reported_speed', pre=True).int

	@_v('anon', pre=True)
	def _v_anon(cls, v):
		return Anonymity[v]

	_v_raw_data = _vNot('raw_data', pre=True).none


	def __eq__(self, other: _AbstractProxyData) -> bool:
		# TODO
		raise NotImplementedError()

	def __lt__(self, other: _AbstractProxyData) -> bool:
		# TODO
		raise NotImplementedError()

	def __gt__(self, other: _AbstractProxyData) -> bool:
		# TODO
		raise NotImplementedError()


_pp_dict = _d[ProxyID, ProxyData]

_abc_assert_pp = _abc_assert(lambda: ProxyPool, cls=True, work_on_abc=True)


class ProxyPool(_TrackingABC, _StaticDataClass):
	"""The main class containing all the available proxies along with their stats."""
	json_file_init = module_dir / 'all_proxy_pools-init.json'
	json_file_cache = module_dir / 'all_proxy_pools-cache.json'

	__combined_pool: _pp_dict = dict()

	_pool_class_priority: tuple = (0, )  # bigger = more important

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def __contains__(cls, key: ProxyID):
		return key in cls.__combined_pool

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def __getitem__(cls, key: ProxyID):
		return cls.__combined_pool[key]

	@classmethod
	def __all_classes(cls, self=True):
		"""All ``ProxyPool`` classes."""
		classes: _i[_Tp[ProxyPool]] = cls._tracked_children
		if self:
			classes = _chain([cls], classes)
		return tuple(classes)

	@classmethod
	def __all_standard_pools(cls):
		"""
		Tuple with all classes and their standard-pools (including
		the main ``ProxyPool``, too).
		Pools are sorted according to ``_pool_class_priority``.
		"""
		_t_res_item = _tpl[_Tp[ProxyPool], _pp_dict]
		all_pools: _l[_t_res_item] = list(_chain(
			[(cls, cls.__combined_pool)],
			((c, c._as_standard_pool()) for c in cls.__all_classes(False))
		))
		all_pools = sorted(
			all_pools, key=lambda x: x[0]._pool_class_priority
		)
		return tuple(all_pools)

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _raw_pool(cls) -> _d[ProxyID, _tA]:
		"""
		Underlying pool dict for each specific pool (it's items are
		``_SpecificPoolItemData`` subclasses, specific for each pool.)
		"""
		return cls.__combined_pool

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _child_entry_class(cls) -> _Tp[_SpecificPoolProxyData]:
		"""Return the type of underlying item data for each pool."""
		# noinspection PyTypeChecker
		return None

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _pop_item(cls, k: ProxyID):
		"""Remove an item with a given key from the pool."""
		for child in cls.__all_classes(False):
			child._pop_item(k)
		cls.__combined_pool.pop(k)

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _sync_item(cls, k: ProxyID, v: ProxyData):
		"""
		Ensure there's no proxy duplicates between pools by merging their data
		and keeping only one instance in the pool with the most recent proxy-data.
		"""
		# TODO
		...

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _load(cls):
		"""Load data from all the sources a given ``ProxyPool`` supports."""
		# TODO
		...

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _cache(cls):
		"""Save the ``ProxyPool`` contents to a cache file (JSON)."""
		# TODO
		...

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _as_standard_pool(cls) -> _pp_dict:
		"""Convert internal raw pool to the standard format."""
		merged_pool: _d[ProxyID, ProxyData] = dict()
		for pool_cls, std_pool in cls.__all_standard_pools():
			raw_pool = pool_cls._raw_pool()
			for k, v in std_pool.items():
				cls._sync_item(k, v)
				if k in raw_pool:
					merged_pool[k] = v

		cls.__combined_pool.update(merged_pool)
		return cls.__combined_pool
