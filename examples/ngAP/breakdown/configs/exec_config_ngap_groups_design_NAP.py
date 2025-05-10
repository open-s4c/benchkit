exec = [
    'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap',
    'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap',
    'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap', 'ngap'
]

excludedApp = [
    ["Fermi", "Snort", "smallSnort"],                          # 0: o0-blocking
    ["Fermi", "Snort", "smallSnort"],                          # 1: o0-nonblocking-NAP
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 2: o1-nonblocking
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 3: o4-nonblocking-r1f
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 4: o3-nonblocking-p3
    None,                                                      # 5: o3-nonblocking-p2 (uses 'app')
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 6: oa-nonblocking-all-p3r1
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 7: oa-nonblocking-all-p3r1f
    None,                                                      # 8: oa-nonblocking-all-p2r1f (uses 'app')
    None,                                                      # 9: oa-nonblocking-all-p2r1 (uses 'app')
    None,                                                      # 10: o0-blocking-unique (uses 'app')
    None,                                                      # 11: o0-nonblocking-NAP-unique (uses 'app')
    None,                                                      # 12: o1-nonblocking-unique (uses 'app')
    None,                                                      # 13: o4-nonblocking-r1f-unique (uses 'app')
    None,                                                      # 14: o3-nonblocking-p3-unique (uses 'app')
    None,                                                      # 15: oa-nonblocking-all-p3r1f-unique (uses 'app')
    None,                                                      # 16: oa-nonblocking-all-p3r1-unique (uses 'app')
    None,                                                      # 17: o1-nonblocking-short (uses 'app')
    None,                                                      # 18: o4-nonblocking-r1f-short (uses 'app')
    None,                                                      # 19: o3-nonblocking-p3-short (uses 'app')
    None,                                                      # 20: oa-nonblocking-all-p3r1f-short (uses 'app')
    None,                                                      # 21: oa-nonblocking-all-p3r1-short (uses 'app')
    None,                                                      # 22: (unused)
    None,                                                      # 23: (unused)
    None,                                                      # 24: (unused)
    None,                                                      # 25: (unused)
    None,                                                      # 26: (unused)
    None                                                       # 27: (unused)
]

app = [
    None,                                                      # 0
    None,                                                      # 1
    None,                                                      # 2
    None,                                                      # 3
    None,                                                      # 4
    ["Hamming_N1000_l18_d3", "YARA"],                         # 5: o3-nonblocking-p2
    None,                                                      # 6
    None,                                                      # 7
    ["Hamming_N1000_l18_d3", "YARA"],                         # 8: oa-nonblocking-all-p2r1f
    ["Hamming_N1000_l18_d3", "YARA"],                         # 9: oa-nonblocking-all-p2r1
    ["Fermi", "Snort", "smallSnort"],                         # 10: o0-blocking-unique
    ["Fermi", "Snort", "smallSnort"],                         # 11: o0-nonblocking-NAP-unique
    ["Fermi", "Snort", "smallSnort"],                         # 12: o1-nonblocking-unique
    ["Fermi", "Snort", "smallSnort"],                         # 13: o4-nonblocking-r1f-unique
    ["Fermi", "Snort", "smallSnort"],                         # 14: o3-nonblocking-p3-unique
    ["Fermi", "Snort", "smallSnort"],                         # 15: oa-nonblocking-all-p3r1f-unique
    ["Fermi", "Snort", "smallSnort"],                         # 16: oa-nonblocking-all-p3r1-unique
    ["Levenshtein_l19d3"],                                    # 17: o1-nonblocking-short
    ["Levenshtein_l19d3"],                                    # 18: o4-nonblocking-r1f-short
    ["Levenshtein_l19d3"],                                    # 19: o3-nonblocking-p3-short
    ["Levenshtein_l19d3"],                                    # 20: oa-nonblocking-all-p3r1f-short
    ["Levenshtein_l19d3"],                                    # 21: oa-nonblocking-all-p3r1-short
    None,                                                      # 22
    None,                                                      # 23
    None,                                                      # 24
    None,                                                      # 25
    None,                                                      # 26
    None                                                       # 27
]

algorithm = [
    ["blockinggroups"],       # 0
    ["NAPgroups"],            # 1
    ["nonblockinggroups"],    # 2
    ["nonblockingr1groups"],  # 3
    ["nonblockingpcgroups"],  # 4
    ["nonblockingpcgroups"],  # 5
    ["nonblockingallgroups"], # 6
    ["nonblockingallgroups"], # 7
    ["nonblockingallgroups"], # 8
    ["nonblockingallgroups"], # 9
    ["blockinggroups"],       # 10
    ["NAPgroups"],            # 11
    ["nonblockinggroups"],    # 12
    ["nonblockingr1groups"],  # 13
    ["nonblockingpcgroups"],  # 14
    ["nonblockingallgroups"], # 15
    ["nonblockingallgroups"], # 16
    ["nonblockinggroups"],    # 17
    ["nonblockingr1groups"],  # 18
    ["nonblockingpcgroups"],  # 19
    ["nonblockingallgroups"], # 20
    ["nonblockingallgroups"], # 21
    None,                     # 22
    None,                     # 23
    None,                     # 24
    None,                     # 25
    None,                     # 26
    None                      # 27
]

output_name = [
    "o0-blocking_",           # 0
    "o0-nonblocking-NAP_",    # 1
    "o1-nonblocking_",        # 2
    "o4-nonblocking-r1f_",    # 3
    "o3-nonblocking-p3_",     # 4
    "o3-nonblocking-p3_",     # 5
    "oa-nonblocking-all-p3r1_",  # 6
    "oa-nonblocking-all-p3r1f_", # 7
    "oa-nonblocking-all-p3r1f_", # 8
    "oa-nonblocking-all-p3r1_",  # 9
    "o0-blocking_",           # 10
    "o0-nonblocking-NAP_",    # 11
    "o1-nonblocking_",        # 12
    "o4-nonblocking-r1f_",    # 13
    "o3-nonblocking-p3_",     # 14
    "oa-nonblocking-all-p3r1f_", # 15
    "oa-nonblocking-all-p3r1_",  # 16
    "o1-nonblocking_",        # 17
    "o4-nonblocking-r1f_",    # 18
    "o3-nonblocking-p3_",     # 19
    "oa-nonblocking-all-p3r1f_", # 20
    "oa-nonblocking-all-p3r1_",  # 21
    None,                     # 22
    None,                     # 23
    None,                     # 24
    None,                     # 25
    None,                     # 26
    None                      # 27
]

input_start_pos = [["0"]] * 28
input_len = [["1000000"]] * 28
split_entire_inputstream_to_chunk_size = [["1000000"]] * 28
group_num = [["1"]] * 28
duplicate_input_stream = [["600"]] * 28
unique = [
    ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'],
    ['true'], ['true'], ['true'], ['true'], ['true'], ['true'], ['true'], ['false'], ['false'], ['false'],
    ['false'], ['false'], None, None, None, None, None, None
]
unique_frequency = [["10"]] * 28
use_soa = [["false"]] * 28
result_capacity = [["54619400"]] * 28
use_uvm = [
    ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'],
    ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['true'], ['true'], ['true'],
    ['true'], ['true'], None, None, None, None, None, None
]
data_buffer_fetch_size = [
    None, ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'],
    None, ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'],
    ['25600'], ['25600'], None, None, None, None, None, None
]
add_aan_start = [
    None, ['0'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    None, ['0'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    ['256'], ['256'], None, None, None, None, None, None
]
add_aas_interval = [
    None, ['1'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    None, ['1'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    ['256'], ['256'], None, None, None, None, None, None
]
active_threshold = [
    None, None, None, ['0'], None, None, ['16'], ['0'], ['0'], ['16'],
    None, None, None, ['0'], None, ['0'], ['16'], None, ['0'], None,
    ['0'], ['16'], None, None, None, None, None, None
]
precompute_cutoff = [
    None, None, None, None, ['-1'], ['-1'], ['-1'], ['-1'], ['-1'], ['-1'],
    None, None, None, None, ['-1'], ['-1'], ['-1'], None, None, ['-1'],
    ['-1'], ['-1'], None, None, None, None, None, None
]
precompute_depth = [
    None, None, None, None, ['3'], ['2'], ['3'], ['3'], ['2'], ['2'],
    None, None, None, None, ['3'], ['3'], ['3'], None, None, ['3'],
    ['3'], ['3'], None, None, None, None, None, None
]
compress_prec_table = [
    None, None, None, None, ['true'], ['true'], ['true'], ['true'], ['true'], ['true'],
    None, None, None, None, ['true'], ['true'], ['true'], None, None, ['true'],
    ['true'], ['true'], None, None, None, None, None, None
]
pc_use_uvm = [
    None, None, None, None, ['false'], ['false'], ['false'], ['false'], ['false'], ['false'],
    None, None, None, None, ['false'], ['false'], ['false'], None, None, ['false'],
    ['false'], ['false'], None, None, None, None, None, None
]
report_off = [['false']] * 28
remove_degree = [['false']] * 28
quit_degree = [['false']] * 28
max_nfa_size = [["-1"]] * 28