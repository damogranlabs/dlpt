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


class ModuleImporter():
    def __init__(self, filePath: str, baseFolderPath: Optional[str] = None):
        """
        Dynamically import module from given filePath and return its instance.
            filePath: abs path to a python module (file) which will be 
                dynamically imported.
            baseFolderPath: path to a root folder from where module
                will be imported. Example:
                    `filePath = C:/root/someFolder/someSubfolder/myModule.py`
                    `baseFolderPath = C:/root/someFolder/`
                    -> module will be imported as: `someSubfolder.myModule`

        NOTE: baseFolderPath (or filePath root folder, if baseFolderPath
            is not specified) is added to sys.path. It is NOT removed once
            object is garbage-collected.
        """
        self.filePath = os.path.normpath(filePath)
        if baseFolderPath is None:
            self.baseFolderPath = os.path.dirname(self.filePath)
        else:
            self.baseFolderPath = os.path.normpath(baseFolderPath)
        self._module: Optional[ModuleType] = None

        # check
        dlpt.pth.check(self.filePath)
        dlpt.pth.check(self.baseFolderPath)
        if not os.path.isabs(self.filePath):
            errorMsg = f"Given filePath is not an ABSOLUTE file path: {self.filePath}"
            raise ValueError(errorMsg)
        if not os.path.isfile(self.filePath):
            errorMsg = f"Given filePath is not a FILE path: {self.filePath}"
            raise ValueError(errorMsg)

        self._import()

    def _import(self) -> ModuleType:
        """
        Import module and return module instance object.
        """
        relPath = os.path.relpath(self.filePath, self.baseFolderPath)
        if relPath.startswith("."):
            errorMsg = f"Given filePath is not inside baseFolderPath:"
            errorMsg += f"\n\tfilePath: {self.filePath}\n\tbaseFolderPath: {self.baseFolderPath}"
            raise ValueError(errorMsg)

        # add base folder to sys.path (possible other imports inside module, pickling, ...)
        for path in sys.path:
            if os.path.normpath(path).lower() == self.baseFolderPath.lower():
                self._baseFolderInSysPath = True
                break
        else:
            sys.path.append(self.baseFolderPath)

        ext = dlpt.pth.getExt(self.filePath)
        importName = relPath.replace(ext, "").replace(os.path.sep, ".")

        if importName in sys.modules:
            # module already imported. Let's just reload it and return its instance
            self._module = importlib.reload(sys.modules[importName])
        else:
            self._module = importlib.import_module(importName)
        if self._module is None:  # pragma: no cover
            errorMsg = f"Unable to import module from: {self.filePath}\n\tInvalid syntax?"
            raise Exception(errorMsg)

        return self._module

    def getModule(self) -> ModuleType:
        """
        Return imported module object.
        """
        assert self._module is not None

        return self._module

    def hasObject(self, objectName: str, raiseException: bool = True) -> bool:
        """
        Check if imported module has object with objectName.
            objectName: name of the object to check in imported module
            raiseException: if True, exception is raised if object is not
                found. Otherwise bool is returned (True if object is found,
                False otherwise).
        """
        if self._module:
            if hasattr(self._module, objectName):
                return True

        if raiseException:
            errorMsg = f"Imported module has no object with name '{objectName}'."
            raise Exception(errorMsg)
        else:
            return False
