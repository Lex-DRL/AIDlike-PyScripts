# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
from typing import (
	Optional as _o,
	Union as _u,
	Callable as _c,
	List as _l,
	Tuple as _tpl,
	Set as _s,
	Dict as _d,
)

import abc as _abc
from dataclasses import dataclass as _dataclass
from datetime import datetime as _dt
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

from common import StaticDataClass as _StaticDataClass
import enum_utils as _enum
from pyd_utils import (
	ValidatorsIfNot as _vNot,
	v_func as _v_func,
)

_o_str = _o[str]
_o_dig = _u[None, int, float]
_tpl_str = _tpl[str, ...]

module_dir = _Path(__file__).parent


class ProxyID(_t.NamedTuple):
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


@_dataclass
class ProxyData:
	proto: _u[str, _l[str], _tpl_str] = ''
	country: str = ''
	city: str = ''
	last_worked: _t.Optional[_dt] = None
	uptime_total: UpTime = UpTime()
	uptime_when_worked: UpTime = UpTime()
	reported_speed: int = 0
	anon: Anonymity = Anonymity.Unknown
	source: ProxySource = ProxySource.Unknown

	orig_data: _o[_BaseModel] = None


class UserAgentPool(_abc.ABC, _StaticDataClass):
	pass


class _UserAgentPoolGeoNode(UserAgentPool):
	json_file_init = module_dir / 'proxy_pool-geonode-init.json'

	class DataJSON(_BaseModel):
		class DataItem(_BaseModel):
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

			uptime: _o_dig = _Field(None, alias='upTime')
			uptime_success: _o[int] = _Field(None, alias='upTimeSuccessCount')
			uptime_tries: _o[int] = _Field(None, alias='upTimeTryCount')
			working: _o_dig = _Field(None, alias='workingPercent')

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

		total: int
		page: int
		limit: int
		data: _tpl[DataItem, ...] = _Field(default_factory=tuple)

	pass  # _UserAgentPoolGeoNode


# https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https

