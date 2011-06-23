# Utility functions for configuration.

# Imports.

import os

# Function for finding the project root.

def get_project_root():
    project_root_paths = [ ".", "..", "/opt/linuxfoundation" ]
    for path in project_root_paths:
        if os.path.exists(os.path.join(path, "foss-barcode.py")) or \
                os.path.exists(os.path.join(path, "bin/foss-barcode.py")):
            return path

    # Shouldn't get here unless we can't find the path.
    raise RuntimeError, "could not find the project path"

# Return the proper directory to use for userdir mode.

def get_userdir():
    return os.path.join(os.environ["HOME"], ".fossbarcode")

# Should we use userdir mode?

def use_userdir():
    if os.getuid() == 0 or os.environ["LOGNAME"] == "compliance":
        return False
    
    project_root = get_project_root()
    if os.access(os.path.join(project_root, "fossbarcode"), os.W_OK):
        return False

    return True
