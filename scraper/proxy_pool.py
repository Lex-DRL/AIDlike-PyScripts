# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
from typing import (
	Optional as _o,
	Union as _u,
	List as _l,
	Tuple as _tpl,
)

from dataclasses import dataclass as _dataclass
from datetime import datetime as _dt
import json as _json
from pathlib import Path as _Path

from pydantic import (
	BaseModel as _BaseModel,
	Field as _Field,
	validator as _validator,
	ValidationError as _ValidError,
)
from pydantic.dataclasses import dataclass as _pyd_dataclass
import requests as _requests

from common import StaticDataClass as _StaticDataClass
import enum_utils as _enum

_o_str = _o[str]
_o_dig = _u[None, int, float]
_tpl_str = _tpl[str, ...]

module_dir = _Path(__file__).parent


class ProxyID(_t.NamedTuple):
	proto: str
	domain: str
	port: int


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


@_enum.map_all_cases(unknown=True)
class Anonymity(_enum.Enum):
	Unknown = -1  # for ide hints
	Transparent = 0
	Anonymous = 1
	Elite = 2


@_enum.map_all_cases(unknown=True)
class ProxySource(_enum.Enum):
	Unknown = -1  # for ide hints
	GeoNode = 0
	FreeProxyList = 1

	Custom = 99


@_dataclass
class ProxyStats:
	country: str = ''
	city: str = ''
	last_worked: _t.Optional[_dt] = None
	uptime_total: UpTime = UpTime()
	uptime_when_worked: UpTime = UpTime()
	reported_speed: int = 0
	anon: Anonymity = Anonymity.Unknown
	source: ProxySource = ProxySource.Unknown


class UserAgentPool(_StaticDataClass):
	pass


class _UserAgentPoolGeoNode(UserAgentPool):
	json_file_init = module_dir / 'proxy_pool-geonode-init.json'

	class DataJSON(_BaseModel):
		class DataItem(_BaseModel):
			id: str = _Field('', alias='_id')
			ip: str = ''
			port: int = 0
			host: str = _Field('', alias='hostName')
			protocols: _tpl_str = _Field(default_factory=tuple)

			asn: str = ''
			city: str = ''
			country: str = ''
			region: str = ''
			isp: str = ''
			org: str = ''
			anon: Anonymity = _Field(Anonymity.Unknown, alias='anonymityLevel')

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

			@_validator('anon', pre=True)
			def anon_map(cls, v):
				return Anonymity[v]

			def false_to_zero(cls, v):
				return v or 0

			val_port = _validator('port', pre=True, allow_reuse=True)(false_to_zero)

			def false_to_empty_str(cls, v):
				return v or ''

			_v_ip = _validator('ip', pre=True, allow_reuse=True)(false_to_empty_str)
			_v_host = _validator('host', pre=True, allow_reuse=True)(false_to_empty_str)

			_v_asn = _validator('asn', pre=True, allow_reuse=True)(false_to_empty_str)
			_v_city = _validator('city', pre=True, allow_reuse=True)(false_to_empty_str)
			_v_country = _validator('country', pre=True, allow_reuse=True)(false_to_empty_str)
			_v_region = _validator('region', pre=True, allow_reuse=True)(false_to_empty_str)
			_v_isp = _validator('isp', pre=True, allow_reuse=True)(false_to_empty_str)
			_v_org = _validator('org', pre=True, allow_reuse=True)(false_to_empty_str)

		total: int
		page: int
		limit: int
		data: _tpl[DataItem, ...] = _Field(default_factory=tuple)

	pass


# https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https

