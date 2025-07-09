exec = ['ngap'] * 28

excludedApp = [
    ["Fermi", "Snort", "smallSnort"],                          # 0: o0-blocking
    ["Fermi", "Snort", "smallSnort"],                          # 1: o0-nonblocking-NAP
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 2: o1-nonblocking
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 3: o4-nonblocking-r1f
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 4: o3-nonblocking-p3
    None,                                                      # 5: o3-nonblocking-p2 (uses 'app')
    ["Fermi", "Snort", "smallSnort", "Levenshtein_l19d3"],     # 6: oa-nonblocking-all-p3r1f
    None,                                                      # 7: oa-nonblocking-all-p2r1f (uses 'app')
    None,                                                      # 8: o0-blocking-unique (uses 'app')
    None,                                                      # 9: o0-nonblocking-NAP-unique (uses 'app')
    None,                                                      # 10: o1-nonblocking-unique (uses 'app')
    None,                                                      # 11: o4-nonblocking-r1f-unique (uses 'app')
    None,                                                      # 12: o3-nonblocking-p3-unique (uses 'app')
    None,                                                      # 13: oa-nonblocking-all-p3r1f-unique (uses 'app')
    None,                                                      # 14: o1-nonblocking-short (uses 'app')
    None,                                                      # 15: o4-nonblocking-r1f-short (uses 'app')
    None,                                                      # 16: o3-nonblocking-p3-short (uses 'app')
    None,                                                      # 17: oa-nonblocking-all-p3r1f-short (uses 'app')
    None, None, None, None, None, None, None, None, None       # Unused indices
]

app = [
    None,                                                      # 0
    None,                                                      # 1
    None,                                                      # 2
    None,                                                      # 3
    None,                                                      # 4
    ["Hamming_N1000_l18_d3", "YARA"],                         # 5: o3-nonblocking-p2
    None,                                                      # 6
    ["Hamming_N1000_l18_d3", "YARA"],                         # 7: oa-nonblocking-all-p2r1f
    ["Fermi", "Snort", "smallSnort"],                         # 8: o0-blocking-unique
    ["Fermi", "Snort", "smallSnort"],                         # 9: o0-nonblocking-NAP-unique
    ["Fermi", "Snort", "smallSnort"],                         # 10: o1-nonblocking-unique
    ["Fermi", "Snort", "smallSnort"],                         # 11: o4-nonblocking-r1f-unique
    ["Fermi", "Snort", "smallSnort"],                         # 12: o3-nonblocking-p3-unique
    ["Fermi", "Snort", "smallSnort"],                         # 13: oa-nonblocking-all-p3r1f-unique
    ["Levenshtein_l19d3"],                                    # 14: o1-nonblocking-short
    ["Levenshtein_l19d3"],                                    # 15: o4-nonblocking-r1f-short
    ["Levenshtein_l19d3"],                                    # 16: o3-nonblocking-p3-short
    ["Levenshtein_l19d3"],                                    # 17: oa-nonblocking-all-p3r1f-short
    None, None, None, None, None, None, None, None, None      # Unused indices
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
    ["blockinggroups"],       # 8
    ["NAPgroups"],            # 9
    ["nonblockinggroups"],    # 10
    ["nonblockingr1groups"],  # 11
    ["nonblockingpcgroups"],  # 12
    ["nonblockingallgroups"], # 13
    ["nonblockinggroups"],    # 14
    ["nonblockingr1groups"],  # 15
    ["nonblockingpcgroups"],  # 16
    ["nonblockingallgroups"], # 17
    None, None, None, None, None, None, None, None, None       # Unused indices
]

output_name = [
    "o0-blocking_",           # 0
    "o0-nonblocking-NAP_",    # 1
    "o1-nonblocking_",        # 2
    "o4-nonblocking-r1f_",    # 3
    "o3-nonblocking-p3_",     # 4
    "o3-nonblocking-p3_",     # 5
    "oa-nonblocking-all-p3r1f_", # 6
    "oa-nonblocking-all-p3r1f_", # 7
    "o0-blocking_",           # 8
    "o0-nonblocking-NAP_",    # 9
    "o1-nonblocking_",        # 10
    "o4-nonblocking-r1f_",    # 11
    "o3-nonblocking-p3_",     # 12
    "oa-nonblocking-all-p3r1f_", # 13
    "o1-nonblocking_",        # 14
    "o4-nonblocking-r1f_",    # 15
    "o3-nonblocking-p3_",     # 16
    "oa-nonblocking-all-p3r1f_", # 17
    None, None, None, None, None, None, None, None, None       # Unused indices
]

input_start_pos = [["0"]] * 28
input_len = [["1000000"]] * 28
split_entire_inputstream_to_chunk_size = [["1000000"]] * 28
group_num = [["1"]] * 28
duplicate_input_stream = [["600"]] * 28
unique = [
    ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'],
    ['true'], ['true'], ['true'], ['true'], ['true'], ['true'], ['false'], ['false'], ['false'], ['false'],
    None, None, None, None, None, None, None, None, None, None
]
unique_frequency = [["10"]] * 28
use_soa = [["false"]] * 28
result_capacity = [["54619400"]] * 28
use_uvm = [
    ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['false'],
    ['false'], ['false'], ['false'], ['false'], ['false'], ['false'], ['true'], ['true'], ['true'], ['true'],
    None, None, None, None, None, None, None, None, None, None
]
data_buffer_fetch_size = [
    None, ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'],
    None, ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'], ['25600'],
    None, None, None, None, None, None, None, None, None, None
]
add_aan_start = [
    None, ['0'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    None, ['0'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    None, None, None, None, None, None, None, None, None, None
]
add_aas_interval = [
    None, ['1'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    None, ['1'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'], ['256'],
    None, None, None, None, None, None, None, None, None, None
]
active_threshold = [
    None, None, None, ['0'], None, None, ['0'], ['0'],
    None, None, None, ['0'], None, ['0'], None, ['0'], None, ['0'],
    None, None, None, None, None, None, None, None, None, None
]
precompute_cutoff = [
    None, None, None, None, ['-1'], ['-1'], ['-1'], ['-1'],
    None, None, None, None, ['-1'], ['-1'], None, None, ['-1'], ['-1'],
    None, None, None, None, None, None, None, None, None, None
]
precompute_depth = [
    None, None, None, None, ['3'], ['2'], ['3'], ['2'],
    None, None, None, None, ['3'], ['3'], None, None, ['3'], ['3'],
    None, None, None, None, None, None, None, None, None, None
]
compress_prec_table = [
    None, None, None, None, ['true'], ['true'], ['true'], ['true'],
    None, None, None, None, ['true'], ['true'], None, None, ['true'], ['true'],
    None, None, None, None, None, None, None, None, None, None
]
pc_use_uvm = [
    None, None, None, None, ['false'], ['false'], ['false'], ['false'],
    None, None, None, None, ['false'], ['false'], None, None, ['false'], ['false'],
    None, None, None, None, None, None, None, None, None, None
]
report_off = [['false']] * 28
remove_degree = [['true']] * 28  # Note: Changed from 'false' in ngap_config1.txt
quit_degree = [['false']] * 28
max_nfa_size = [["-1"]] * 28