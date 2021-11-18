# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

from pathlib import Path
from common import StaticDataClass as _StaticDataClass


class Paths(_StaticDataClass):
	"""Static class with package-wise constants about local filesystem paths."""

	package_dir = Path(__file__).parent
	benchmark_cache_dir = package_dir / 'benchmarks'
	tags_cache_dir = package_dir / 'tags_cache'

	reserved_chars = tuple(r'<>:"/|\?*')
	reserved_placeholder = ''
