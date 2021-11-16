# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

from dataclasses import dataclass as _dataclass
from datetime import datetime as _dt
import json as _json
from pathlib import Path as _Path
import requests as _requests

from common import StaticDataClass as _StaticDataClass
import enum_utils as _enum


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
	last_worked: _t.Optional[_dt] = None
	uptime_total: UpTime = UpTime()
	uptime_when_worked: UpTime = UpTime()
	reported_speed: int = 0
	anonymity: Anonymity = Anonymity.Unknown
	source: ProxySource = ProxySource.Unknown


class UserAgentPool(_StaticDataClass):
	pass


# https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https

