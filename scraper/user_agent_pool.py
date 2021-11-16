# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

from itertools import islice as _islice
import json as _json
from pathlib import Path as _Path
import random as _random
import warnings as _warnings

from common import StaticDataClass as _StaticDataClass

module_dir = _Path(__file__).parent

_t_percent = _t.Union[None, int, float]


class UserAgentID(_t.NamedTuple):
	user_agent: str
	system: str = ''


class UserAgentFullData(_t.NamedTuple):
	user_agent: str
	system: str = ''
	percent: _t_percent = None


_t_pool = _t.Dict[UserAgentID, _t_percent]
_t_pool_item = _t.Tuple[UserAgentID, _t_percent]


class UserAgentPool(_StaticDataClass):
	"""
	The initial user-agent list is taken here:

	https://techblog.willshouse.com/2012/01/03/most-common-user-agents/
	https://www.google.com/search?q=list+of+user-agent+strings+by+usage
	"""
	pool_file = module_dir / 'user_agent_pool.json'

	__pool: _t_pool = dict()

	@classmethod
	def update(cls, items: _t.Iterable[_t_pool_item]):
		cls.__pool.update(items)

	@classmethod
	def _load(cls):
		with open(cls.pool_file, 'rt', encoding='utf-8') as f:
			raw = _json.load(f)
		cls.update(
			(UserAgentID(agent, system), percent)
			for agent, system, percent in raw
		)

	@classmethod
	def _save(cls):
		pool_flattened = [
			UserAgentFullData(k.user_agent, k.system, percent)
			for k, percent in cls.__pool.items()
		]
		with open(cls.pool_file, 'wt', encoding='utf-8') as f:
			return _json.dump(pool_flattened, f)

	@classmethod
	def pool(cls):
		if not cls.__pool:
			cls._load()
		return cls.__pool

	@classmethod
	def __contains__(cls, key: UserAgentID):
		return key in cls.pool

	@staticmethod
	def __sorted_items(pool: _t_pool) -> _t.List[_t_pool_item]:
		def sort_key(item) -> _t.Tuple[bool, _t_percent]:
			percent = item[1]
			return percent is not None, percent

		return sorted(
			pool.items(), key=sort_key, reverse=True
		)

	@classmethod
	def n_most_popular(
		cls, n: _t.Optional[int] = 20, normalize_percent=False,
	) -> _t.Tuple[UserAgentFullData, ...]:
		pool = cls.pool()
		total = len(pool)
		if n is None:
			n = total
		n = max(0, n)
		if n > total:
			_warnings.warn(
				f"Not enough user-agents in pool: asked for {n}, pool has only {total}",
				category=RuntimeWarning, stacklevel=2
			)
			n = total

		res = _islice(cls.__sorted_items(pool), 0, n)
		if normalize_percent:
			percent_sum = sum(x for x in res.values() if x is not None)
			if percent_sum != 100 and percent_sum != 0:
				scale = 100.0 / percent_sum
				res = (
					(k, (v if v is None else v * scale))
					for k, v in res
				)
		return tuple(UserAgentFullData(k.user_agent, k.system, v) for k, v in res)

	@classmethod
	def n_random(
		cls, n: _t.Optional[int] = 20,
		n_popular_chosen_from: _t.Optional[int] = None,
		normalize_percent=False,
	) -> _t.Tuple[UserAgentFullData, ...]:
		chosen_from = cls.n_most_popular(n_popular_chosen_from, normalize_percent)
		total = len(chosen_from)
		if n > total:
			_warnings.warn(
				f"Not enough user-agents in pool: asked for {n}, pool has only {total}",
				category=RuntimeWarning, stacklevel=2
			)
			n = total

		return tuple(_random.sample(chosen_from, n))

if __name__ == '__main__':
	test_n = 20
	best = UserAgentPool.n_most_popular(test_n)
	print(f"{test_n} most used agents:")
	for ua, sys, pc in best:
		ps = f'{pc:.2f}'
		print(f'{pc:.2f}%\t{ua}')

	print(f"\n{test_n} most used systems:")
	for ua, sys, pc in best:
		ps = f'{pc:.2f}'
		print(f'{pc:.2f}%\t{sys}')

	print(f"\n{test_n} randomly selected:")
	for ua, sys, pc in UserAgentPool.n_random(test_n):
		ps = f'{pc:.2f}'
		print(f'{pc:.2f}%\t{ua}')
