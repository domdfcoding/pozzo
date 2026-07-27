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

# 3rd party
import tqdm
from consolekit.terminal_colours import Fore, Style

__all__ = ["ProgressBar", "has_pathsep"]


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

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._error_count = 0
		self._warning_count = 0

	def info(self, message: str) -> None:
		"""
		Print the given information message, in bright/bold text.

		:param message:
		"""

		self.write(Style.BRIGHT(message))

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
