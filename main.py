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

#  Setting: logging style

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s ",
    datefmt="%Y-%m-%d %H:%M:%S",
    )

#  "./QAPokerMockClient/accounts.csv"

async def main(yaml_path):
    logging.info("Starting poker bot...")
    current_folder = os.getcwd()
    yaml_data = parser_Yaml(os.path.join(current_folder, yaml_path))
    if not args.yaml:
        return

    with open("./accounts.csv", 'r') as file:
        csvReader = csv.reader(file)
        robotlist = list(csvReader)

    tasks = []
    robot = robotlist[:int(args.gangbang)]
    # logging.info(robot)
    for i, logindata in enumerate(robot):
        logging.info(f"[QUEUE] 第{i+1}位機器人")
        await asyncio.sleep(0.5)
        tasks.append(asyncio.create_task(robot_login(logindata, yaml_data)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", required=True, help="測試路徑")
    parser.add_argument("--gangbang", required=True, help="測試路徑")
    args = parser.parse_args()
    
    try:
        logging.info("補齊登入case的pattern")
        asyncio.run(main(args.yaml))
    except KeyboardInterrupt:
        logging.info("Poker robot stopped by CTRL+C")
    except Exception as e:
        logging.error(f"Main錯誤: {str(e)}", exc_info=True)