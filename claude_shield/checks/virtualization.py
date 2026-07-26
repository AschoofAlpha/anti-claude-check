from .wsl import check_wsl
from .docker import check_docker

def run_virtualization_checks():
    return [
        check_wsl(),
        check_docker()
    ]
