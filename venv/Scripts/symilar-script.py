#!D:\project\flask\venv\Scripts\python.exe
# EASY-INSTALL-ENTRY-SCRIPT: 'pylint==1.4.3','console_scripts','symilar'
__requires__ = 'pylint==1.4.3'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('pylint==1.4.3', 'console_scripts', 'symilar')()
    )
