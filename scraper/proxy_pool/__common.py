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


@_enum.map_all_cases(unknown=True)
class ProxySource(_enum.Enum):
	Unknown = None
	GeoNode = 0
	FreeProxyList = 1

	Custom = 99


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


_abc_assert_specific_data = _abc_assert(lambda: _SpecificPoolProxyData)


class _SpecificPoolProxyData(_abc.ABC, _BaseModel):

	# noinspection PyUnreachableCode
	@_abc_assert_specific_data
	@_abc.abstractmethod
	def as_standard(self):
		"""Represent specific pool data as standard key-value pair for proxy."""
		raise NotImplementedError()
		# noinspection PyTypeChecker
		k: ProxyID = None
		# noinspection PyTypeChecker
		v: ProxyData = None
		return k, v


@_dataclass
class ProxyData:
	"""
	Optional data (stats) for a given proxy. Basically, everything except for
	proxy-url.
	Additionally, may contain linked `raw_data` with proxy info
	taken from a specific source (for a specific proxy pool).
	"""
	proto: _u[str, _l[str], _tpl_str] = ''
	country: str = ''
	city: str = ''
	last_worked: _o[_dt] = None
	uptime_total: UpTime = UpTime()
	uptime_when_worked: UpTime = UpTime()
	reported_speed: int = 0
	anon: Anonymity = Anonymity.Unknown
	source: ProxySource = ProxySource.Unknown

	raw_data: _o[_SpecificPoolProxyData] = None


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
		return cls.__combined_pool

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _child_entry_class(cls) -> _Tp[_SpecificPoolProxyData]:
		# noinspection PyTypeChecker
		return None

	@classmethod
	@_abc_assert_pp
	@_abc.abstractmethod
	def _pop_item(cls, k: ProxyID):
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
