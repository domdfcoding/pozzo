#!/usr/bin/env python3
#
#  config.py
"""
Parse TOML config.
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
from typing import Any, Callable, ClassVar, Dict, List, Optional, Union, cast

# 3rd party
from dom_toml.parser import TOML_TYPES, AbstractConfigParser, BadConfigError, construct_path
from domdf_python_tools.utils import strtobool
from typing_extensions import NotRequired, Required, TypedDict

# this package
from pozzo.utils import has_pathsep

__all__ = [
		"ConfigTableDict",
		"ConfigTableParser",
		"ExportTableDict",
		"ExportTableParser",
		"PozzoConfigDict",
		"PozzoConfigParser",
		]


class ConfigTableDict(TypedDict):
	"""
	:class:`typing.TypedDict` representing the output from the :class:`~.ConfigTableParser` class.
	"""

	godot: Required[str]
	import_cycles: Required[int]
	checkout_submodules: Required[bool]


class ExportTableDict(TypedDict):
	"""
	:class:`typing.TypedDict` representing the output from the :class:`~.ExportTableParser` class.
	"""

	preset_file: NotRequired[str]
	preset: Required[str]
	filename: Required[str]
	mode: NotRequired[str]
	zip: NotRequired[Union[str, None]]
	extends: NotRequired[str]


class PozzoConfigDict(TypedDict):
	"""
	:class:`typing.TypedDict` representing the output from the :class:`~.PozzoConfigParser` class.
	"""

	config: Required[ConfigTableDict]
	exports: Required[Dict[str, ExportTableDict]]  # todo: kt


class ConfigTableParser(AbstractConfigParser[ConfigTableDict]):
	"""
	Parser for the ``config`` table in ``pozzo.toml``.
	"""

	table_name: ClassVar[str] = "config"
	required_keys: ClassVar[List[str]] = []
	keys: ClassVar[List[str]] = ["godot", "import_cycles", "checkout_submodules"]
	defaults: ClassVar[Dict[str, Any]] = {"godot": "godot", "import_cycles": 1, "checkout_submodules": False}

	def parse_godot(self, config: Dict[str, TOML_TYPES]) -> str:
		"""
		Parse the ``godot`` key.

		:param config: The unparsed TOML config for the ``config`` table in ``pozzo.toml``.
		"""

		key_name = "godot"
		key_path = [self.table_name, key_name]
		value = config[key_name]
		self.assert_type(value, str, key_path)
		return value

	def parse_import_cycles(self, config: Dict[str, TOML_TYPES]) -> int:
		"""
		Parse the ``import_cycles`` key.

		:param config: The unparsed TOML config for the ``config`` table in ``pozzo.toml``.
		"""

		key_name = "import_cycles"
		key_path = [self.table_name, key_name]
		value = config[key_name]
		self.assert_type(value, (str, int), key_path)

		if isinstance(value, str) and not value.isdigit():
			name = construct_path(key_path)
			raise TypeError(f"Invalid type for {name!r}: expected {int!r}, got {type(str)!r}")

		return int(value)

	def parse_checkout_submodules(self, config: Dict[str, TOML_TYPES]) -> bool:
		"""
		Parse the ``checkout_submodules`` key.

		:param config: The unparsed TOML config for the ``config`` table in ``pozzo.toml``.
		"""

		key_name = "checkout_submodules"
		key_path = [self.table_name, key_name]
		value = config[key_name]
		self.assert_type(value, (str, int, bool), key_path)

		if not isinstance(value, bool):
			value = strtobool(value)

		return value

	def parse(
			self,
			config: Dict[str, TOML_TYPES],
			set_defaults: bool = True,
			) -> ConfigTableDict:
		"""
		Parse the TOML configuration.

		:param config:
		:param set_defaults: If :py:obj:`True`, the values in
			:attr:`self.defaults <dom_toml.parser.AbstractConfigParser.defaults>` and
			:attr:`self.factories <dom_toml.parser.AbstractConfigParser.factories>`
			will be set as defaults for the returned mapping.
		"""

		parsed_config = super().parse(config, set_defaults)
		return parsed_config

	@classmethod
	def default(cls) -> ConfigTableDict:
		"""
		Return the default table values.
		"""

		return cls().parse({}, set_defaults=True)


class ExportTableParser(AbstractConfigParser[ExportTableDict]):
	"""
	Parser for a child of the ``exports`` table in ``pozzo.toml``.

	:param export_name:
	"""

	table_name: ClassVar[str] = "exports"
	export_name: str
	required_keys: ClassVar[List[str]] = ["preset", "filename"]
	keys: ClassVar[List[str]] = [
			"preset_file",
			"preset",
			"filename",
			"mode",
			"zip",
			"extends",
			]
	defaults: ClassVar[Dict[str, Any]] = {
			"preset_file": "export_presets.cfg",
			"mode": "release",
			"zip": None,
			"extends": None,
			}

	def __init__(self, export_name: str):
		super().__init__()
		self.export_name = export_name

	def parse_preset_file(self, config: Dict[str, TOML_TYPES]) -> str:
		"""
		Parse the ``preset_file`` key.

		:param config: The unparsed TOML config for a child of the ``exports`` table in ``pozzo.toml``.
		"""

		return self.string_value_parser("preset_file", config)

	def parse_preset(self, config: Dict[str, TOML_TYPES]) -> str:
		"""
		Parse the ``preset`` key.

		:param config: The unparsed TOML config for a child of the ``exports`` table in ``pozzo.toml``.
		"""

		return self.string_value_parser("preset", config)

	def parse_filename(self, config: Dict[str, TOML_TYPES]) -> str:
		"""
		Parse the ``filename`` key.

		:param config: The unparsed TOML config for a child of the ``exports`` table in ``pozzo.toml``.
		"""

		return self.string_value_parser("filename", config)

	def parse_mode(self, config: Dict[str, TOML_TYPES]) -> str:
		"""
		Parse the ``mode`` key.

		:param config: The unparsed TOML config for a child of the ``exports`` table in ``pozzo.toml``.
		"""

		return self.string_value_parser("mode", config)

	def string_value_parser(self, key_name: str, config: Dict[str, TOML_TYPES]) -> str:
		"""
		Parse a string value.

		:param key_name:
		:param config: The unparsed TOML config for a child of the ``exports`` table in ``pozzo.toml``.
		"""

		key_path = [self.table_name, self.export_name, key_name]
		value = config[key_name]
		self.assert_type(value, str, key_path)
		return value

	def parse_zip(self, config: Dict[str, TOML_TYPES]) -> Optional[str]:
		"""
		Parse the ``zip`` key.

		:param config: The unparsed TOML config for the ``config`` table in ``pozzo.toml``.
		"""

		key_name = "zip"
		key_path = [self.table_name, self.export_name, key_name]
		value = config[key_name]

		if value is None:
			return None

		self.assert_type(value, str, key_path)
		return value

	def parse(
			self,
			config: Dict[str, TOML_TYPES],
			set_defaults: bool = False,
			) -> ExportTableDict:
		"""
		Parse the TOML configuration.

		:param config:
		:param set_defaults: If :py:obj:`True`, the values in
			:attr:`self.defaults <dom_toml.parser.AbstractConfigParser.defaults>` and
			:attr:`self.factories <dom_toml.parser.AbstractConfigParser.factories>`
			will be set as defaults for the returned mapping.
		"""

		if set_defaults:
			for key in self.required_keys:
				if key not in config:
					if (key in self.defaults or key in self.factories):
						continue  # pragma: no cover https://github.com/nedbat/coveragepy/issues/198
					else:
						raise BadConfigError(
								f"The {construct_path([self.table_name, self.export_name, key])!r} field must be provided.",
								)

		parsed_config = super().parse(config, set_defaults)
		return parsed_config


class PozzoConfigParser(AbstractConfigParser[PozzoConfigDict]):
	"""
	Parser for ``pozzo.toml``.
	"""

	required_keys: ClassVar[List[str]] = []
	keys: ClassVar[List[str]] = ["config", "exports"]
	factories: ClassVar[Dict[str, Callable[..., Any]]] = {"config": ConfigTableParser.default, "exports": dict}

	def parse_config(self, config: Dict[str, TOML_TYPES]) -> ConfigTableDict:
		"""
		Parse the ``config`` key.

		:param config: The unparsed TOML config from the ``pozzo.toml`` file.
		"""

		key_name = "config"
		key_path = [key_name]
		value = config[key_name]
		self.assert_type(value, dict, key_path)

		return ConfigTableParser().parse(value)

	def parse_exports(self, config: Dict[str, TOML_TYPES]) -> Dict[str, ExportTableDict]:
		"""
		Parse the ``exports`` key.

		:param config: The unparsed TOML config from the ``pozzo.toml`` file.
		"""

		key_name = "exports"
		key_path = [key_name]
		value = config[key_name]
		self.assert_type(value, dict, key_path)

		assert isinstance(value, dict)

		exports: Dict[str, ExportTableDict] = {}

		for export_name, export_table in value.items():
			if has_pathsep(export_name):
				raise ValueError(f"Export name {export_name!r} may not contain path separators")

			key_path = [key_name, export_name]
			self.assert_type(export_table, dict, key_path)
			assert isinstance(export_table, dict)
			extends = export_table.get("extends", None)
			derived = isinstance(extends, str)
			exports[export_name] = ExportTableParser(export_name).parse(
					export_table,
					set_defaults=not derived,
					)

		for export_name, export_config in exports.items():
			extends = export_config.get("extends", None)
			if extends:
				if extends in exports:
					exports[export_name] = cast(
							ExportTableDict,
							dict([*exports[extends].items(), *export_config.items()]),
							)
				else:
					raise ValueError(f"Export {export_name!r} extends nonexistent export {extends!r}")

		return exports

	def parse(
			self,
			config: Dict[str, TOML_TYPES],
			set_defaults: bool = True,
			) -> PozzoConfigDict:
		"""
		Parse the TOML configuration.

		:param config:
		:param set_defaults: If :py:obj:`True`, the values in
			:attr:`self.defaults <dom_toml.parser.AbstractConfigParser.defaults>` and
			:attr:`self.factories <dom_toml.parser.AbstractConfigParser.factories>`
			will be set as defaults for the returned mapping.
		"""

		parsed_config = super().parse(config, set_defaults)
		return parsed_config

	@classmethod
	def default(cls) -> PozzoConfigDict:
		"""
		Return the default table values.
		"""

		return cls().parse({}, set_defaults=True)
