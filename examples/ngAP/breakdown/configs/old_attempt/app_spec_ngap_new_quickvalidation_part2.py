names = ["Snort", "FileCarving", "ClamAV"]
inputs = [
    "AutomataZoo/Snort/benchmarks/inputs/wrccdc2012.pcap",
    "AutomataZoo/FileCarving/benchmarks/inputs/fat32_files.input",
    "AutomataZoo/ClamAV/benchmarks/inputs/clamav.input"
]
mnrls = [
    "AutomataZoo/Snort/benchmarks/automata/snort.mnrl",
    "AutomataZoo/FileCarving/benchmarks/mnrl/automata_0.mnrl",
    "AutomataZoo/ClamAV/benchmarks/mnrl/automata_0.mnrl"
]
anml_no_ORs = [
    "AutomataZoo/Snort/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/FileCarving/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/ClamAV/benchmarks/anml_remove_or/automata_0.anml"
]
optimized_ANMLs = [
    "AutomataZoo/Snort/benchmarks/optimized_ANML/automata_0.anml",
    "AutomataZoo/FileCarving/benchmarks/optimized_ANML/automata_0.anml",
    "AutomataZoo/ClamAV/benchmarks/optimized_ANML/automata_0.anml"
]
hss = [
    "AutomataZoo/Snort/benchmarks/hs/automata.hs",
    "AutomataZoo/FileCarving/benchmarks/hs/automata.hs",
    "AutomataZoo/ClamAV/benchmarks/hs/automata.hs"
]
automatas = [
    "AutomataZoo/Snort/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/FileCarving/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/ClamAV/benchmarks/anml_remove_or/automata_0.anml"
]
quick_validations = ["128259", "0", "1"]
exclude_apps = [
    "Hamming_N1000_l22_d5",
    "Hamming_N1000_l31_d10",
    "Levenshtein_l24d5",
    "Levenshtein_l37d10",
    "RandomForest_20_400_270",
    "RandomForest_20_800_200",
    "SeqMatch_BIBLE_w6_p10",
    "Fermi",
    "FileCarving",
    "smallFileCarving"
]
