
from benchkit.helpers.linux.predictable.predlinux import PredLinux
from benchkit.platforms import get_current_platform


def main():
    platform = get_current_platform()
    pred = PredLinux(platform=platform)

    pred.predverifydo(
        change_frequency=False,
        expected_nb_isolated_cpus=0,
        bypass_isolation_check=True,
    )

    pred.preddo(
        frequency_to_set=None,
        expected_nb_isolated_cpus=0,
        bypass_isolation_check=True,
    )


if __name__ == '__main__':
    main()
