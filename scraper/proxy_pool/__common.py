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
import requests as _requests

from common import (
	StaticDataClass as _StaticDataClass,
	TrackingABC as _TrackingABC,
)
import enum_utils as _enum
from drl_pydantic import (
	ValidatorsIfNot as _vNot,
	v_func as _v_func,
)

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


class _SpecificPoolItemData(_abc.ABC, _BaseModel):

	# noinspection PyUnreachableCode
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

	raw_data: _o[_SpecificPoolItemData] = None


_pp_dict = _d[ProxyID, ProxyData]


class ProxyPool(_TrackingABC, _StaticDataClass):
	"""The main class containing all the available proxies along with their stats."""
	json_file_init = module_dir / 'proxy_pool-init.json'
	json_file_cache = module_dir / 'proxy_pool-cache.json'

	__combined_pool: _pp_dict = dict()

	_pool_class_priority: tuple = (0, )  # bigger = more important

	@classmethod
	@_abc.abstractmethod
	def __contains__(cls, key):
		return key in cls.__combined_pool

	@classmethod
	@_abc.abstractmethod
	def __getitem__(cls, key):
		return cls.__combined_pool[key]

	@classmethod
	def __abc_error(cls):
		if cls is not ProxyPool:
			raise NotImplementedError()

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
	@_abc.abstractmethod
	def _raw_pool(cls) -> _d[ProxyID, _tA]:
		cls.__abc_error()
		return cls.__combined_pool

	@classmethod
	@_abc.abstractmethod
	def _child_entry_class(cls) -> _Tp[_SpecificPoolItemData]:
		# noinspection PyTypeChecker
		return None

	@classmethod
	@_abc.abstractmethod
	def _pop_item(cls, k: ProxyID):
		cls.__abc_error()
		for child in cls.__all_classes(False):
			child._pop_item(k)
		cls.__combined_pool.pop(k)

	@classmethod
	@_abc.abstractmethod
	def _sync_item(cls, k: ProxyID, v: ProxyData):
		"""
		Ensure there's no proxy duplicates between pools by merging their data
		and keeping only one instance in the pool with the most recent proxy-data.
		"""
		cls.__abc_error()
		# TODO

	@classmethod
	@_abc.abstractmethod
	def _load(cls):
		"""Load data from all the sources a given ``ProxyPool`` supports."""
		cls.__abc_error()
		# TODO

	@classmethod
	@_abc.abstractmethod
	def _cache(cls):
		cls.__abc_error()
		# TODO

	@classmethod
	@_abc.abstractmethod
	def _as_standard_pool(cls) -> _pp_dict:
		"""Convert internal raw pool to the standard format."""
		cls.__abc_error()

		merged_pool: _d[ProxyID, ProxyData] = dict()
		for pool_cls, std_pool in cls.__all_standard_pools():
			raw_pool = pool_cls._raw_pool()
			for k, v in std_pool.items():
				cls._sync_item(k, v)
				if k in raw_pool:
					merged_pool[k] = v

		cls.__combined_pool.update(merged_pool)
		return cls.__combined_pool


class _GeoNodeItem(_SpecificPoolItemData):
	"""Single proxy data scrubbed from geonode.com"""
	ip: str = ''
	port: int = 0
	host: str = _Field('', alias='hostName')
	id: str = _Field('', alias='_id')

	protocols: _tpl_str = _Field(default_factory=tuple)

	anon: Anonymity = _Field(Anonymity.Unknown, alias='anonymityLevel')
	country: str = ''
	city: str = ''
	region: str = ''
	isp: str = ''
	org: str = ''
	asn: str = ''

	created: _o[_dt] = _Field(None, alias='created_at')
	updated: _o[_dt] = _Field(None, alias='updated_at')
	checked: _o[_dt] = _Field(None, alias='lastChecked')

	google: bool = False
	speed: _o[int] = None
	latency: _o[int] = None
	response: _o[int] = None

	uptime: _o_if = _Field(None, alias='upTime')
	uptime_success: _o[int] = _Field(None, alias='upTimeSuccessCount')
	uptime_tries: _o[int] = _Field(None, alias='upTimeTryCount')
	working: _o_if = _Field(None, alias='workingPercent')

	_v_port = _vNot('port', pre=True).int

	_v_ip = _vNot('ip', pre=True).str
	_v_host = _vNot('host', pre=True).str
	_v_id = _vNot('id', pre=True).str

	@_v('anon', pre=True)
	def _v_anon(cls, v):
		return Anonymity[v]

	_v_country = _vNot('country', pre=True).str
	_v_city = _vNot('city', pre=True).str
	_v_region = _vNot('region', pre=True).str
	_v_isp = _vNot('isp', pre=True).str
	_v_org = _vNot('org', pre=True).str
	_v_asn = _vNot('asn', pre=True).str

	_v_created = _vNot('created', pre=True).none
	_v_updated = _vNot('updated', pre=True).none
	_v_checked = _vNot('checked', pre=True).none

	_v_google = _vNot('google', pre=True).bool
	_v_speed = _vNot('speed', pre=True).none
	_v_latency = _vNot('latency', pre=True).none
	_v_response = _vNot('response', pre=True).none

	_v_uptime = _vNot('uptime', pre=True).none
	_v_uptime_success = _vNot('uptime_success', pre=True).none
	_v_uptime_tries = _vNot('uptime_tries', pre=True).none
	_v_working = _vNot('working', pre=True).none


class _GeoNodeProxyPool(ProxyPool):
	"""Pool of proxies taken from geonode.com"""
	json_file_init = module_dir / 'proxy_pool-geonode-init.json'
	json_file_cache = module_dir / 'proxy_pool-geonode-cache.json'
	url = 'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https'

	__raw_pool: _d[ProxyID, _GeoNodeItem] = dict()

	_pool_class_priority: tuple = (10,)  # bigger = more important

	@classmethod
	def __contains__(cls, key):
		return key in cls.__raw_pool

	@classmethod
	def __getitem__(cls, key):
		return cls.__raw_pool[key]

	@classmethod
	def _raw_pool(cls):
		return cls.__raw_pool

	@classmethod
	def _child_entry_class(cls):
		return _GeoNodeItem

	@classmethod
	def __load_items_to_pool(cls, *items: _GeoNodeItem):
		raise NotImplementedError()

	@classmethod
	def __load_json_files(cls):
		raise NotImplementedError()

	@classmethod
	def __load_from_web(cls):
		raise NotImplementedError()

	@classmethod
	def _load(cls):
		cls.__load_json_files()
		cls.__load_from_web()

	@classmethod
	def _cache(cls):
		raise NotImplementedError()

	@classmethod
	def _as_standard_pool(cls) -> _pp_dict:
		def process_single_item(key: ProxyID, raw_item: _GeoNodeItem):
			new_key, std_item = raw_item.as_standard()
			if new_key != key:
				raise RuntimeError(f'Proxy discrepancy in {cls}: {key} -> {new_key}')
			return key, std_item

		return {
			k: v for k, v in
			(process_single_item(r_k, r_v) for r_k, r_v in cls.__raw_pool.items())
		}



# https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https

