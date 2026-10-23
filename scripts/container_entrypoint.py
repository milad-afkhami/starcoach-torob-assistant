"""Prepare only the mounted state directory, then irreversibly run as the app UID."""

import ctypes
import os
import stat
import sys
from pathlib import Path

STATE_DIR = Path("/data")
APP_UID = APP_GID = 10001


def prepare_state():
    # Operate on the opened directory itself; never follow a link or walk its files.
    descriptor = os.open(STATE_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        mode = stat.S_IMODE(os.fstat(descriptor).st_mode)
        os.fchown(descriptor, APP_UID, APP_GID)
        os.fchmod(descriptor, mode | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    finally:
        os.close(descriptor)


def no_new_privileges():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # Linux PR_SET_NO_NEW_PRIVS, irreversible.
        raise OSError(ctypes.get_errno(), "Could not establish unprivileged execution")


def main(command):
    if not command:
        raise ValueError("Application command required")
    if os.geteuid() == 0:
        prepare_state()
        os.setgroups([])
        os.setresgid(APP_GID, APP_GID, APP_GID)
        os.setresuid(APP_UID, APP_UID, APP_UID)
    if os.getresuid() != (APP_UID, APP_UID, APP_UID) or os.getresgid() != (APP_GID, APP_GID, APP_GID):
        raise PermissionError("Unexpected application identity")
    no_new_privileges()
    os.execvp(command[0], command)


if __name__ == "__main__":
    main(sys.argv[1:])
