# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

from pathlib import Path
from dataclasses import dataclass as _dataclass


@_dataclass(init=False, frozen=True)
class _StaticDataClass:
	def __init__(self):
		raise TypeError(f"<{self.__class__.__name__}> is non-instantiable data class")


class Paths(_StaticDataClass):
	package_dir = Path(__file__).parent
	benchmark_cache_dir = package_dir / 'benchmarks'
