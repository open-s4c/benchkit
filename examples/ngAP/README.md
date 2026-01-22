# Campaign for Breakdown and Sensitivity Benchmarks for ngAP  
These campaigns perform benchmarks for the breakdown and sensitivity sections of ngAP (Non-blocking Large-scale Automata Processing
on GPUs).  
https://getianao.github.io/papers/asplos24ngap.pdf

## parse_options.py
This file is used to convert the configs stored in /configs directory in lists of dictionaries that IterateVariablesCampaign accepts.


## Getting the configuration files
```
mkdir configs && cd configs
wget https://raw.githubusercontent.com/getianao/ngAP/refs/heads/master/code/scripts/configs/app_spec_ngap_new_quickvalidation_part1 \
    https://raw.githubusercontent.com/getianao/ngAP/refs/heads/master/code/scripts/configs/app_spec_ngap_new_quickvalidation_part2 \
    https://raw.githubusercontent.com/getianao/ngAP/refs/heads/master/code/scripts/configs/app_spec_ngap_new_quickvalidation_part3 \
    https://raw.githubusercontent.com/getianao/ngAP/refs/heads/master/code/scripts/configs/exec_config_ngap_groups_design_NAP \
    https://raw.githubusercontent.com/getianao/ngAP/refs/heads/master/code/scripts/configs/exec_config_ngap_groups_design_NAP_4degree
cd ..
```

## Setting up NGAP
To make this benchmark work you need to clone the ngAP repo using the following command:  
```
git clone --recursive git@github.com:getianao/ngAP.git
```
and then you need to move your benchkit directory to the directory with ngAP contents.  
This is because running ngap benchmarks requires you to use docker and you need to be able to run benchkit campaigns within the docker container.
By doing this and following the steps documented on: https://github.com/getianao/ngAP, benchkit is mounted within the docker container.

## Inside the docker container
### Setting up the python environment
```
./configure.sh
source venv/bin/activate
```

### Setting PYTHONENV variable for ncu_report processing
```export PYTHONPATH="${PYTHONPATH}:/opt/nvidia/nsight-compute/2022.4.1/extras/python"```

### Running the campaign
python3 campaign.py