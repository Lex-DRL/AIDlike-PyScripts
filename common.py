# encoding: utf-8
"""
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t

from dataclasses import dataclass as _dataclass


@_dataclass(init=False, frozen=True)
class StaticDataClass:
	"""Base for static (non-instantiable) classes."""

	def __init__(self):
		raise TypeError(f"<{self.__class__.__name__}> is non-instantiable data class")
