# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
from pathlib import Path
from enum import Enum
from datetime import (
	datetime as dt,
	timezone as tz,
)

import requests
# noinspection PyProtectedMember
from bs4 import (
	BeautifulSoup,
	Tag as _bsTag
)

from .__url import URLs
from .__paths import _StaticDataClass


parser = 'lxml'


class TagType(Enum):
	Fandom = 0
	Character = 1
	Relationship = 2
	Freeform = 3

	Unsorted = 7

	def __repr__(self):
		return "%s.%s" % (self.__class__.__name__, self.name)


type_parse_map = {
	'Fandom': TagType.Fandom,
	'Character': TagType.Character,
	'Relationship': TagType.Relationship,
	'Freeform': TagType.Freeform,
	'UnsortedTag': TagType.Unsorted,
}


# def init_tag_cleanup_dec(class_obj: _t.Type[_t.NamedTuple]):
# 	def new_instance(*args, **kwargs):
# 		if len(args) > 4:
# 			args_list = list(args)
# 			args_list[4] = clean_url(args[4])
# 			args = tuple(args_list)
# 		if 'url_token' in kwargs:
# 			kwargs['url_token'] = clean_url(kwargs['url_token'])
# 		return class_obj(*args, **kwargs)
#
# 	return new_instance


_unknown_tag_usage = -1  # default <usage> value


_type = type
NoneType = type(None)


# @init_tag_cleanup_dec
class Tag(_t.NamedTuple):
	"""
	NamedTuple representing a tag.

	For equality check and hashing, only name and url_token are used since they're
	the ones uniquely identifying a tag.
	Therefore:
		* `(name, url_token) == tag_instance`
		* `(type, name, url_token) != tag_instance`
		* `(type, name, url_token, canonical, usages, date) != tag_instance`

	So beware about it. Since, if you just make a full slice, the newly created
	regular tuple is already not equal to the tag instance.

	Similarly, if you have two tag instances with only other optional field varying
	and you make a set of them / dict with them as keys - then only one of them
	would get into the set.
	"""
	type: _t.Union[None, TagType, str]
	name: str
	url_token: str = None
	canonical: _t.Optional[bool] = False
	usages: int = _unknown_tag_usage
	date: _t.Optional[dt] = None

	# noinspection PyAttributeOutsideInit
	@property
	def id(self):
		"""The actual value the tag is represented as during hashing/equality check."""
		return self.name, self.url_token

	def __eq__(self, other):
		return self.id == (
			other.id if isinstance(other, Tag) else other
		)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return hash(self.id)

	@classmethod
	def _clean_date(cls, calling_method: str, date: _t.Optional[dt], name: str = None):
		"""
		Part of `_clean_args()` that checks only date argument
		(it might be needed to check it separately).
		"""
		tag_part = cls.__name__ if name is None else f'for tag <{name}>'
		assert isinstance(date, (NoneType, dt)), (
			f'Wrong date {tag_part}.{calling_method}(): {repr(date)}'
		)
		date: _t.Optional[dt] = date
		return date

	# noinspection PyShadowingBuiltins
	@classmethod
	def _clean_args(
		cls,
		calling_method: str,
		*args,
		url_token_already_clean=False  # we need to know whether it's already not an URL
	):
		"""Perform check on input arguments and auto-clean them if possible."""

		type, name, url_token, canonical, usages, date, *extras = args

		assert name and isinstance(name, str), (
			f'Invalid tag name passed to {cls.__name__}.{calling_method}(): {repr(name)}'
		)

		if (
			url_token != _TagDumpConfig.token_match_name_indicator
			and not url_token_already_clean
		):
			# url_token = 'https://archiveofourown.org/tags/Admiral%20Anderson'
			# url_token = '/tags/Mass%20Effect%20Trilogy'
			# url_token = 'Mass Effect Trilogy'
			# url_token = 'Mass Effect Trilogy/works'
			url_token: str = URLs.split(url_token, unquote=True, to_abs=False).path
			if url_token.startswith(URLs.tag_root):
				url_token = url_token[URLs.tag_root_n:]
			url_token = url_token.split('/')[0]
			if url_token == name:
				url_token = _TagDumpConfig.token_match_name_indicator

		assert isinstance(url_token, str) and (
			not url_token
			or url_token == _TagDumpConfig.token_match_name_indicator
			or _TagDumpConfig.token_match_name_indicator not in url_token
		), (
			f'Wrong URL for tag <{name}>.{calling_method}(): {repr(url_token)}'
		)

		if canonical is not None:
			canonical = bool(canonical)

		if usages is None:
			usages = _unknown_tag_usage

		assert isinstance(type, (NoneType, TagType, str)), (
			f'Wrong type for tag <{name}>.{calling_method}(): {repr(type)}'
		)
		assert isinstance(canonical, (NoneType, bool)), (
			f'Wrong canonical state for tag <{name}>.{calling_method}(): {repr(canonical)}'
		)
		assert isinstance(usages, int), (
			f'Wrong usages for tag <{name}>.{calling_method}(): {repr(usages)}'
		)

		type: _t.Union[None, TagType, str] = type
		canonical: _t.Optional[bool] = canonical
		date: _t.Optional[dt] = cls._clean_date(calling_method, date, name)
		if date is None and usages > -1:
			date = dt.now()

		return type, name, url_token, canonical, usages, date

	# noinspection PyShadowingBuiltins
	@classmethod
	def new_instance(
		cls,
		type: _t.Union[None, TagType, str],
		name: str,
		url_token: _t.Optional[str] = None,
		canonical: _t.Optional[bool] = False,
		usages: _t.Optional[int] = _unknown_tag_usage,
		date: _t.Optional[dt] = None,
	):
		"""
		Use this constructor method instead of just `Tag()`, because it performs
		some extra arguments check/cleanup.
		"""
		type, name, url_token, canonical, usages, date = cls._clean_args(
			'new_instance',
			type, name, url_token, canonical, usages, date,
		)

		return cls(type, name, url_token=url_token, canonical=canonical, usages=usages, date=date,)

	@classmethod
	def build_from_li(cls, tag_li: _bsTag):
		"""Build a tag object from tag's <li> html on search page."""

		# <li>
		# <span class="canonical">
		# 	Character:
		# 	<a class="tag" href="/tags/Male%20Shepard%20(Mass%20Effect)">
		# 		Male Shepard (Mass Effect)
		# 	</a>
		# 	‎(2806)
		# </span>
		# </li>
		a = tag_li.find('a', class_='tag')
		span = a.find_parent('span')
		span_attrs = span.attrs

		canonical = (
			bool(span_attrs)
			and 'class' in span_attrs
			and 'canonical' in span_attrs['class']
		)

		type_str = span.find(text=True).strip().rstrip(':')
		tag_type = type_parse_map.get(type_str, str(type_str))

		return cls.new_instance(
			tag_type, a.text, canonical=canonical, url_token=a.get('href')
		)

	@classmethod
	def date_str(cls, date: _t.Optional[dt]):
		clean_date = cls._clean_date('date_str', date)
		if clean_date is None:
			return ''
		return clean_date.strftime(_TagDumpConfig.date_format)

	@classmethod
	def date_from_str(cls, date_str: _t.Optional[str], in_timezone=None):
		if not date_str:
			return None
		return dt.strptime(date_str, _TagDumpConfig.date_format).astimezone(in_timezone)

	@classmethod
	def reorder_to_dump(cls, items: _t.Iterable):
		"""Reorder tag elements from tuple to dumped order."""
		# noinspection PyShadowingBuiltins
		type, name, url_token, canonical, usages, date, *left = items
		return name, url_token, type, canonical, usages, date

	# noinspection PyShadowingBuiltins
	def dumps(self) -> _t.Tuple[str, ...]:
		"""Dump tag object to a string representation for saving to a file."""

		type, name, url_token, canonical, usages, date = self._clean_args(
			'dumps', *self,
			url_token_already_clean=True
		)

		dump_maps = _TagDumpConfig.dump_map

		if not type:
			type = ''
		if isinstance(type, TagType):
			# noinspection PyTypeChecker
			type: str = dump_maps.type[type]
		assert isinstance(type, str)

		# noinspection PyUnresolvedReferences
		canonical_s: str = dump_maps.canonical[canonical]

		if usages is None or usages < 0:
			usages = -1
		usages_s: str = '' if usages < 0 else str(usages)

		date_s = '' if date is None else self.date_str(date.astimezone(tz=tz.utc))

		return self.reorder_to_dump(
			id + val for id, val in zip(
				_TagDumpConfig.dump_id,
				(type, name, url_token, canonical_s, usages_s, date_s),
			)
		)


# noinspection PyTypeChecker
class _TagDumpConfig(_StaticDataClass):
	"""Constants related to dumped tag format."""

	date_format: str = '%Y.%m.%d-%H:%M:%S|%Z'

	# A char that can't possibly be inside url token, we use it to indicate that
	# token url is exactly the same as name, to save on dump size (and mem footprint):
	token_match_name_indicator = '/'

	dump_id = Tag(
		type='-Tp:', name='-Tag:', url_token='-URL:',
		canonical='-Canon:', usages='-Use:', date='-Dt:',
	)
	dump_map = Tag(
		type={
			TagType.Fandom: 'Fandom',
			TagType.Character: 'Character',
			TagType.Relationship: 'Relationship',
			TagType.Freeform: 'Freeform',
			TagType.Unsorted: 'UnsortedTag',
		},
		name=None,
		url_token=None,
		canonical={
			None: '',
			True: '+',
			False: '-',
		},
		usages=None,
		date=None,
	)


class __TagIO(object):
	"""Base class with common methods for loading/saving tags."""

	def _load_from_search_page(self, url: str):
		"""Parse a single search page for tags."""

		def prepare_clean_split_url(src_url: str):
			"""Cleanup URL, turn it to standard (split) form, then re-quote it."""
			protocol, domain, path, query, *rest = URLs.split(src_url)
			protocol, domain, *rest = (
				URLs.quote(x, safe='') for x in (protocol, domain, *rest)
			)
			# path heeds special treatment:
			path = URLs.quote(path, safe='/')
			query = URLs.quote(query, safe='&=')
			return URLs.SplitResult(protocol, domain, path, query, *rest)

		url_split = prepare_clean_split_url(url)
		assert url_split.path.startswith(URLs.tag_search_root), f"Not a tag search page: {url}"
		url = url_split.geturl()

		page = BeautifulSoup(requests.get(url).text, parser)
		tag_ols = page.find_all('ol', class_='tag index group')
		assert len(tag_ols) == 1, f"Found {len(tag_ols)} tag lists"
		tag_ol: _bsTag = tag_ols[0]
		tag_lines = tag_ol.find_all('li')

		return (Tag.build_from_li(tag_li) for tag_li in tag_lines)


class TagSet(_t.Set[Tag], __TagIO):

	name: str = ''

	def __init__(self, *args, name: str = ''):
		super(TagSet, self).__init__(*args)
		if name:
			self.name = name

	def _load_from_search_page(self, url: str):
		self.update(
			super(TagSet, self)._load_from_search_page(url)
		)
		return self

	def __repr__(self):
		res = super(TagSet, self).__repr__()
		if self.name:
			res = res.replace('(', f'({repr(self.name)}: ', 1)
		return res


if __name__ == '__main__':
	tags = TagSet(name='QQQ')
	tags._load_from_search_page(
		"https://archiveofourown.org/tags/search?utf8=✓&query[name]=male shepard NOT female NOT she NOT edi NOT Ashley NOT Williams NOT Liara NOT Tali'Zorah NOT Miranda"
	)