from benchkit.devices.adb import AndroidDebugBridge, AndroidCommLayer
from benchkit.platforms import Platform
from benchkit.benchmark import Benchmark
from benchkit.campaign import CampaignCartesianProduct


class AppStartBench(Benchmark):
    def __init__(self, platform: Platform):
        super().__init__()
        self.platform = platform

    def single_run(self, app_name: str, **kwargs) -> str:
        self.platform.comm.shell(f"am force-stop {app_name}")
        return self.platform.comm.shell(f"am start -W {app_name}")

    def parse_output_to_results(self, command_output: str, **kwargs) -> dict:
        lines = [line.strip() for line in command_output.splitlines()]
        key_values = [line.rsplit(":", maxsplit=1) for line in lines if ":" in line]
        results = {e[0].strip(): e[1].strip() for e in key_values}
        return results

    def get_run_var_names(self) -> list[str]:
        return ["app_name"]


def main():
    device = list(AndroidDebugBridge.query_devices())[0]
    with AndroidDebugBridge.from_device(device) as adb:
        phone = Platform(comm_layer=AndroidCommLayer(adb))
        bench = AppStartBench(platform=phone)
        campaign = CampaignCartesianProduct(
            name="appstart",
            benchmark=bench,
            nb_runs=15,
            variables={
                "app_name": [
                    "com.google.android.calculator",
                    "com.google.android.youtube",
                    "com.spotify.music",
                ],
            },
        )
        campaign.run()
        campaign.generate_graph(
            plot_name="stripplot",
            title="App start time",
            y="app_name",
            hue="app_name",
            x="TotalTime",
        )


if __name__ == "__main__":
    main()
