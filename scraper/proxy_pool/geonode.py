# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

from datetime import datetime as _dt

from pydantic import (
	BaseModel as _BaseModel,
	Field as _Field,
	validator as _v,
)

from drl_pydantic import (
	ValidatorsIfNot as _vNot,
	v_func as _v_func,
)

from .__common import *
# and protected members - manually:
from .__common import (
	_SpecificPoolProxyData,
	_pp_dict,
)

from drl_typing import *


class GeoNodeProxyData(_SpecificPoolProxyData):
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

	def as_standard(self) -> _tpl[ProxyID, ProxyData]:
		# TODO
		raise NotImplementedError()


class GeoNodeProxyPool(ProxyPool):
	"""Pool of proxies taken from geonode.com"""

	json_file_init = module_dir / 'geonode-init.json'
	json_file_cache = module_dir / 'geonode-cache.json'
	url = 'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https'

	__raw_pool: _d[ProxyID, GeoNodeProxyData] = dict()

	_pool_class_priority: tuple = (10,)  # bigger = more important

	@classmethod
	def __contains__(cls, key: ProxyID):
		return key in cls.__raw_pool

	@classmethod
	def __getitem__(cls, key):
		return cls.__raw_pool[key]

	@classmethod
	def _raw_pool(cls):
		return cls.__raw_pool

	@classmethod
	def _child_entry_class(cls):
		return GeoNodeProxyData

	@classmethod
	def _pop_item(cls, k: ProxyID):
		# TODO
		raise NotImplementedError()

	@classmethod
	def _sync_item(cls, k: ProxyID, v: ProxyData):
		# TODO
		raise NotImplementedError()

	@classmethod
	def __load_items_to_pool(cls, *items: GeoNodeProxyData):
		# TODO
		raise NotImplementedError()

	@classmethod
	def __load_json_files(cls):
		# TODO
		raise NotImplementedError()

	@classmethod
	def __load_from_web(cls):
		# TODO
		raise NotImplementedError()

	@classmethod
	def _load(cls):
		cls.__load_json_files()
		cls.__load_from_web()

	@classmethod
	def _cache(cls):
		# TODO
		raise NotImplementedError()

	@classmethod
	def _as_standard_pool(cls) -> _pp_dict:
		def process_single_item(key: ProxyID, raw_item: GeoNodeProxyData):
			new_key, std_item = raw_item.as_standard()
			if new_key != key:
				raise RuntimeError(f'Proxy discrepancy in {cls}: {key} -> {new_key}')
			return key, std_item

		return {
			k: v for k, v in
			(process_single_item(r_k, r_v) for r_k, r_v in cls.__raw_pool.items())
		}
