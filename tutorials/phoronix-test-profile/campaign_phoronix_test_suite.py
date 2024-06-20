from phoronix import phoronix_test_profile_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir

def main() -> None:
    # We benchmark the draco library
    test_profile_src_dir = (get_curdir(__file__) / "test-profiles/pts/draco-1.6.1").resolve()

    # Create a campaign for the test profile
    campaign = phoronix_test_profile_campaign(
        test_profile_src_dir=test_profile_src_dir,
        nb_runs=1,
        benchmark_duration_seconds=3,
        
        # These arguments will be passed to the benchmark as specified in the test profile
        model=["church.ply", "lion.ply"]
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
