# encoding: utf-8
"""
This script joins stories from different files, removing duplicates.
"""

__author__ = 'Lex Darlog (DRL)'

import typing as _t
import re as _re
from pathlib import Path
from itertools import chain


TextLines = _t.List[str]
StoryVariants = _t.List[TextLines]


def reversed_int_indices(size):
	"""An iterator over list indices, in reversed order."""
	return range(size - 1, -1, -1)


class StoriesDatabase(_t.Dict[str, StoryVariants]):
	"""
	A dict-like dataclass containing multiple stories.
	The structure is following:

	Dict[story_name] = [
		variant_0: List[str],
		variant_1: List[str],
		...
	]

	The multiple-variants design is used just in case multiple different stories
	are provided with the same name. You can remove all the duplicates later.
	"""

	root_dir = Path(__file__).parent
	src_dir = root_dir / '_src'
	out_file = root_dir / 'Combined.txt'

	story_name_pattern = _re.compile(
		'\s*-{3,}\s*'
		'(.*?)'
		'\s*-{3,}\s*$'
		# For those who are unfamiliar with regex, it ^ is this format:
		# '--- Story Name with whatever characters in it ---'
		# There ^ might be 3 or more dash chars at the beginning/end, and/or
		# any whitespace chars around dashes.
	)
	out_story_name_format = '----- {story_name} -----'

	unnamed_story_key = ''
	unnamed_story_name_out_format = 'Story # {i}'
	multi_variant_name_format = '{name} - Variant # {i}'

	out_empty_lines_after_title = 1
	out_empty_lines_after_story = 2

	def append_new_empty_variant(self, story_name: str):
		"""Adds a new empty variant for the given story."""
		if story_name not in self:
			self[story_name]: StoryVariants = list()
		variants = self[story_name]
		cur_variant: TextLines = list()
		variants.append(cur_variant)
		return cur_variant

	def parse_file(self, file_path: Path):
		"""
		Reads the entire file contents and classifies it
		to individual stories (variants).

		Returns the total number of stories/variants extracted.
		"""
		with file_path.open('rt', encoding='UTF-8') as f:
			file_lines = f.readlines()

		if not file_lines:
			return 0

		def remove_trailing_empty_lines(story: TextLines):
			for last_line in reversed(story):
				if last_line:
					break
				story.pop()

		story_name_matcher: _t.Callable[[str], _t.Match] = self.story_name_pattern.match

		# noinspection PyTypeChecker
		cur_story_variant: TextLines = None
		# noinspection PyTypeChecker
		cur_story_line_append: _t.Callable[[str], _t.Any] = None
		not_in_story_yet = True
		no_lines_in_story_yet = True
		n_vars_total = 0

		for line in file_lines:
			line = line.strip()
			name_match = story_name_matcher(line)
			if name_match or not_in_story_yet:
				story_name = ''
				if name_match:
					story_name = name_match.group(1)
				if not story_name:
					not_in_story_yet = False  # in case we got here by it
					story_name = self.unnamed_story_key

				if cur_story_variant is not None:
					# remove trailing empty lines in a currently finished story
					remove_trailing_empty_lines(cur_story_variant)
				cur_story_variant = self.append_new_empty_variant(story_name)
				cur_story_line_append = cur_story_variant.append
				n_vars_total += 1
				no_lines_in_story_yet = True
				continue  # don't add the name itself to each variant's text-list

			if no_lines_in_story_yet:
				# remove any empty lines before the story starts
				if not line:
					continue
				no_lines_in_story_yet = False
			cur_story_line_append(line)

		# remove trailing empty lines in the last story:
		if cur_story_variant is not None:
			remove_trailing_empty_lines(cur_story_variant)

		return n_vars_total

	def parse_files(self, file_paths: _t.Iterable[Path], ext=None):
		"""
		Parse multiple files in sequence.
		Paths pointing to directories are filtered out.
		"""
		if isinstance(ext, str):
			ext = [ext, ]
		if not ext:
			ext = list()
		ext_set: _t.Set[str] = {
			(e.lower() if e.startswith('.') else '.' + e.lower())
			for e in ext
			if isinstance(e, str)
		}
		if not ext_set:
			ext_set = {'.txt', }
		return sum(
			self.parse_file(path) for path in file_paths
			if path.is_file() and path.suffix.lower() in ext_set
		)

	def parse_dir(self, dir_path: Path = None):
		if not dir_path:
			dir_path = self.src_dir
		if not dir_path.exists():
			dir_path.mkdir(parents=True)
		assert dir_path.is_dir(), "Given path is not a directory"
		return self.parse_files(dir_path.iterdir())

	def remove_duplicates(self):
		"""
		Keep only a single instance of all the variants and remove all empty stories.
		"""
		def story_identifier_key(story_variant: TextLines):
			"""
			Hashable text of the whole story, without any empty lines or
			leading/trailing whitespaces.
			"""
			return tuple(
				line for line in story_variant
				if line.strip()
			)

		empty_story_key = tuple()

		for story_variants in self.values():
			unique_variants_dict: _t.Dict[_t.Tuple[str, ...], int] = {
				story_identifier_key(story_variants[i]): i
				for i in reversed_int_indices(len(story_variants))
				# we need to iterate variants ^ in reversed order to keep the first
				# duplicates, not the last ones
			}
			if empty_story_key in unique_variants_dict:
				unique_variants_dict.pop(empty_story_key)

			if len(story_variants) == len(unique_variants_dict):
				continue
			story_variants[:] = (
				story_variants[var_i]
				for var_i in sorted(unique_variants_dict.values())
				if any(line.strip() for line in story_variants[var_i])
			)

		# we have removed all the empty variants. Now, let's also remove all the
		# stories with no variants left there:
		for story_name in list(self.keys()):
			if not self[story_name]:
				self.pop(story_name)

	def combined_text(self):
		"""
		Generate a combined text of all the unique stories.
		All the duplicates are removed in process.
		The text contains no trailing newline characters.
		"""
		self.remove_duplicates()
		if not self:
			return list()  # type: TextLines

		lines_after_title = ['', ] * self.out_empty_lines_after_title
		lines_after_story = ['', ] * self.out_empty_lines_after_story

		def single_story_text(story_formatted_name: str, story_lines: TextLines):
			return chain(
				[story_formatted_name],
				iter(lines_after_title),
				story_lines,
				iter(lines_after_story),
			)

		def format_story_name(story_name: str, variant_i: int, num_vars: int):
			if story_name == self.unnamed_story_key:
				story_name = self.unnamed_story_name_out_format.format(
					name=story_name,
					i=variant_i,
				)
			elif num_vars > 1:
				story_name = self.multi_variant_name_format.format(
					name=story_name,
					i=variant_i,
				)
			return self.out_story_name_format.format(story_name=story_name)

		return chain(*(
			single_story_text(
				format_story_name(name, var_i, len(story_variants)),
				var_text
			)
			for name, story_variants in sorted(self.items())
			for var_i, var_text in enumerate(story_variants)
			if var_text
		))

	def save_out_file(self, out_file: Path = None):
		if not out_file:
			out_file = self.out_file

		if not self:
			return  # don't overwrite a file if the current DB is empty

		with out_file.open('wt', encoding='UTF-8', newline='\n') as f:
			f.writelines(ln + '\n' for ln in self.combined_text())


if __name__ == '__main__':
	db = StoriesDatabase()
	print('Reading all the text files from dir: {}'.format(db.src_dir))
	db.parse_dir()
	print('Saving to a single file with no duplicates: {}'.format(db.out_file))
	db.save_out_file()
	print('Done.')
	input()
