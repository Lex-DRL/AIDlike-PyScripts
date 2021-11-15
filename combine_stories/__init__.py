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
TextLinesIter = _t.Iterable[str]
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

	print_progress = True
	root_dir = Path(__file__).parent
	src_dir = root_dir / '_src'
	out_file = root_dir / 'Combined.txt'

	# a dumb cleanup, removing any stories that have a line
	# starting with '<link rel=' :
	remove_code = True
	code_pattern = _re.compile(
		'\\s*<link\\s+rel\\s*='
	)

	# replace HTML char-codes to actual chars:
	html_chars_replace = True
	html_chars_map: _t.List[_t.Tuple[str, str]] = [
		# ASCII:
		('&amp;', '&'),
		('&nbsp;', ' '),
		('&times;', '*'),
		('&divide;', '/'),
		('&lt;', '<'),
		('&gt;', '>'),

		# various quotes:
		('&quot;', '"'),
		('&lsquo;', '"'),
		('&rsquo;', '"'),
		('&ldquo;', '"'),
		('&rdquo;', '"'),
		('&bdquo;', '"'),
		('&laquo;', '"'),
		('&raquo;', '"'),

		('&prime;', "'"),
		('&Prime;', "''"),
		('&sbquo;', ','),

		# "nice" punctuation:
		('&ndash;', '-'),
		('&mdash;', '-'),
		('&hellip;', '...'),

		# upper script marks:
		('&copy;', '©'),
		('&reg;', '®'),
		('&trade;', '™'),
		('&deg;', '°'),
	]

	# In order to detect identical stories, their lines are pre-cleaned-up.
	# This list defines these replacements performed in this specific order.
	# The third argument specifies whether the given replacement needs to be
	# performed in a loop, until no pattern occurrence found.
	story_id_cleanup = [
		# pattern, replacement, do_in_loop:
		('\t', ' ', False),

		('[', '(', False),
		('{', '(', False),
		('<', '(', False),
		(']', ')', False),
		('}', ')', False),
		('>', ')', False),

		(_re.compile('\\(\\s+'), '(', False),
		(_re.compile('\\s+\\)'), ')', False),
		('(', ' (', False),
		(')', ') ', False),

		(_re.compile('\\s+-'), ' - ', False),
		(_re.compile('\\s*-\\s+'), ' - ', False),
		(_re.compile('\\s+,'), ',', False),
		(_re.compile(',\\s*'), ', ', False),
		(_re.compile('\\s+\\.'), '.', False),

		(_re.compile('\\?{2,}'), '?', False),
		(_re.compile('![1!]+'), '!', False),
		(_re.compile('[?!]{2,}'), '?!', False),

		('`', "'", False),
		(_re.compile("'{2,}"), '"', False),
		# any combination of various quotes in a row:
		(_re.compile("[\"']*(?:'+\"+|\"+'+)[\"']*"), '"', False),
		(_re.compile('"{3,}'), '""', False),

		(_re.compile('\\s{2,}'), ' ', False),
	]

	story_name_pattern = _re.compile(
		'\\s*-{3,}[-\\s]*'
		'([^\\s-].*?)'
		'[-\\s]*-{3,}\\s*$'
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

	def parse_text(self, text_lines: TextLines):
		"""Parse a chunk of text for individual stories and append them."""

		if not text_lines:
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

		for line in text_lines:
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

	def parse_file(self, file_path: Path):
		"""
		Reads the entire file contents and classifies it
		to individual stories (variants).

		Returns the total number of stories/variants extracted.
		"""
		if self.print_progress:
			if not file_path:
				print('\tNo file path given!')
			else:
				print('\t{}'.format(file_path))

		if not file_path:
			return 0

		with file_path.open('rt', encoding='UTF-8') as f:
			file_lines = f.readlines()
		return self.parse_text(file_lines)

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

		file_paths = (
			path for path in file_paths
			if path.is_file() and path.suffix.lower() in ext_set
		)
		if self.print_progress:
			file_paths = list(file_paths)
			if not file_paths:
				print('\tNo valid file paths!')

		return sum(map(self.parse_file, file_paths))

	def parse_dir(self, dir_path: Path = None):
		if not dir_path:
			dir_path = self.src_dir
		if not dir_path.exists():
			if self.print_progress:
				print(
					'Creating an empty directory for source text files: '
					'{}'.format(dir_path)
				)
			dir_path.mkdir(parents=True)
			return 0
		assert dir_path.is_dir(), "Given path is not a directory"
		if self.print_progress:
			print('Reading all the text files from dir: {}'.format(dir_path))
		return self.parse_files(dir_path.iterdir())

	def is_code_story(self, story: _t.Iterable[str]):
		"""Whether the given story has some garbage code from scrape."""
		matcher = self.code_pattern.match
		return any(matcher(line) for line in story)

	def cleanup_stories(self):
		"""
		Clean all the stories variants:
			* Keep only a single instance if a story has multiple identical variants.
			* Replace HTML special character codes to the actual characters.
			* Remove any leading/trailing whitespaces.
			* Remove all empty variants and stories with no variants left.

		This cleanup is NOT a replacement for a regular data preparation,
		it's only a last resort to fix some tiny issues. If the source text completely
		messed up, you better of cleaning it yourself before passing it to this class.
		"""

		def key_line_replacer_f(*args):
			"""
			A factory that returns a function that performs a specific replacement
			on a single key line, or None if wrong arguments are given.
			Args are story_id_cleanup items.
			"""
			n = len(args)
			if n < 1:
				return None

			pattern: _t.Union[_t.Pattern, str] = args[0]
			repl: str = '' if n < 2 else args[1]
			do_loop: bool = False if n < 3 else args[2]

			# simple case: basic string replacement
			if isinstance(pattern, str):
				def simple_no_loop(line: str):
					return line.replace(pattern, repl)

				def simple_with_loop(line: str):
					while pattern in line:
						line = line.replace(pattern, repl)
					return line

				return simple_with_loop if do_loop else simple_no_loop

			# complex case - regex:
			try:
				sub = pattern.sub
			except:
				return None

			def re_no_loop(line: str):
				return sub(repl, line)

			def re_with_loop(line: str):
				prev_line = ''
				while prev_line != line:
					prev_line = line
					line = sub(repl, line)
				return line

			return re_with_loop if do_loop else re_no_loop

		def story_identifier_key(story_variant: TextLinesIter):
			"""
			Hashable text of the whole story, without any empty lines or
			leading/trailing whitespaces.
			"""
			for cleanup_args in self.story_id_cleanup:
				replacer_f = key_line_replacer_f(*cleanup_args)
				if replacer_f is None:
					continue
				story_variant = map(replacer_f, story_variant)

			return tuple(filter(None, story_variant))

		def replace_html_chars_single_line_dec(do_replace: bool):
			"""
			Conditionally add html-chars replacement after the main cleanup func.
			"""
			def decorator(f: _t.Callable[[str], str]):
				# cache as tuple of tuples - for some perf optimization
				html_chars_map: _t.Tuple[_t.Tuple[str, str], ...] = tuple(
					(src, repl)
					for src, repl, *buffer in self.html_chars_map
				)

				def wrapper(line: str):
					line = f(line)
					for char_code, out_char in html_chars_map:
						line = line.replace(char_code, out_char)
					return line

				return wrapper if do_replace else f
			return decorator

		@replace_html_chars_single_line_dec(self.html_chars_replace)
		def cleanup_single_line(line: str):
			return line.strip()

		empty_story_key = tuple()

		for story_variants in self.values():
			story_variants_clean = tuple(
				[cleanup_single_line(ln) for ln in variant_text]
				for variant_text in story_variants
			)
			unique_variants_dict: _t.Dict[_t.Tuple[str, ...], int] = {
				story_identifier_key(story_variants_clean[i]): i
				for i in reversed_int_indices(len(story_variants_clean))
				# we need to iterate variants ^ in reversed order to keep the first
				# duplicates, not the last ones
			}
			if empty_story_key in unique_variants_dict:
				unique_variants_dict.pop(empty_story_key)

			if self.remove_code:
				for story_id_tuple in list(unique_variants_dict.keys()):
					story_i = unique_variants_dict[story_id_tuple]
					# The id-tuple may be cleaned up 'too much', containing some
					# messed-up brackets, so we need to check the actual clean story,
					# not id-tuple:
					if self.is_code_story(story_variants_clean[story_i]):
						unique_variants_dict.pop(story_id_tuple)

			if len(story_variants_clean) == len(unique_variants_dict):
				continue

			id_to_unique_text_tuple_map: _t.Dict[int, _t.Tuple[str, ...]] = {
				i: id_tuple for id_tuple, i in unique_variants_dict.items()
			}
			story_variants[:] = (
				story_variants_clean[var_i]
				for var_i, text_tuple in sorted(id_to_unique_text_tuple_map.items())
				if any(line for line in text_tuple)
			)

		# we have removed all the empty variants. Now, let's also remove all the
		# stories with no variants left there:
		for story_name in list(self.keys()):
			# we need to apply the same line-cleanup to the story names themselves:
			clean_name = cleanup_single_line(story_name)
			if clean_name != story_name:
				self[clean_name] = self.pop(story_name)
				story_name = clean_name

			if not self[story_name]:
				self.pop(story_name)

	def combined_text(self):
		"""
		Generate a combined text of all the unique stories.
		All the duplicates are removed in process.
		The text contains no trailing newline characters.
		"""
		self.cleanup_stories()
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
			# don't overwrite a file if the current DB is empty
			if self.print_progress:
				print('No stories parsed, skipping file output.')
			return

		if self.print_progress:
			print('Saving to a single file with no duplicates: {}'.format(out_file))

		with out_file.open('wt', encoding='UTF-8', newline='\n') as f:
			f.writelines(ln + '\n' for ln in self.combined_text())


if __name__ == '__main__':
	db = StoriesDatabase()
	db.parse_dir()
	db.save_out_file()
	print('Done.')
	input()
