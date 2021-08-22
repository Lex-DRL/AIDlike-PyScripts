# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
from pathlib import Path
from enum import Enum


module_dir = Path(__file__).parent


class TagType(Enum):
	Fandom = 0
	Character = 1
	Relationship = 2
	Freeform = 3

	Unsorted = 7


class Tag(_t.NamedTuple):
	"""
	NamedTuple representing a tag.

	Only first two items (name/type) are used for any comparisons and hashing,
	optional items are ignored.
	Therefore:
		* `(name, type) == tag_instance`
		* `(name, type, url) != tag_instance`
		* `(name, type, url, usages, canonical) != tag_instance`

	So beware about it. Since, if you slice it, the newly created regular tuple
	is no longer equal to the tag instance, because it contains all the items and
	the instance itself is "represented" with just two in equality check.

	Similarly, if you have two tag instances with different values in optional
	items and you make a set of them / dict with them as keys - then only one
	of them will get into the set.
	"""
	name: str
	type: TagType
	url: str = ''
	usages: int = -1
	canonical: bool = False

	def __eq__(self, other):
		if isinstance(other, Tag):
			other = other[:2]
		return self[:2] == (other[:2] if isinstance(other, Tag) else other)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return hash(self[:2])
