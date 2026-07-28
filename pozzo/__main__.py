#!/usr/bin/env python3
#
#  __main__.py
"""
Godot project export orchestrator (or rope tugger).
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
# 3rd party
import consolekit
from consolekit.options import auto_default_argument, auto_default_option, colour_option

if False:  # TYPE_CHECKING:  # pylint: disable=using-constant-test

	# 3rd party
	from consolekit.terminal_colours import ColourTrilean

__all__ = ["export", "main"]


@consolekit.click_group(
		cls=consolekit.SuggestionGroup,
		invoke_without_command=False,
		context_settings={**consolekit.CONTEXT_SETTINGS, "show_default": True},
		)
def main() -> None:
	"""
	Godot project export orchestrator (or rope tugger).
	"""


# TODO: option for which export configs (all by default)


@colour_option()
@auto_default_option("-q", "--quiet", help="Don't print logs, only the list of artifacts.", is_flag=True)
@auto_default_option("-o", "--output-dir", help="Directory to save artifacts in.")
@auto_default_option("-c", "--config-file", help="The TOML configuration file to use.")
@auto_default_argument("project")
@main.command()
def export(
		project: str = '.',
		config_file: str = "pozzo.toml",
		output_dir: str = "dist",
		quiet: bool = False,
		colour: "ColourTrilean" = None,
		) -> None:
	"""
	Export artifacts from a Godot project.
	"""

	# 3rd party
	from consolekit.terminal_colours import resolve_color_default
	from domdf_python_tools.paths import PathPlus

	# this package
	from pozzo.config import load
	from pozzo.rope import Exporter

	outdir = PathPlus(output_dir).abspath()
	config = load(config_file)
	exporter = Exporter(project, output_dir, config, colour=resolve_color_default(colour), quiet=quiet)
	artifacts = exporter.export_all()
	exporter.progbar.close()

	if not quiet:
		exporter.report_errors_warnings("Export complete.")
		print(f"Artifacts written to {outdir.abspath().relative_to(PathPlus.cwd()).as_posix()}:")

	for file in artifacts:
		assert file.exists()
		assert file.is_file()

		if quiet:
			print(file.as_posix())
		else:
			print(f"    {file.name}")


if __name__ == "__main__":
	main()
