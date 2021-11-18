# encoding: utf-8
"""
Common typing shorthands named to stay protected in the module they're
imported to, while still being able to import with::

	from drl_typing import *
"""

from enum import Enum, EnumMeta

__all__ = [
	'_t',
	'_Tp', '_tA', '_c', '_o', '_u',
	'_d', '_tpl', '_NT', '_l', '_set', '_i', '_seq', '_gen',
	'_TpVar', '_str',
	'_reM', '_reP',
	'_if', '_T', '_KT', '_VT', '_TIter', '_TSeq',
	'_o_b', '_o_if',
	'_o_str', '_tpl_str', '_l_str', '_set_str', '_i_str', '_seq_str', '_gen_str',

	'_t_enum', '_t_enum_meta',
]

import typing as _t
# noinspection PyPep8Naming
from typing import (
	Type as _Tp,
	Any as _tA,
	Callable as _c,
	Optional as _o,
	Union as _u,

	Dict as _d,
	Tuple as _tpl,
	NamedTuple as _NT,
	List as _l,
	Set as _set,
	Iterable as _i,
	Sequence as _seq,
	Generator as _gen,

	# TypeVars:
	TypeVar as _TpVar,
	AnyStr as _str,

	Match as _reM,
	Pattern as _reP,
)

# noinspection PyTypeHints,PyShadowingBuiltins
_if = _TpVar('IntFloat', int, float)

# re-create standard TypeVars:
# noinspection PyTypeHints,PyShadowingBuiltins
_T = _TpVar('T')  # Any type.
# noinspection PyTypeHints,PyShadowingBuiltins
_KT = _TpVar('KT')  # Key type.
# noinspection PyTypeHints,PyShadowingBuiltins
_VT = _TpVar('VT')  # Value type.

# noinspection PyTypeHints,PyShadowingBuiltins
_TIter = _TpVar('TIter', bound=_i)
# noinspection PyTypeHints,PyShadowingBuiltins
_TSeq = _TpVar('TSeq', bound=_seq)

_o_b = _o[bool]
_o_if = _u[None, _if]

_o_str = _o[_str]
_tpl_str = _tpl[_str, ...]
_l_str = _l[_str]
_set_str = _set[_str]
_i_str = _i[_str]
_seq_str = _seq[_str]
_gen_str = _gen[_str, _tA, None]

# noinspection PyTypeHints,PyShadowingBuiltins
_t_enum = _TpVar('EnumType', _Tp[Enum], EnumMeta)
_t_enum_meta = _Tp[EnumMeta]
