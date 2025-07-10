# generates the list of dicitonaries for the campaign from the config and app files

# dictonary for one command
single_dict_format = {
   "--algorithm": None,
   "--block-size": None,
   "--max-nfa-size": None,
   "--report-off": None,
   "--report-filename": None,
   "--result-capacity": None,
   "--input-start-pos": None,
   "--input-len": None,
   "--input": None,
   "--automata": None,
   "--split-entire-inputstream-to-chunk-size": None,
   "--only-exec-cc-with-state-id": None,
   "--only-exec-ccid": None,
   "--duplicate-input-stream": None,
   "--quick-validation": None,
   "--unique-frequency": None,
   "--padding": None,
   "--app-name": None,
   "--use-uvm": None,
   "--quit-degree": None,
   "--remove-degree": None,
   "--add-aan-start": None,
   "--add-aas-interval": None,
   "--unique": None,
   "--active-threshold": None,
   "--validation": None,
   "--use-soa": None,
   "--precompute-cutoff": None,
   "--precompute-depth": None,
   "--data-buffer-fetch-size": None,
   "--motivate-worklist-length": None,
   "--num-state-per-group": None,
   "--group-num": None,
   "--tuning": None,
   "--pc-use-uvm": None,
   "--adaptive-aas": None,
   "--try-adaptive-aas": None,
   "--compress-prec-table": None,
   "--output-file": None,
}


from typing import Any, Dict, List
import itertools
import os
import csv


def get_app_names(apps_dict: Dict) -> List[str]:
    app_names = []
    for a in apps_dict['apps']:
        app_names.append(a['name'])

    return app_names



def construct_dict(config_dict, cfg_name, app, isHS, isVASim, input_file, anml, param_order, params, quick_validation = False) -> Dict[str, Any]:
    assert(cfg_name in config_dict['exp_parameters'])

    d = {}
    if isHS:
        for param_idx in range(len(param_order)):
            d[param_order[param_idx]] = params[param_idx]

        d['--no-name-provided'] = []
        d['--no-name-provided'].append(anml)
        d['--no-name-provided'].append(input_file)
        d['-v'] = quick_validation

    elif isVASim:
        for param_idx in range(len(param_order)):
            d[param_order[param_idx]] = params[param_idx]

        d['--no-name-provided'] = []
        d['--no-name-provided'].append(anml)
        d['--no-name-provided'].append(input_file)

    else:
        d["-a"] = anml
        d["-i"] = input_file
        d["--app-name"] = app

        for param_idx in range(len(param_order)):
            d[f"--{param_order[param_idx]}"] = params[param_idx]

        # cmd_str_template += "--quick-validation=%s " % quick_validation
        d["--quick-validation"] = quick_validation

    return d

# All the command attributes that were not initialized through the config and app file are init to None
def pad_dict(cmd_dict):

    cmd_dict_copy = cmd_dict.copy()
    for key in single_dict_format:
        if key not in cmd_dict_copy:
            cmd_dict_copy[key] = None

    return cmd_dict_copy


'''
Given a config dict, app dict and a specific app and config entry generate a list of commands
as dictionaries in a list
'''
def gen_cmd_dicts(config, apps_dict, app_name: str, config_name: str) -> List[Dict[str, Any]]:

    list_of_dicts = []

    output_name = ""
    list_of_list = []
    param_order = [] # names of the options
    for tup in config['exp_parameters'][config_name]:

        if(len(tup) >= 2 and tup[0] == "app"):
            if(app_name not in tup[1]):
                return {}

        if(len(tup) >= 2 and tup[0] == "excludedApp"):
            if (app_name in tup[1]):
                return {}

        if(len(tup) >= 2 and tup[0] == "output-name"):
            output_name = tup[1]

        if not (len(tup) >= 3 and tup[2] == 'nocombination'):
            param_order.append(tup[0])
            list_of_list.append(tup[1])

    isHS = False
    isVASim = False
    if "hyperscan" in config_name:
        isHS = True
    elif "vasim" in config_name:
        isVASim = True
    
    # Fetching the input file, anml file and quick validation file paths from the application file
    input_file = ""
    anml_file = ""
    quick_validation = ""
    for a in apps_dict['apps']:
        if a['name'] == app_name:

            input_file = os.path.join(apps_dict['root'], a['input'])
            if (isHS):
                anml_file = os.path.join(apps_dict['root'], a['hs'])
            else:
                anml_file = os.path.join(apps_dict['root'], a['automata'])
            quick_validation = a['quick_validation']

    if "error" in anml_file:
        return {}

    # the star operator unpacks the list according to how many arguments the function takes
    for combin in itertools.product(*list_of_list):
        cmd_dict = construct_dict(
            config, 
            config_name, 
            app_name, 
            isHS, 
            isVASim, 
            input_file, 
            anml_file, 
            param_order, 
            combin, 
            quick_validation)

        cmd_dict["--output-file"] = output_name
        padded_cmd_dict = pad_dict(cmd_dict)
        # sorting according to keys to keep the same order
        sorted_keys = []
        for k in padded_cmd_dict.keys(): sorted_keys.append(k)
        sorted_keys.sort()
        sd = {}
        for sk in sorted_keys:
            sd[sk] = padded_cmd_dict[sk]
        list_of_dicts.append(sd)
    
    return list_of_dicts


# Generates a list of dictionaries given an app and config file
def gen_dict_list(app_file: str, config_file: str) -> List[Dict[str, Any]]:

    result = []

    apps = open(app_file,'r')
    config = open(config_file,'r')

    app_dict = eval(apps.read())
    config_dict = eval(config.read())

    # breakpoint()

    app_names = get_app_names(app_dict)
    for app in app_names:
        for cfg in config_dict["exp_parameters"]:
            app_dicts = gen_cmd_dicts(config_dict, app_dict, app, cfg)
            result.extend(app_dicts)

    return result


# if __name__ == 'main':

app_file = "./app_spec_ngap_new_quickvalidation_part1"
config_file = "./exec_config_ngap_groups_design_NAP"

app_file_2 = "./app_spec_ngap_new_quickvalidation_part1"
config_file_2 = "./exec_config_ngap_groups_design_NAP"

app_file_3 = "./app_spec_ngap_new_quickvalidation_part1"
config_file_3 = "./exec_config_ngap_groups_design_NAP"

dict_list_1 = gen_dict_list(app_file, config_file)
dict_list_2 = gen_dict_list(app_file_2, config_file_2)
dict_list_3 = gen_dict_list(app_file_3, config_file_3)

# breakpoint()

lists = [dict_list_1, dict_list_2, dict_list_3]

keys = dict_list_1[0].keys()

for idx in range(len(lists)):
    fp = open(f"../list_of_dicts/part{idx+1}.csv", 'w')
    writer = csv.DictWriter(fp, fieldnames=keys)
    writer.writeheader()
    for d in lists[idx]:
        writer.writerow(d)
    fp.close()

    # part2_file = open("../list_of_dicts/part2.csv", 'w')
    # for p2d in dict_list_2:
    #     pass
    # part2_file.close()

    # part3_file = open("../list_of_dicts/part3.csv", 'w')
    # for p3d in dict_list_3:
    #     pass
    # part3_file.close()