import asyncio
import argparse
import logging
import os
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
    
    robot_login_list = yaml_data['loginData']
    for i in robot_login_list:
        i["PW"] = encodePassword(i.get("Acc"), i.get("PW"))
    # tasks = [robot_login(robot_account, yaml_data) for robot_account in robot_login_list]

    tasks = []
    for i, account in enumerate(robot_login_list):
        await asyncio.sleep(0.5)  # 每個帳號相隔 0.5 秒啟動
        tasks.append(asyncio.create_task(robot_login(account, yaml_data)))


    await asyncio.gather(*tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", required=True, help="測試路徑")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args.yaml))
    except KeyboardInterrupt:
        logging.info("Poker robot stopped by CTRL+C")
    except Exception as e:
        logging.error(f"Main錯誤: {str(e)}", exc_info=True)