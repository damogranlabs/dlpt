"""
Dynamically import python module in the runtime.
"""
import importlib
import importlib.machinery
import importlib.util
import os
import sys
from types import ModuleType
from typing import Optional

import dlpt


class ModuleImporter:
    def __init__(self, file_path: str, base_dir_path: Optional[str] = None):
        """
        Dynamically import module from given ``file_path``.

        Args:
            file_path: abs path to a python module (file) which will be
                dynamically imported.
            base_dir_path: path to a root directory from where module
                will be imported. Example:
                ``file_path = C:/root/someDir/someSubdir/myModule.py``
                ``base_dir_path = C:/root/someDir/``
                -> module will be imported as: `someSubdir.myModule`

        NOTE:
            ``base_dir_path`` (or ``file_path`` root directory, if ``base_dir_path``
            is not specified) is added to `sys.path`. It is NOT removed once
            object is garbage-collected.
        """
        self.file_path = os.path.normpath(file_path)
        dlpt.pth.check(self.file_path)
        if not os.path.isabs(self.file_path):
            err_msg = f"Given `file_path` is not an ABSOLUTE file path: "
            err_msg += self.file_path
            raise ValueError(err_msg)
        if not os.path.isfile(self.file_path):
            err_msg = f"Given `file_path` is not a FILE path: {self.file_path}"
            raise ValueError(err_msg)

        if base_dir_path is None:
            self.base_dir_path = os.path.dirname(self.file_path)
        else:
            self.base_dir_path = os.path.normpath(base_dir_path)
            dlpt.pth.check(self.base_dir_path)

        if self.base_dir_path not in self.file_path:
            err_msg = f"Given `file_path` is not inside `base_dir_path`:"
            err_msg += f"\n\t`filePath`: {self.file_path}"
            err_msg += f"\n\t`base_dir_path`: {self.base_dir_path}"
            raise ValueError(err_msg)

        self._module: Optional[ModuleType] = None

        self._import()

    def _import(self) -> ModuleType:
        """
        Import module and return module instance object.

        Returns:
            Imported module instance (object).
        """

        # add base directory to sys.path because of
        # possible other imports inside module, pickling, ...
        for path in sys.path:
            if os.path.normpath(path).lower() == self.base_dir_path.lower():
                break
        else:
            sys.path.append(self.base_dir_path)

        ext = dlpt.pth.get_ext(self.file_path)
        rel_path = os.path.relpath(self.file_path, self.base_dir_path)
        import_name = rel_path.replace(ext, "").replace(os.path.sep, ".")

        if import_name in sys.modules:
            # module already imported.
            # Let's just reload it and return its instance
            self._module = importlib.reload(sys.modules[import_name])
        else:
            self._module = importlib.import_module(import_name)
        if self._module is None:  # pragma: no cover
            err_msg = f"Unable to import module from: {self.file_path}"
            err_msg += f"\n\tInvalid syntax, invalid imports, ...?"
            raise Exception(err_msg)

        return self._module

    def get_module(self) -> ModuleType:
        """
        Return imported module object.

        Returns:
            Imported module instance (object).
        """
        assert self._module is not None

        return self._module

    def has_object(self, name: str, raise_exception: bool = True) -> bool:
        """
        Check if imported module has object with objectName.

        Args:
            name: name of the object to check in imported module
            raise_exception: if True, exception is raised if object is not
                found. Otherwise bool is returned (True if object is found,
                False otherwise).

        Returns:
            True if imported module has object with `name`, False
            otherwise.
        """
        if self._module:
            if hasattr(self._module, name):
                return True

        if raise_exception:
            err_msg = f"Imported module has no object with name '{name}'."
            raise Exception(err_msg)
        else:
            return False
