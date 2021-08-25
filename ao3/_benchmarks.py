# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
from pprint import pprint as pp

from bs4 import (
	BeautifulSoup,
	Tag as _bsTag
)

import requests
from datetime import datetime as dt

from pympler import asizeof

from ao3._utils import human_bytes, format_thousands
from ao3.__url import URLs
from ao3.__paths import Paths, _StaticDataClass


class BenchTagSearch(_StaticDataClass):
	"""
Started: 2021-08-25 22:49:15.632240
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda
Size in RAM: 78.156 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=2
Size in RAM: 79.586 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=3
Size in RAM: 79.398 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=4
Size in RAM: 80.172 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=5
Size in RAM: 80.273 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=6
Size in RAM: 78.797 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=7
Size in RAM: 81.039 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=8
Size in RAM: 79.008 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=9
Size in RAM: 79.789 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=10
Size in RAM: 77.852 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=11
Size in RAM: 78.008 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=12
Size in RAM: 77.969 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=13
Size in RAM: 79.156 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=14
Size in RAM: 79.391 KiB
https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&page=15
Size in RAM: 69.898 KiB

End: 2021-08-25 22:49:27.187464
Time spent: 0:00:11.555224

Pages: 15

Average page size in RAM: 78.566 KiB
Total size as list: 1.151 MiB
Total size as dict: 1.152 MiB

Estimate sizes:
150 pages:	785.661 KiB
1'500 pages:	7.672 MiB
15'000 pages:	76.725 MiB
150'000 pages:	767.248 MiB
	"""

	n_pages = 15
	url = "https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&query[type]="
	# page1 = "https://archiveofourown.org/tags/search?page=2&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda&query[type]=&utf8=✓"

	sort_key_map = {
		'utf8': -2,
		'page': 99,
	}

	cache_file_pattern = 'TagSearch-page-{:02d}.html'

	@classmethod
	def split_url(cls):
		try:
			return cls.__split_url
		except AttributeError:
			cls.__split_url = URLs.split(cls.url)
		return cls.__split_url

	@classmethod
	def query(cls):
		try:
			return cls.__query
		except AttributeError:
			cls.__query = URLs.split_qs_dict(cls.split_url().query)
		return cls.__query

	@classmethod
	def _query_item_sorting_key(cls, args) -> _t.Tuple[str, ...]:
		key, *args = (str(x) for x in args)
		if key in cls.sort_key_map:
			# noinspection PyTypeChecker
			return (cls.sort_key_map[key], key, *args)
		# noinspection PyTypeChecker
		return (0, key, *args)

	@classmethod
	def build_page_url(cls, **override_keys):
		query = dict(cls.query())
		for k, v in override_keys.items():
			if k == 'page' and v is None or int(v) in {0, 1}:
				if k in query:
					query.pop(k)
				continue
			if v is not None:
				query[k] = v
		q_sorted = sorted(query.items(), key=cls._query_item_sorting_key)
		new_split = list(cls.split_url())
		new_split[3] = URLs.unquote_plus(URLs.unsplit_qs(q_sorted, doseq=True))
		return URLs.SplitResult(*new_split).geturl()

	@classmethod
	def page_urls(cls):
		try:
			return cls.__page_urls
		except AttributeError:
			cls.__page_urls = [
				cls.build_page_url(page=x) for x in range(1, cls.n_pages + 1)
			]
		return cls.__page_urls

	@classmethod
	def _cache_pages_to_files(cls, pages_content: _t.Iterable[str]):
		cache_dir = Paths.benchmark_cache_dir
		if not cache_dir.exists():
			cache_dir.mkdir()

		print('\nSaving cached pages...')
		for i, page_html in enumerate(pages_content):
			file_path = cache_dir / cls.cache_file_pattern.format(i)
			print(f'\t{file_path}')
			with file_path.open('wt', encoding='UTF-8', newline='\n') as f:
				f.write(page_html)

	@classmethod
	def test_page_size(cls, cache_pages=True):
		def do_single(page_url: str):
			print(page_url)
			page = requests.get(page_url).text
			mem_size = asizeof.asizeof(page)
			print(f'Size in RAM: {human_bytes(mem_size)}')
			return page, mem_size

		page_urls = cls.page_urls()

		start = dt.now()
		print(f'Started: {start}')
		res = [
			do_single(url)
			for url in page_urls
		]
		end = dt.now()
		print(f'\nEnd: {end}\nTime spent: {end-start}')

		n = len(res)
		print(f'\nPages: {n}')
		avg_size = sum(m for p, m in res) / float(n)
		print(f'\nAverage page size in RAM: {human_bytes(avg_size)}')
		print(f'Total size as list: {human_bytes(asizeof.asizeof([p for p, m in res]))}')
		print(f'Total size as dict: {human_bytes(asizeof.asizeof({i: p for i, (p, m) in enumerate(res)}))}')

		print('\nEstimate sizes:')
		for x_n in (10, 100, 1000, 10000):
			print(f'{format_thousands(str(n * x_n))} pages:\t{human_bytes(avg_size * x_n)}')

		if cache_pages:
			cls._cache_pages_to_files(html for html, size in res)

		return res


if __name__ == '__main__':
	sizes = BenchTagSearch.test_page_size()
