import yaml, os, logging



def parser_Yaml(filePath):
    try:
        with open(filePath, "r", encoding="utf-8") as file:
            yamldata = yaml.safe_load(file)
            return yamldata
    except Exception as e:
        logging.error(e)
    


