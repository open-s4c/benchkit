"""Contains classes for parsing Phoronix test profiles."""

import pathlib
from typing import Iterable, Optional
from benchkit.utils.types import PathType
import xml.etree.ElementTree as ET
import urllib.request
from hashlib import sha256

# Some utility procedures for converting from Phoronix' XML format

def find(element: ET.Element, name: str):
    """Finds an XML element by its name and returns its contents."""
    return element.find(name).text


def find_optional(element: ET.Element, name: str):
    """
    Finds an optional XML element by its name. Returns its contents
    if its exists, otherwise returns None.
    """
    item = element.find(name)
    if item is not None:
        return item.text
    return None

def find_optional_array_str(element: ET.Element, name: str, seperator=", "):
    """
    Finds an optional XML element by its names. Returns its contents split
    by the given seperator if it exists, otherwise returns None.
    """
    item = element.find(name)
    if item is not None:
        return item.text.split(seperator)
    return None

def convert_to_bool(value: str):
    """Converts a string value provided by Phoronix to a boolean."""
    if value is None:
        return None
    else: return value == "TRUE"
    
def file_if_exists(path: PathType, name: str):
    """Returns a Phatlib Path if the file in the path with the given name exists, otherwise returns None."""
    full_path = pathlib.Path(path / name)
    if full_path.exists():
        return full_path
    else:
        return None


class PhoronixDownload:
    """Represents a Phoronix package download."""
    
    def __init__(
        self,
        urls: Iterable[str],
        md5: Optional[str],
        sha256: Optional[str],
        file_name: Optional[str],
        file_size: int
    ):
        self.urls = urls
        self.md5 = md5
        self.sha256 = sha256
        self.file_name = file_name
        self.file_size = file_size

    @staticmethod
    def from_xml(element: ET.Element):
        return PhoronixDownload(
            urls=element.find("URL").text.split(", "),
            md5=find_optional(element, "MD5"),
            sha256=find_optional(element, "SHA256"),
            file_name=find_optional(element, "FileName"),
            file_size=int(element.find("FileSize").text)
        )
    
    def _validate_data(self, data):
        """Attempts to validate if the data is authentic."""
        
        try:
            # Check the file size and the SHA256 hash if it is specified
            if len(data) == self.file_size and (self.sha256 is None or sha256(data).hexdigest() == self.sha256):
                return True
            else:
                return False
        except Exception:
            return False    
        
    
    def exists(self, src_path: PathType) -> bool:
        """Checks if the download already exists on the system."""
        
        try:
            # Try to read the file and validate it
            with open(src_path / self.file_name, "rb") as file:
                data = file.read()
                return self._validate_data(data)
        except Exception:
            return False
        
    def download(self, src_path: PathType):
        """Downloads the package."""
        
        # we try each url until one succeeds
        for url in self.urls:
            try:
                file_name = self.file_name 
                if file_name is None:
                    # if the file name wasn't manually specified
                    file_name = url.split("/")[-1]
                with urllib.request.urlopen(url) as response, open(src_path / file_name, "wb") as file:
                    data = response.read()
                    
                    # validate the data before writing it to a file
                    if self._validate_data(data):
                        file.write(data)
                        return
                    else:
                        raise Exception("Downloaded file cannot be validated.")
            except Exception as e:
                print(e)
                print("Failed to write file from", url, "to a file.")

    def ensure_exists(self, src_path: PathType):
        """Ensures the download exists on the system. Only downloads the file if it does not exist yet."""
        
        if not self.exists(src_path):
            self.download(src_path)


class PhoronixDownloads:
    """Represents a set of files that should be downloaded."""
    
    def __init__(self, downloads: Iterable[PhoronixDownload]):
        self.downloads = downloads

    @staticmethod
    def from_path(path: PathType):
        downloads = []

        tree = ET.parse(path)
        for download in tree.find("Downloads"):
            if download.tag == "Package":
                downloads.append(PhoronixDownload.from_xml(download))

        return PhoronixDownloads(downloads)


class PhoronixSystemMonitorResult:
    """Represents a Phoronix System Monitor Result"""
    
    def __init__(
        self,
        sensor: str,
        polling_frequency: Optional[int]
    ):
        self.sensor = sensor
        self.polling_frequency = polling_frequency
    
    @staticmethod
    def from_xml(element: ET.Element):
        polling_frequency = element.find("PollingFrequency")
        if polling_frequency is not None:
            polling_frequency = int(polling_frequency.text)

        return PhoronixSystemMonitorResult(
            sensor=element.find("Sensor").text,
            polling_frequency=polling_frequency
        )


class PhoronixResultsParser:
    """Represents a Phoronix Results Parser."""
    
    def __init__(
        self,
        output_template: str,
        strip_from_result: Optional[str],
        strip_result_postfix: Optional[str],
        multi_match: Optional[str],
        divide_result_by: Optional[int],
        divide_result_divisor: Optional[int],
        multiply_result_by: Optional[str],
        turn_chars_to_space: Optional[str],
        delete_output_before: Optional[str],
        delete_output_after: Optional[str]
    ):
        self.output_template = output_template
        self.strip_from_result = strip_from_result
        self.strip_result_postfix = strip_result_postfix
        self.multi_match = multi_match
        self.divide_result_by = divide_result_by
        self.divide_result_divisor = divide_result_divisor
        self.multiply_result_by = multiply_result_by
        self.turn_chars_to_space = turn_chars_to_space
        self.delete_output_before = delete_output_before
        self.delete_output_after = delete_output_after
    
    @staticmethod
    def from_xml(element: ET.Element):
        return PhoronixResultsParser(
            output_template=element.find("OutputTemplate").text,
            strip_from_result=find_optional(element, "StripFromResult"),
            strip_result_postfix=find_optional(element, "StripResultPostfix"),
            multi_match=find_optional(element, "MultiMatch"),
            divide_result_by=find_optional(element, "DivideResultBy"),
            divide_result_divisor=find_optional(element, "DivideResultDivisor"),
            multiply_result_by=find_optional(element, "MultiplyResultBy"),
            turn_chars_to_space=find_optional(element, "TurnCharsToSapce"),
            delete_output_before=find_optional(element, "DeleteOutputBefore"),
            delete_output_after=find_optional(element, "DeleteOutputAfter"),
        )


class PhoronixResultsDefinition:
    """Represents a Phoronix Results Definition."""
    
    def __init__(self, system_monitors: Iterable[PhoronixSystemMonitorResult], results_parsers: Iterable[PhoronixResultsParser]):
        self.system_monitors = system_monitors
        self.results_parsers = results_parsers

    @staticmethod
    def from_path(path: PathType):
        system_monitors = []
        results_parsers = []

        tree = ET.parse(path)
        for definition in tree.getroot():
            if definition.tag == "SystemMonitor":
                system_monitors.append(PhoronixSystemMonitorResult.from_xml(definition))
            elif definition.tag == "ResultsParser":
                results_parsers.append(PhoronixResultsParser.from_xml(definition))

        return PhoronixResultsDefinition(system_monitors, results_parsers)


class PhoronixTestInformation:
    """Represents Phoronix Test Information."""
    
    def __init__(self, executable: Optional[str]):
        # we only need the custom executable name if there is one specified
        self.executable = executable
    
    @staticmethod
    def from_xml(element: ET.Element):
        return PhoronixTestInformation(executable=find_optional(element, "Executable"))


class PhoronixTestProfile:
    """Represents a Phoronix Test Profile."""
    
    def __init__(
        self,
        supported_platforms: Optional[Iterable[str]],
        supported_architectures: Optional[Iterable[str]],
        external_dependencies: Optional[Iterable[str]]
    ):
        self.supported_platforms = supported_platforms
        self.supported_architectures = supported_architectures
        self.external_dependencies = external_dependencies
    
    @staticmethod
    def from_xml(element: ET.Element):
        return PhoronixTestProfile(
            supported_platforms=find_optional_array_str(element, "SupportedPlatforms"),
            supported_architectures=find_optional_array_str(element, "SupportedArchitectures"),
            external_dependencies=find_optional_array_str(element, "ExternalDependencies")
        )


class PhoronixDefaultTestSettings:
    """Represents the default test settings for a Phoronix test profile."""
    
    def __init__(
        self,
        arguments: Optional[str],
        post_arguments: Optional[str]
    ):
        self.arguments = arguments
        self.post_arguments = post_arguments
    
    @staticmethod
    def from_xml(element: ET.Element):
        return PhoronixDefaultTestSettings(
            arguments=find_optional(element, "Arguments"),
            post_arguments=find_optional(element, "PostArguments"),
        )


class PhoronixTestOptionEntry:
    """Represents a Phoronix test option entry."""
    
    def __init__(
        self,
        name: str,
        value: Optional[str]
    ):
        self.name = name
        self.value = value
    
    @staticmethod
    def from_xml(element: ET.Element):
        return PhoronixTestOptionEntry(
            name=find_optional(element, "Name"),
            value=find_optional(element, "Value")
        )
    
    
class PhoronixTestOption:
    """Represents a Phoronix test option."""
    
    def __init__(
        self,
        display_name: str,
        identifier: Optional[str],
        argument_prefix: Optional[str],
        argument_postfix: Optional[str],
        entries: Iterable[PhoronixTestOptionEntry]
    ):
        self.display_name = display_name
        self.identifier = identifier
        self.argument_prefix = argument_prefix
        self.argument_postfix = argument_postfix
        self.entries = entries
        
    def get_valid_values(self):
        return list(map(lambda entry: entry.value, self.entries))
    
    @staticmethod
    def from_xml(element: ET.Element):
        menu = element.find("Menu")
        entries = []
        if menu is not None:
            entries = list(map(lambda el: PhoronixTestOptionEntry.from_xml(el), menu.findall("Entry")))
        
        return PhoronixTestOption(
            display_name=find_optional(element, "DisplayName"),
            identifier=find_optional(element, "Identifier"),
            argument_prefix=find_optional(element, "ArgumentPrefix"),
            argument_postfix=find_optional(element, "ArgumentPostfix"),
            entries=entries
        )


class PhoronixTestSettings:
    """Represents the Phoronix test settings of a test profile."""
    
    def __init__(
        self,
        default: Optional[PhoronixDefaultTestSettings],
        options: Iterable[PhoronixTestOption]
    ):
        self.default = default
        self.options = options
    
    @staticmethod
    def from_xml(element: ET.Element):
        
        default = element.find("Default")
        if default is not None:
            default = PhoronixDefaultTestSettings.from_xml(default)
    
        options = list(map(lambda el: PhoronixTestOption.from_xml(el), element.findall("Option")))
        return PhoronixTestSettings(
            default=default,
            options=options
        )


class PhoronixTestDefinition:
    """Represents a Phoronix test definition."""
    
    def __init__(
        self,
        test_information: PhoronixTestInformation,
        test_profile: PhoronixTestProfile,
        test_settings: Optional[PhoronixTestSettings]
    ):
        self.test_information = test_information
        self.test_profile = test_profile
        self.test_settings = test_settings

    @staticmethod
    def from_path(path: PathType):
        tree = ET.parse(path)
        test_information = PhoronixTestInformation.from_xml(tree.find("TestInformation"))
        test_profile = PhoronixTestProfile.from_xml(tree.find("TestProfile"))
        
        test_settings = tree.find("TestSettings")
        if test_settings is not None:
            test_settings = PhoronixTestSettings.from_xml(test_settings)

        return PhoronixTestDefinition(test_information, test_profile, test_settings)


class PhoronixTestSuite:
    """Represents a Phoronix test suite."""
    
    def __init__(
        self,
        install: Optional[PathType],
        interim: Optional[PathType],
        post: Optional[PathType],
        pre: Optional[PathType],
        downloads: PhoronixDownloads,
        results_def: PhoronixResultsDefinition,
        test_def: PhoronixTestDefinition
    ):
        self.install = install
        self.interim = interim
        self.post = post
        self.pre = pre
        self.downloads = downloads
        self.results_def = results_def
        self.test_def = test_def

    @staticmethod
    def create_from_path(path: PathType):
        install_path = file_if_exists(path, "install.sh")
        interim_path = file_if_exists(path, "interim.sh")
        post_path = file_if_exists(path, "post.sh")
        pre_path = file_if_exists(path, "pre.sh")

        downloads = file_if_exists(path, "downloads.xml")
        results_def = file_if_exists(path, "results-definition.xml")
        test_def = file_if_exists(path, "test-definition.xml")

        if downloads is not None:
            downloads = PhoronixDownloads.from_path(downloads)
        if results_def is not None:
            results_def = PhoronixResultsDefinition.from_path(results_def)
        if test_def is not None:
            test_def = PhoronixTestDefinition.from_path(test_def)

        return PhoronixTestSuite(
            install=install_path,
            interim=interim_path,
            post=post_path,
            pre=pre_path,
            downloads=downloads,
            results_def=results_def,
            test_def=test_def
        )
    
    