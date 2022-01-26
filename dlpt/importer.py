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
    def __init__(self, fPath: str, baseFolderPath: Optional[str] = None):
        """
        Dynamically import module from given `fPath`.

        Args:
            fPath: abs path to a python module (file) which will be
                dynamically imported.
            baseFolderPath: path to a root folder from where module
                will be imported. Example:
                ``fPath = C:/root/someFolder/someSubfolder/myModule.py``
                ``baseFolderPath = C:/root/someFolder/``
                -> module will be imported as: `someSubfolder.myModule`

        NOTE:
            `baseFolderPath` (or `fPath` root folder, if `baseFolderPath`
            is not specified) is added to `sys.path`. It is NOT removed once
            object is garbage-collected.
        """
        self.fPath = os.path.normpath(fPath)
        dlpt.pth.check(self.fPath)
        if not os.path.isabs(self.fPath):
            errorMsg = f"Given `fPath` is not an ABSOLUTE file path: "
            errorMsg += self.fPath
            raise ValueError(errorMsg)
        if not os.path.isfile(self.fPath):
            errorMsg = f"Given `fPath` is not a FILE path: {self.fPath}"
            raise ValueError(errorMsg)

        if baseFolderPath is None:
            self.baseFolderPath = os.path.dirname(self.fPath)
        else:
            self.baseFolderPath = os.path.normpath(baseFolderPath)
            dlpt.pth.check(self.baseFolderPath)

        if self.baseFolderPath not in self.fPath:
            errorMsg = f"Given `fPath` is not inside `baseFolderPath`:"
            errorMsg += f"\n\tfilePath: {self.fPath}"
            errorMsg += f"\n\tbaseFolderPath: {self.baseFolderPath}"
            raise ValueError(errorMsg)

        self._module: Optional[ModuleType] = None

        self._import()

    def _import(self) -> ModuleType:
        """
        Import module and return module instance object.

        Returns:
            Imported module instance (object).
        """

        # add base folder to sys.path because of
        # possible other imports inside module, pickling, ...
        for path in sys.path:
            if os.path.normpath(path).lower() == self.baseFolderPath.lower():
                break
        else:
            sys.path.append(self.baseFolderPath)

        ext = dlpt.pth.get_ext(self.fPath)
        relPath = os.path.relpath(self.fPath, self.baseFolderPath)
        importName = relPath.replace(ext, "").replace(os.path.sep, ".")

        if importName in sys.modules:
            # module already imported.
            # Let's just reload it and return its instance
            self._module = importlib.reload(sys.modules[importName])
        else:
            self._module = importlib.import_module(importName)
        if self._module is None:  # pragma: no cover
            errorMsg = f"Unable to import module from: {self.fPath}"
            errorMsg += f"\n\tInvalid syntax, invalid imports, ...?"
            raise Exception(errorMsg)

        return self._module

    def get_module(self) -> ModuleType:
        """
        Return imported module object.

        Returns:
            Imported module instance (object).
        """
        assert self._module is not None

        return self._module

    def has_object(self, name: str, raiseException: bool = True) -> bool:
        """
        Check if imported module has object with objectName.

        Args:
            name: name of the object to check in imported module
            raiseException: if True, exception is raised if object is not
                found. Otherwise bool is returned (True if object is found,
                False otherwise).

        Returns:
            True if imported module has object with `name`, False
            otherwise.
        """
        if self._module:
            if hasattr(self._module, name):
                return True

        if raiseException:
            errorMsg = f"Imported module has no object with name '{name}'."
            raise Exception(errorMsg)
        else:
            return False
