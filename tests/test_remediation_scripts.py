import os
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "nt" and shutil.which("wsl"), "requires Windows Subsystem for Linux")
class TestRemediationScripts(unittest.TestCase):
    def test_posix_apply_and_restore_absent_file(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "remediate_posix_network.sh"
        drive, tail = os.path.splitdrive(script)
        script_wsl = f"/mnt/{drive[0].lower()}{str(tail).replace(chr(92), '/')}"
        test_home = subprocess.check_output(
            ["wsl", "--exec", "bash", "-c", "mktemp -d"], text=True, encoding="utf-8"
        ).strip()
        command = "set -euo pipefail;export HOME=$1;bash $2 --apply >/dev/null;backup=$(find $HOME/.anti-claude-check/backups -maxdepth 1 -type f -name \\*.absent -print -quit);test -n $backup;bash $2 --restore $backup >/dev/null;test ! -e $HOME/.anti-claude-check/claude-code-privacy.env"
        subprocess.run(
            ["wsl", "--exec", "bash", "-c", command, "_", test_home, script_wsl],
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
