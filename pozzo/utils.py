#!/usr/bin/env python3
#
#  rope.py
"""
Call Godot to create exports.
"""
#
#  Copyright © 2026 Dominic Davis-Foster <dominic@davis-foster.co.uk>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.
#

# stdlib
import sys
from typing import IO, Iterable, Mapping, Optional, TextIO, Tuple, TypeVar, Union

# 3rd party
import tqdm
from consolekit.terminal_colours import Fore, Style, resolve_color_default, strip_ansi

__all__ = ["ProgressBar", "has_pathsep", "should_show_colours"]


def has_pathsep(value: str) -> bool:
	"""
	Returns whether the given string contains a path separator.

	:param value:
	"""

	if '/' in value:
		return True

	if '\\' in value:
		return True

	return False


class ProgressBar(tqdm.tqdm):  # noqa: PRM002
	"""
	Customised ``tqdm`` progressbar.
	"""

	total: int

	def __init__(
			self,
			iterable: Optional[Iterable] = None,
			desc: Optional[str] = None,
			total: Optional[float] = None,
			leave: bool = True,
			file: IO = sys.stdout,
			ncols: Optional[int] = None,
			mininterval: float = 0.1,
			maxinterval: float = 10.0,
			miniters: Optional[float] = None,
			ascii: Union[bool, str, None] = None,  # noqa: A002  # pylint: disable=redefined-builtin
			unit: str = "it",
			unit_scale: Union[bool, float] = False,
			dynamic_ncols: bool = False,
			smoothing: float = 0.3,
			bar_format: Optional[str] = None,
			initial: float = 0,
			position: Optional[int] = None,
			postfix: Union[Mapping[str, object], str, None] = None,
			unit_divisor: float = 1000,
			write_bytes: Optional[bool] = False,
			lock_args: Union[Tuple[Optional[bool], Optional[float]], Tuple[Optional[bool]], None] = None,
			nrows: Optional[int] = None,
			colour: Optional[str] = None,
			delay: Optional[float] = 0,
			gui: bool = False,
			show_colours: Optional[bool] = None,
			) -> None:

		self.show_colours = should_show_colours(stream=file, colour=resolve_color_default(show_colours))
		if not self.show_colours:
			colour = False  # type: ignore[assignment]

		super().__init__(  # type: ignore[call-arg]
			iterable,  # type: ignore[arg-type]
			desc=desc,
			total=total,
			leave=leave,
			file=file,
			ncols=ncols,
			mininterval=mininterval,
			maxinterval=maxinterval,
			miniters=miniters,
			ascii=ascii,
			disable=hasattr(sys.stdout, "isatty") and not sys.stdout.isatty(),
			unit=unit,
			unit_scale=unit_scale,
			dynamic_ncols=dynamic_ncols,
			smoothing=smoothing,
			bar_format=bar_format,
			initial=initial,
			position=position,
			postfix=postfix,
			unit_divisor=unit_divisor,
			write_bytes=write_bytes,
			lock_args=lock_args,
			nrows=nrows,
			colour=colour,
			delay=delay,
			gui=gui,
		)

		self._error_count = 0
		self._warning_count = 0

	def info(self, message: str) -> None:
		"""
		Print the given information message, in bright/bold text.

		:param message:
		"""

		self.write(Style.BRIGHT(message))

	def write(  # type: ignore[override]
		self,
		s: str,
		file: Optional[TextIO] = None,
		end: str = '\n',
		nolock: bool = False,
	) -> None:
		"""
		Write to stdout without overlapping the progressbar.

		:param s:
		:param file:
		:param end:
		:param nolock:
		"""

		# When outputting to a file instead of a terminal, strip codes.
		if not self.show_colours:
			s = strip_ansi(s)

		super().write(s, file=file, end=end, nolock=nolock)

		if not sys.stdout.isatty():
			sys.stdout.flush()

		if not sys.stdout.isatty():
			sys.stderr.flush()

	def error(self, message: str) -> None:
		"""
		Print the given error message, in yellow text.

		:param message:
		"""

		self._error_count += 1
		self.write(Fore.RED(message))

	def warning(self, message: str) -> None:
		"""
		Print the given warning message, in yellow text.

		:param message:
		"""

		self._warning_count += 1
		self.write(Fore.YELLOW(message))

	def report_errors_warnings(self, message: str = '') -> None:
		"""
		Print the given message followed by a count of errors and warnings, if any.

		:param message:
		"""

		if self._error_count:
			if self._error_count >= 1:
				message += f"{self._error_count} errors"
			else:
				message += f"{self._error_count} error"

			if self._warning_count:
				message += "; "

		if self._warning_count:
			if self._warning_count >= 1:
				message += f"{self._warning_count} warnings."
			else:
				message += f"{self._warning_count} warning."

		if message:
			if self._error_count:
				self.write(Fore.RED(message))
			elif self._warning_count:
				self.write(Fore.YELLOW(message))
			else:
				self.write(message)

	def set_total(self, total: int) -> None:
		"""
		Set the total for the progressbar and reset progress to ``0``.

		:param total:
		"""

		self.total = total
		self.update(0)

	def set_description_str(  # noqa: D102
		self, desc: Optional[str] = None, refresh: Optional[bool] = True,
	) -> None:
		super().set_description_str(desc, refresh)  # type: ignore[misc]  # false positive


def should_show_colours(stream: Optional[IO] = None, colour: Optional[bool] = None) -> bool:
	"""
	Whether ANSI control characters should be stripped from the output (e.g. if writing to file).

	:param stream: File or ``sys.stdout`` etc. to write to.
	:param colour: Whether to display colours (:py:obj:`None` for autodetection).
	"""

	if colour is None:
		if stream is None:
			stream = sys.stdin

		try:
			return stream.isatty()
		except Exception:
			return False

	return colour
