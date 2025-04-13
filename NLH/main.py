from core import (
    parser_Yaml,
    rebot_login
    )
from utils import encodePassword
import asyncio
import logging







async def main():
    logging.info("Starting poker bot...")
    robot_data = parser_Yaml("./data/robotData.yaml")
    robot_login_list = robot_data['RobotData']['login']

    for i in robot_login_list:
        i["PW"] = encodePassword(i.get("Acc", "+852 0922"),i.get("PW", "aaaa1234"))

    tasks = [rebot_login(account) for account in robot_login_list]    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Poker bot stopped by user")
    except Exception as e:
        logging.error(f"Main error: {str(e)}", exc_info=True)
