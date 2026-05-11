from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


CommandBuilder = Callable[[Path, Path], list[str]]


@dataclass(frozen=True)
class FileActionInvocation:
    mode: str
    command: list[str] | None = None
    cwd: Path | None = None
    target_path: Path | None = None


@dataclass(frozen=True)
class FileActionDefinition:
    id: str
    label: str
    suffixes: tuple[str, ...]
    output_suffix: str | None = None
    command_builder: CommandBuilder | None = None
    destructive: bool = False
    icon: str | None = None
    button_variant: str = "ghost"
    confirm_message_template: str | None = None

    def applies_to(self, file_path: Path) -> bool:
        if not self.suffixes:
            return True
        return file_path.suffix.lower() in self.suffixes

    def build_output_path(self, source_path: Path) -> Path | None:
        if self.output_suffix is None:
            return None
        return source_path.with_suffix(self.output_suffix)

    def build_command(self, source_path: Path) -> list[str]:
        if self.command_builder is None:
            raise ValueError(f"Action {self.id} does not define a command builder.")
        output_path = self.build_output_path(source_path)
        if output_path is None:
            raise ValueError(f"Action {self.id} does not define an output path.")
        return self.command_builder(source_path, output_path)

    def build_invocation(self, source_path: Path) -> FileActionInvocation:
        output_path = self.build_output_path(source_path)
        if self.command_builder is not None:
            return FileActionInvocation(
                mode="launch",
                command=self.build_command(source_path),
                cwd=source_path.parent,
                target_path=output_path,
            )
        return FileActionInvocation(
            mode="delete",
            target_path=source_path,
        )

    def build_confirm_message(self, source_path: Path, base_dir: Path | None = None) -> str | None:
        if not self.confirm_message_template:
            return None

        relative_path = source_path.name
        if base_dir is not None:
            try:
                relative_path = source_path.relative_to(base_dir).as_posix()
            except ValueError:
                relative_path = source_path.name
        return self.confirm_message_template.format(relative_path=relative_path)

    def describe(self, source_path: Path, base_dir: Path | None = None) -> dict[str, str | bool]:
        output_path = self.build_output_path(source_path)
        target_relative_path = ""
        target_name = ""
        output_exists = False
        if output_path is not None:
            target_relative_path = output_path.name
            if base_dir is not None:
                try:
                    target_relative_path = output_path.relative_to(base_dir).as_posix()
                except ValueError:
                    target_relative_path = output_path.name
            target_name = output_path.name
            output_exists = output_path.exists()

        return {
            "id": self.id,
            "label": self.label,
            "target_relative_path": target_relative_path,
            "target_name": target_name,
            "output_exists": output_exists,
            "destructive": self.destructive,
            "icon": self.icon or "",
            "button_variant": self.button_variant,
            "confirm_message": self.build_confirm_message(source_path, base_dir) or "",
        }


def _openscad_stl_command(source_path: Path, output_path: Path) -> list[str]:
    return ["openscad", "-o", str(output_path), str(source_path)]


def _inkscape_pdf_command(source_path: Path, output_path: Path) -> list[str]:
    return ["inkscape", str(source_path), f"--export-filename={output_path}"]


FILE_ACTIONS: tuple[FileActionDefinition, ...] = (
    FileActionDefinition(
        id="generate-stl",
        label="Generate STL",
        suffixes=(".scad",),
        output_suffix=".stl",
        command_builder=_openscad_stl_command,
    ),
    FileActionDefinition(
        id="convert-pdf",
        label="Convert to PDF",
        suffixes=(".svg",),
        output_suffix=".pdf",
        command_builder=_inkscape_pdf_command,
    ),
    FileActionDefinition(
        id="delete-file",
        label="Delete",
        suffixes=(),
        destructive=True,
        icon="bin",
        button_variant="danger",
        confirm_message_template="Delete {relative_path}? This cannot be undone.",
    ),
)

_FILE_ACTIONS_BY_ID = {action.id: action for action in FILE_ACTIONS}


def get_file_action(action_id: str) -> FileActionDefinition | None:
    return _FILE_ACTIONS_BY_ID.get(action_id)


def iter_file_actions(file_path: Path) -> tuple[FileActionDefinition, ...]:
    file_path = Path(file_path)
    return tuple(action for action in FILE_ACTIONS if action.applies_to(file_path))


def describe_file_actions(file_path: Path, base_dir: Path | None = None) -> list[dict[str, str | bool]]:
    file_path = Path(file_path)
    return [action.describe(file_path, base_dir) for action in iter_file_actions(file_path)]