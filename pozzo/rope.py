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
from typing import Callable, Generator, Iterable, Iterator, List, Literal, NamedTuple, Optional, Tuple

# 3rd party
import handy_archives
from consolekit.terminal_colours import Fore, Style
from domdf_python_tools.paths import PathPlus, TemporaryPathPlus
from domdf_python_tools.typing import PathLike

# this package
from pozzo.config import ExportTableDict, PozzoConfigDict
from pozzo.utils import ProgressBar, has_pathsep

__all__ = [
		"CommandResult",
		"Exporter",
		"ProcessOutput",
		"clone_project",
		"export",
		"export_project",
		"get_source_epoch",
		"import_resources",
		"join_args",
		"move_artifact",
		"zip_directory",
		]

T = typing.TypeVar('T')
U = typing.TypeVar('U')
V = typing.TypeVar('V')

stdout_indent = "    "


class ProcessOutput(typing.Generic[T, U, V]):
	"""
	Result of a subprocess.

	:param generator:
	"""

	return_code: Optional[V] = None
	"""
	The return or exit code of the process.

	Not set until :func:`~.stdout` is called.
	"""

	def __init__(self, generator: typing.Generator[T, U, V]):
		self._generator = generator
		super().__init__()

	def stdout(self) -> typing.Generator[T, U, None]:
		"""
		Returns an iterator over the process's stdout.
		"""

		yield from self

	def __iter__(self) -> typing.Generator[T, U, None]:
		self.return_code = yield from self._generator


_CommandRet = Tuple[List[PathLike], ProcessOutput[str, None, int]]


def clone_project(
		project_dir: PathPlus,
		target_dir: PathPlus,
		recursive: bool = False,
		) -> _CommandRet:
	"""
	Make a clone of a git repository.

	:param project_dir:
	:param target_dir:
	:param recursive:
	"""

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
		) -> _CommandRet:
	"""
	Call Godot to import resources.

	:param project_dir:
	:param godot: Path or command for the Godot executable.

	:returns: The command line arguments used, and the result of the process (stdout and return code).
	"""

	args: List[PathLike] = [godot, "--headless", "--import", "--verbose"]

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
		) -> _CommandRet:
	"""
	Call Godot to export a given preset.

	:param project_dir:
	:param preset:
	:param filename:
	:param output_dir:
	:param mode:
	:param godot: Path or command for the Godot executable.

	:returns: The command line arguments used, and the result of the process (stdout and return code).
	"""

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
	"""
	The result of calling a command with :meth:`~Exporter.run_command`.
	"""

	log: str
	succeeded: bool


def join_args(split_command: Iterable[PathLike]) -> str:
	"""
	Return a shell-escaped string from ``split_command``.

	:param split_command:
	"""

	return ' '.join(shlex.quote(os.fspath(arg)) for arg in split_command)


class Exporter:
	"""
	Clone and export Godot project repository.

	:param project_dir:
	:param output_dir:
	:param config:
	"""

	def __init__(self, project_dir: PathLike, output_dir: PathLike, config: PozzoConfigDict):
		self.project_dir = PathPlus(project_dir)
		self.output_dir = PathPlus(output_dir)
		self.config = config
		self.progbar = ProgressBar()

	def run_command(self, command: Callable[..., _CommandRet], *args, **kwargs) -> CommandResult:
		r"""
		Call a command, print the output, and check the return code.

		:param command:
		:param \*args: Positional arguments passed to ``command``.
		:param \*\*kwargs: Keyword arguments passed to ``command``.
		"""

		log = []

		command_args, process = command(*args, **kwargs)
		self.progbar.write(stdout_indent + Style.DIM('$' + join_args(command_args)))

		for line in process:
			log.append(line)
			self.progbar.write(stdout_indent + line, end='')

		return_code = process.return_code
		if return_code != 0:
			self.progbar.error(f"Process '{join_args(command_args)}' exited with code {return_code}")

		return CommandResult(
				''.join(log),
				return_code == 0,
				)

	def _clone(self, workdir: PathPlus) -> None:
		self.progbar.info("Cloning project into fresh directory.")

		clone_result = self.run_command(
				clone_project,
				self.project_dir,
				workdir,
				self.config["config"]["checkout_submodules"],
				)
		if not clone_result.succeeded:
			raise RuntimeError("Failed to clone repository.")

		self.progbar.update()

	def _import(self, workdir: PathPlus) -> None:
		self.progbar.info("Importing resources.")

		for _ in range(self.config["config"]["import_cycles"]):

			import_result = self.run_command(import_resources, workdir, self.config["config"]["godot"])
			if not import_result.succeeded:
				raise RuntimeError("Godot failed to import resources.")

			self.progbar.update()

	def _export(self, export_name: str, export_cfg: ExportTableDict, workdir: PathPlus) -> Iterator[PathPlus]:
		if export_cfg["preset_file"] != "export_presets.cfg":
			raise NotImplementedError

		with TemporaryPathPlus() as export_output_dir:
			export_result = self.run_command(
					export,
					workdir,
					export_cfg["preset"],
					export_cfg["filename"],
					export_output_dir,
					export_cfg["mode"],
					self.config["config"]["godot"],
					)

			assert not has_pathsep(export_name)

			if export_result.succeeded:
				if export_cfg["zip"]:

					self.progbar.write(stdout_indent + Style.BRIGHT("Creating ZIP archive."))
					with TemporaryPathPlus() as zip_outdir:

						zip_outfile = zip_outdir / f"{export_cfg['zip']}.zip"

						for arcname in zip_directory(export_output_dir, zip_outfile):
							self.progbar.write(stdout_indent * 2 + f"Writing {arcname.as_posix()}")

						self.progbar.write(
								stdout_indent
								+ Fore.GREEN(f"Zip archive created at {zip_outfile.resolve().as_posix()}"),
								)

						yield (move_artifact(zip_outfile, self.output_dir))
				else:
					for artifact in export_output_dir.iterdir():
						yield (move_artifact(artifact, self.output_dir))

		log_filename = (self.output_dir / f"{export_name}.log")
		log_filename.write_clean(export_result.log)
		yield (log_filename)

		self.progbar.update()

	def export_all(self) -> List[PathPlus]:
		"""
		Clone, import resources and export all artifacts.
		"""

		return self.export(*self.config["exports"])

	def export(self, *export_names: str) -> List[PathPlus]:
		r"""
		Clone, import resources and export artifacts.

		:param \*export_names: The names of export configurations in ``config.toml``.
		"""

		for name in export_names:
			if name not in self.config["exports"]:
				raise ValueError(f"No such export configuration {name!r}")

		self.output_dir.maybe_make(parents=True)
		artifacts = []

		self.progbar.set_total(1 + self.config["config"]["import_cycles"] + len(export_names))
		with TemporaryPathPlus() as workdir:

			self._clone(workdir)

			self.progbar.write('')
			self._import(workdir)

			#

			for export_name, export_cfg in self.config["exports"].items():
				if export_name not in export_names:
					continue

				self.progbar.write('')
				self.progbar.info(f"Exporting {export_name!r}.")

				for artifact in self._export(export_name, export_cfg, workdir):
					artifacts.append(artifact)

		return artifacts


def export_project(project_dir: PathLike, output_dir: PathLike, config: PozzoConfigDict) -> List[PathPlus]:
	"""
	Export the given project.

	:param project_dir:
	:param output_dir:
	:param config:
	"""

	exporter = Exporter(project_dir, output_dir, config)
	return exporter.export_all()


def move_artifact(artifact: PathPlus, output_dir: PathPlus) -> PathPlus:
	"""
	Move the given artifact into the output directory.

	:param artifact:
	:param output_dir:
	"""

	output_dir.maybe_make(parents=True)
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


def zip_directory(directory: PathPlus, out_file: PathPlus) -> Iterator[PathPlus]:
	"""
	Compress all files in the given directory.

	:param directory:
	:param out_file:
	"""

	mtime = get_source_epoch()
	files = list(directory.iterchildren())

	# Perhaps LZMA support in the future
	with handy_archives.ZipFile(out_file, mode='w', compression=zipfile.ZIP_DEFLATED) as wheel_archive:
		for file in files:
			arcname = file.relative_to(directory)
			wheel_archive.write_file(file, arcname=arcname, mtime=mtime)

			yield arcname
