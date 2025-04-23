import yaml, os



def parser_Yaml(filePath):
    with open(filePath, "r", encoding="utf-8") as file:
        yamldata = yaml.safe_load(file)
        return yamldata
    


