# РАБОТА С МЕТА ФАЙЛОМ ОПИСАНИЯ УСТРОЙСТВА

import json

from CORE.MainConfigHandler import MainConfigHandler



meta_path = "meta.json"
config_handler = MainConfigHandler.from_json_file(meta_path)


#t = config_handler.get_param_info("T_LVCBSUP_1_RCBF1_FuncEnabled")
#print(t) lvrbvtr1

pars = config_handler.find_parameters_starting_with("")

result = []
for par in pars:
    if par["group"] == "Measurement" or par["group"] == "measurement": # "measurement":  #"setting": # and par["fullDescription"] == "Внешнее отключение от УРОВ НН":
        #print(par)
        result.append(par)  # добавляем в список       
    #if par["group"] == "Setting" or par["group"] == "setting":    
        #print(par)
        #result.append(par)  # добавляем в список

# Сохранение всех параметров в out.json
with open("out.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=4)


i = config_handler.get_param_info("DZT2_IO_1_VLVIsolOp")
#print(i)