import asyncio
import argparse
import logging
import os
import pandas as pd
import csv
from core import (
    parser_Yaml,
    robot_login,
    )
from utils import encodePassword


# Setting: logging style
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s ",
    datefmt="%Y-%m-%d %H:%M:%S",
    )



async def main(yaml_path):
    logging.info("Starting poker bot...")
    current_folder = os.getcwd()
    yaml_data = parser_Yaml(os.path.join(current_folder, yaml_path))
    if not yaml_data:
        return
    path = "./QAPokerMockClient/accounts.csv"
    robot_login_list ={}
    with open(path, 'r') as file:
        csvReader = csv.reader(file)
        listReport = list(csvReader)
    print(listReport)
    for i,v in enumerate(listReport):
        if i == 500:
            break