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
import datetime
import os
import shlex
import shutil
import subprocess
import sys
import typing
import zipfile
from typing import Callable, Generator, Iterable, List, Literal, NamedTuple, Optional, Tuple

# 3rd party
import handy_archives
from consolekit.terminal_colours import Fore, Style
from domdf_python_tools.paths import PathPlus, TemporaryPathPlus
from domdf_python_tools.typing import PathLike
from domdf_python_tools.utils import stderr_writer

# this package
from pozzo.config import PozzoConfigDict
from pozzo.utils import has_pathsep

__all__ = [
		"CommandResult",
		"ProcessOutput",
		"clone_project",
		"export",
		"export_project",
		"import_resources",
		"join_args",
		"run_command",
		]

T = typing.TypeVar('T')
U = typing.TypeVar('U')
V = typing.TypeVar('V')

stdout_indent = "    "


class ProcessOutput(typing.Generic[T, U, V]):
	return_code: Optional[V] = None

	def __init__(self, generator: typing.Generator[T, U, V]):
		self._generator = generator
		super().__init__()

	def stdout(self) -> typing.Generator[T, U, None]:
		yield from self

	def __iter__(self) -> typing.Generator[T, U, None]:
		self.return_code = yield from self._generator


def clone_project(
		project_dir: PathPlus,
		target_dir: PathPlus,
		recursive: bool = False,
		) -> Tuple[List[PathLike], ProcessOutput[str, None, int]]:
	args: List[PathLike] = ["git", "clone"]

	if recursive:
		args.append("--recursive")

	args.extend((project_dir.abspath(), target_dir.abspath()))

	def clone() -> Generator[str, None, int]:
		process = subprocess.Popen(
				args=args,
				bufsize=1,
				executable=shutil.which("git"),
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				universal_newlines=True,
				)

		assert process.stdout is not None
		yield from process.stdout

		process.stdout.close()
		return process.wait()

	return args, ProcessOutput(clone())


def import_resources(
		project_dir: PathPlus,
		godot: str = "godot",
		) -> Tuple[List[str], ProcessOutput[str, None, int]]:
	args = [godot, "--headless", "--import", "--verbose"]

	def _import() -> Generator[str, None, int]:
		process = subprocess.Popen(
				args=args,
				bufsize=1,
				executable=godot,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				universal_newlines=True,
				cwd=project_dir.abspath(),
				)

		assert process.stdout is not None
		yield from process.stdout

		process.stdout.close()
		return process.wait()

	return args, ProcessOutput(_import())


def export(
		project_dir: PathPlus,
		preset: str,
		filename: str,
		output_dir: PathPlus,
		mode: Literal["release", "debug", "pack", "patch"] = "release",
		godot: str = "godot",
		) -> Tuple[List[PathLike], ProcessOutput[str, None, int]]:

	if ".." in filename:
		raise ValueError("Relative filenames are not permitted")

	filename_p = PathPlus(filename)
	if filename_p.is_absolute():
		raise ValueError("Filename may not be absolute")

	args: List[PathLike] = [godot, "--headless"]

	if mode == "release":
		args.append("--export-release")
	elif mode == "debug":
		args.append("--export-debug")
	elif mode == "pack":
		args.append("--export-pack")
	elif mode == "patch":
		args.append("--export-patch")
	else:
		raise ValueError(f"Unknown export mode {mode!r}")

	args.append("--verbose")
	args.extend((shlex.quote(preset), output_dir.absolute() / filename_p.name))

	def _import() -> Generator[str, None, int]:
		process = subprocess.Popen(
				args=args,
				bufsize=1,
				executable=godot,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				universal_newlines=True,
				cwd=project_dir.abspath(),
				)

		assert process.stdout is not None
		yield from process.stdout

		process.stdout.close()
		return process.wait()

	return args, ProcessOutput(_import())


class CommandResult(NamedTuple):
	log: str
	succeeded: bool


def join_args(split_command: Iterable[PathLike]) -> str:
	"""
	Return a shell-escaped string from ``split_command``.

	:param split_command:
	"""

	return ' '.join(shlex.quote(os.fspath(arg)) for arg in split_command)


def run_command(command: Callable, *args, **kwargs) -> CommandResult:
	log = []

	command_args, process = command(*args, **kwargs)
	print(stdout_indent, Style.DIM('$' + join_args(command_args)))

	for line in process:
		log.append(line)
		print(stdout_indent, line, end='')

	return_code = process.return_code
	if return_code != 0:
		stderr_writer(Fore.RED(f"Process '{join_args(command_args)}' exited with code {return_code}"))

	return CommandResult(
			''.join(log),
			return_code == 0,
			)


def export_project(project_dir: PathPlus, output_dir: PathPlus, config: PozzoConfigDict) -> List[PathPlus]:
	output_dir.maybe_make(parents=True)
	artifacts = []

	with TemporaryPathPlus() as workdir:

		print(Style.BRIGHT("Cloning project into fresh directory."))

		clone_result = run_command(clone_project, project_dir, workdir, config["config"]["checkout_submodules"])
		if not clone_result.succeeded:
			raise RuntimeError("Failed to clone repository.")

		#

		print()
		print(Style.BRIGHT("Importing resources."))

		for _ in range(config["config"]["import_cycles"]):

			import_result = run_command(import_resources, workdir, config["config"]["godot"])
			if not import_result.succeeded:
				raise RuntimeError("Godot failed to import resources.")

		#

		for export_name, export_cfg in config["exports"].items():

			print()
			print(Style.BRIGHT(f"Exporting {export_name!r}."))

			if export_cfg["preset_file"] != "export_presets.cfg":
				raise NotImplementedError

			with TemporaryPathPlus() as export_output_dir:
				export_result = run_command(
						export,
						workdir,
						export_cfg["preset"],
						export_cfg["filename"],
						export_output_dir,
						export_cfg["mode"],
						config["config"]["godot"],
						)

				assert not has_pathsep(export_name)

				if export_result.succeeded:
					if export_cfg["zip"]:

						print(stdout_indent, Style.BRIGHT("Creating ZIP archive."))
						with TemporaryPathPlus() as zip_outdir:
							zip_outfile = zip_outdir / f"{export_cfg['zip']}.zip"
							zip_directory(export_output_dir, zip_outfile)
							artifacts.append(move_artifact(zip_outfile, output_dir))
					else:
						for artifact in export_output_dir.iterdir():
							artifacts.append(move_artifact(artifact, output_dir))

				log_filename = (output_dir / f"{export_name}.log")
				log_filename.write_clean(export_result.log)
				artifacts.append(log_filename)

	return artifacts


def move_artifact(artifact: PathPlus, output_dir: PathPlus) -> PathPlus:
	dst = output_dir / artifact.name
	return artifact.move(dst)


def get_source_epoch() -> Optional[datetime.datetime]:
	"""
	Returns the parsed value of the :envvar:`SOURCE_DATE_EPOCH` environment variable, or :py:obj:`None` if unset.

	See https://reproducible-builds.org/specs/source-date-epoch/ for the specification.

	:raises ValueError: if the value is in an invalid format.
	"""

	# If SOURCE_DATE_EPOCH is set (e.g. by Debian), it's used for timestamps inside the wheel.
	epoch: Optional[str] = os.environ.get("SOURCE_DATE_EPOCH")
	if epoch is None:
		return None
	elif epoch.isdigit() and sys.version_info >= (3, 11):
		return datetime.datetime.fromtimestamp(int(epoch), datetime.UTC)  # type: ignore[attr-defined]
	elif epoch.isdigit():
		return datetime.datetime.utcfromtimestamp(int(epoch))
	else:
		raise ValueError(f"'SOURCE_DATE_EPOCH' must be an integer with no fractional component, not {epoch!r}")


def zip_directory(directory: PathPlus, out_file: PathPlus) -> List[PathPlus]:

	mtime = get_source_epoch()
	files = list(directory.iterchildren())

	# Perhaps LZMA support in the future
	with handy_archives.ZipFile(out_file, mode='w', compression=zipfile.ZIP_DEFLATED) as wheel_archive:
		for file in files:
			wheel_archive.write_file(
					file,
					arcname=file.relative_to(directory),
					mtime=mtime,
					)

			# TODO: iterator
			print(stdout_indent * 2, f"Writing {file.relative_to(directory).as_posix()}")

	print(stdout_indent * 2, Fore.GREEN(f"Zip archive created at {out_file.resolve().as_posix()}"))

	return files
