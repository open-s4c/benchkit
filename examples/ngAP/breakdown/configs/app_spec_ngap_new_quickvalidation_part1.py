root = ["/ngAP/automata_benchmark_original"] * 28  # Same for all apps

name = [
    "Brill", "EntityResolution", "Dotstar", "PowerEN", "CRISPR_CasOFFinder", 
    "CRISPR_CasOT", "RandomForest_20_400_200", "RandomForest_20_400_270", 
    "RandomForest_20_800_200", "Hamming_N1000_l18_d3", "Hamming_N1000_l22_d5", 
    "Hamming_N1000_l31_d10", "Levenshtein_l19d3", "Levenshtein_l24d5", 
    "Levenshtein_l37d10", "Protomata", "APPRNG4", "SeqMatch_BIBLE_w6_p6", 
    "SeqMatch_BIBLE_w6_p10", "Fermi", "YARA", "Bro217", "ExactMath", 
    "Ranges05", "Ranges1", "TCP", None, None
]

input = [
    "AutomataZoo/Brill/benchmarks/inputs/brown_corpus.txt",
    "AutomataZoo/EntityResolution/benchmarks/inputs/1m_names.input",
    "ANMLZoo/Dotstar/inputs/backdoor_10MB.input",
    "ANMLZoo/PowerEN/inputs/poweren_10MB.input",
    "AutomataZoo/CRISPR/benchmarks/CasOFFinder/inputs/10MB_G.dna",
    "AutomataZoo/CRISPR/benchmarks/CasOT/inputs/10MB_H.dna",
    "AutomataZoo/RandomForest/benchmarks/inputs/20_400_200_inputs/input_features_large.bin",
    "AutomataZoo/RandomForest/benchmarks/inputs/20_400_270_inputs/input_features_large.bin",
    "AutomataZoo/RandomForest/benchmarks/inputs/20_800_200/input_features_large.bin",
    "AutomataZoo/Hamming/benchmarks/N1000_l18_d3/inputs/10MB_D.DNA",
    "AutomataZoo/Hamming/benchmarks/N1000_l22_d5/inputs/10MB_E.dna",
    "AutomataZoo/Hamming/benchmarks/N1000_l31_d10/inputs/10MB_F.dna",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l19_d3/inputs/10MB_A.dna",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l24_d5/inputs/10MB_B.dna",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l37_d10/inputs/10MB_C.DNA",
    "AutomataZoo/Protomata/benchmarks/inputs/30k_prots.input",
    "AutomataZoo/APPRNG/benchmarks/4_sided/inputs/10MB_A.prng",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p6/inputs/transactions.bin",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p10/inputs/transactions.bin",
    "ANMLZoo/Fermi/inputs/rp_input_10MB.input",
    "AutomataZoo/YARA/benchmarks/YARA/inputs/malware_malz2.input",
    "Regex/Bro217/inputs/Bro217_10MB_depth_s0_p0.75.trace.input",
    "Regex/ExactMath/inputs/exact-math_depth_s0_p0.75.trace.input",
    "Regex/Ranges05/inputs/ranges05_depth_s0_p0.75.trace.input",
    "Regex/Ranges1/inputs/ranges1_depth_s0_p0.75.trace.input",
    "Regex/TCP/inputs/TCP_depth_s0_p0.75.trace.input",
    None, None
]

mnrl = [
    "AutomataZoo/Brill/benchmarks/automata/brill.mnrl",
    "AutomataZoo/EntityResolution/benchmarks/mnrl/automata_0.mnrl",
    "ANMLZoo/Dotstar/mnrl/automata_0.mnrl",
    "ANMLZoo/PowerEN/mnrl/automata_0.mnrl",
    "AutomataZoo/CRISPR/benchmarks/CasOFFinder/mnrl/automata_0.mnrl",
    "AutomataZoo/CRISPR/benchmarks/CasOT/mnrl/automata_0.mnrl",
    "AutomataZoo/RandomForest/benchmarks/mnrl/automata_0.mnrl",
    "AutomataZoo/RandomForest/benchmarks/mnrl/automata_0.mnrl",
    "AutomataZoo/RandomForest/benchmarks/mnrl/automata_0.mnrl",
    "AutomataZoo/Hamming/benchmarks/N1000_l18_d3/mnrl/automata_0.mnrl",
    "AutomataZoo/Hamming/benchmarks/N1000_l22_d5/mnrl/automata_0.mnrl",
    "AutomataZoo/Hamming/benchmarks/N1000_l31_d10/mnrl/automata_0.mnrl",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l19_d3/mnrl/automata_0.mnrl",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l24_d5/mnrl/automata_0.mnrl",
    None,
    "AutomataZoo/Protomata/benchmarks/automata/protomata.mnrl",
    "AutomataZoo/APPRNG/benchmarks/4_sided/mnrl/automata_0.mnrl",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p6/mnrl/automata_0.mnrl",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p10/mnrl/automata_0.mnrl",
    "ANMLZoo/Fermi/mnrl/automata_0.mnrl",
    "AutomataZoo/YARA/benchmarks/YARA/automata/YARA.mnrl",
    None, None, None, None, None, None, None
]

short_name = [
    "Brill", "ER", None, None, None, None, None, None, None, None, 
    None, None, None, None, None, None, None, None, None, None, 
    None, None, None, None, None, None, None, None
]

anml = [
    None,
    "AutomataZoo/EntityResolution/benchmarks/automata/er_10000names.anml",
    "ANMLZoo/Dotstar/anml/backdoor_dotstar.1chip.anml",
    "ANMLZoo/PowerEN/anml/complx_01000_00123.1chip.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOFFinder/automata/CRISPR_CasOFFinder_2000.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOT/automata/CRISPR_CasOT_2000.anml",
    "AutomataZoo/RandomForest/benchmarks/automata/rf_20_400_200.anml",
    "AutomataZoo/RandomForest/benchmarks/automata/rf_20_400_270.anml",
    "AutomataZoo/RandomForest/benchmarks/automata/rf_20_800_200.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l18_d3/automata/ham_1000_3.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l22_d5/automata/ham_1000_5.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l31_d10/automata/ham_1000_10.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l19_d3/automata/lev_1000_3.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l24_d5/automata/lev_1000_5.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l37_d10/automata/lev_1000_10.anml",
    None,
    "AutomataZoo/APPRNG/benchmarks/4_sided/automata/apprng_n1000_d4.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p6/automata/6wide_6pad.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p10/automata/6wide_10pad.anml",
    "ANMLZoo/Fermi/anml/fermi_2400.1chip.anml",
    None,
    "Regex/Bro217/anml/bro217.anml",
    "Regex/ExactMath/anml/exactmath.anml",
    "Regex/Ranges05/anml/ranges05.anml",
    "Regex/Ranges1/anml/ranges1.anml",
    "Regex/TCP/anml/automata_0.anml",
    None, None
]

anml_no_ORs = [
    "AutomataZoo/Brill/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/EntityResolution/benchmarks/anml_remove_or/automata_0.anml",
    "ANMLZoo/Dotstar/anml_remove_or/automata_0.anml",
    "ANMLZoo/PowerEN/anml_remove_or/automata_0.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOFFinder/anml_remove_or/automata_0.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOT/anml_remove_or/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l18_d3/anml_remove_or/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l22_d5/anml_remove_or/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l31_d10/anml_remove_or/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l19_d3/anml_remove_or/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l24_d5/anml_remove_or/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l37_d10/anml_remove_or/automata_0.anml",
    "AutomataZoo/Protomata/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/APPRNG/benchmarks/4_sided/anml_remove_or/automata_0.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p6/anml_remove_or/automata_0.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p10/anml_remove_or/automata_0.anml",
    "ANMLZoo/Fermi/anml_remove_or/automata_0.anml",
    "AutomataZoo/YARA/benchmarks/YARA/anml_remove_or/automata_0.anml",
    None, None, None, None, None, None, None
]

optimized_ANML = [
    "AutomataZoo/Brill/benchmarks/optimized_ANML/automata_0.anml",
    "AutomataZoo/EntityResolution/benchmarks/optimized_ANML/automata_0.anml",
    "ANMLZoo/Dotstar/optimized_ANML/automata_0.anml",
    "ANMLZoo/PowerEN/optimized_ANML/automata_0.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOFFinder/optimized_ANML/automata_0.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOT/optimized_ANML/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/optimized_ANML/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/optimized_ANML/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/optimized_ANML/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l18_d3/optimized_ANML/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l22_d5/optimized_ANML/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l31_d10/optimized_ANML/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l19_d3/optimized_ANML/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l24_d5/optimized_ANML/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l37_d10/optimized_ANML/automata_0.anml",
    "AutomataZoo/Protomata/benchmarks/optimized_ANML/automata_0.anml",
    "AutomataZoo/APPRNG/benchmarks/4_sided/optimized_ANML/automata_0.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p6/optimized_ANML/automata_0.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p10/optimized_ANML/automata_0.anml",
    "ANMLZoo/Fermi/optimized_ANML/automata_0.anml",
    "AutomataZoo/YARA/benchmarks/YARA/optimized_ANML/automata_0.anml",
    None, None, None, None, None, None, None
]

hs = [
    "AutomataZoo/Brill/benchmarks/hs/automata.hs",
    "AutomataZoo/EntityResolution/benchmarks/hs/automata.hs",
    "ANMLZoo/Dotstar/hs/automata.hs",
    "ANMLZoo/PowerEN/hs/automata.hs",
    "AutomataZoo/CRISPR/benchmarks/CasOFFinder/hs/automata.hs",
    "AutomataZoo/CRISPR/benchmarks/CasOT/hs/automata.hs",
    "AutomataZoo/RandomForest/benchmarks/hs/automata.hs",
    "AutomataZoo/RandomForest/benchmarks/hs/automata.hs",
    "AutomataZoo/RandomForest/benchmarks/hs/automata.hs",
    "AutomataZoo/Hamming/benchmarks/N1000_l18_d3/hs/automata.hs",
    "AutomataZoo/Hamming/benchmarks/N1000_l22_d5/hs/automata.hs",
    "AutomataZoo/Hamming/benchmarks/N1000_l31_d10/hs/automata.hs",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l19_d3/hs/automata.hs",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l24_d5/hs/automata.hs",
    None,
    "AutomataZoo/Protomata/benchmarks/hs/automata.hs",
    "AutomataZoo/APPRNG/benchmarks/4_sided/hs/automata.hs",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p6/hs/automata.hs",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p10/hs/automata.hs",
    "ANMLZoo/Fermi/hs/automata.hs",
    "AutomataZoo/YARA/benchmarks/YARA/hs/automata.hs",
    "Regex/Bro217/anml/bro217.hs",
    "Regex/ExactMath/anml/exactmath.hs",
    "Regex/Ranges05/anml/ranges05.hs",
    "Regex/Ranges1/anml/ranges1.hs",
    "Regex/TCP/anml/automata_0.hs",
    None, None
]

automata = [
    "AutomataZoo/Brill/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/EntityResolution/benchmarks/anml_remove_or/automata_0.anml",
    "ANMLZoo/Dotstar/anml_remove_or/automata_0.anml",
    "ANMLZoo/PowerEN/anml_remove_or/automata_0.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOFFinder/anml_remove_or/automata_0.anml",
    "AutomataZoo/CRISPR/benchmarks/CasOT/anml_remove_or/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/RandomForest/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l18_d3/anml_remove_or/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l22_d5/anml_remove_or/automata_0.anml",
    "AutomataZoo/Hamming/benchmarks/N1000_l31_d10/anml_remove_or/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l19_d3/anml_remove_or/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l24_d5/anml_remove_or/automata_0.anml",
    "AutomataZoo/Levenshtein/benchmarks/N1000_l37_d10/anml_remove_or/automata_0.anml",
    "AutomataZoo/Protomata/benchmarks/anml_remove_or/automata_0.anml",
    "AutomataZoo/APPRNG/benchmarks/4_sided/anml_remove_or/automata_0.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p6/anml_remove_or/automata_0.anml",
    "AutomataZoo/SeqMatch/benchmarks/BIBLE_w6_p10/anml_remove_or/automata_0.anml",
    "ANMLZoo/Fermi/anml_remove_or/automata_0.anml",
    "AutomataZoo/YARA/benchmarks/YARA/anml_remove_or/automata_0.anml",
    "Regex/Bro217/anml/bro217.anml",
    "Regex/ExactMath/anml/exactmath.anml",
    "Regex/Ranges05/anml/ranges05.anml",
    "Regex/Ranges1/anml/ranges1.anml",
    "Regex/TCP/anml/automata_0.anml",
    None, None
]

quick_validation = [
    "9038877", "795", "0", "4304", "62", "52", "0", "0", "99500", "345", 
    "-1", "-1", "719", "-1", "-1", "72852", "500000000", "1297900", 
    "1297900", "90951", "85044", "16956", "34", "39", "25", "100824", 
    None, None
]

exclude_apps = [
    "Hamming_N1000_l22_d5", "Hamming_N1000_l31_d10", "Levenshtein_l24d5", 
    "Levenshtein_l37d10", "RandomForest_20_400_270", "RandomForest_20_800_200", 
    "SeqMatch_BIBLE_w6_p10", "Fermi", "FileCarving", "smallFileCarving", 
    None, None, None, None, None, None, None, None, None, None, 
    None, None, None, None, None, None, None, None
]