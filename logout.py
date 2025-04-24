import asyncio
import json
import logging
import websockets
from core import parser_Yaml
from utils import encodePassword
import csv

logging.basicConfig(level=logging.INFO)

async def send_and_receive(websocket, msg):
    try:
        await websocket.send(json.dumps(msg))
        res = await asyncio.wait_for(websocket.recv(), timeout=180)
        return json.loads(res)
    except Exception as e:
        logging.error(f"[SEND/RECV] 失敗: {e}", exc_info=True)
        return None

async def robot_quit(account, uri):
    try:
        async with websockets.connect(uri, ping_interval=None,ping_timeout=180) as ws:
            logging.info(f"🟢 連線成功 - {account[0]}")

            login_msg = {
                "msgId": 201,
                "msgBody": json.dumps({
                    "userName": account[0],
                    "password": account[1],
                    "imei": "",
                    "model": "",
                    "channel": "德州",
                    "channelInt": 100,
                    "version": "1.10.11.2",
                    "jingDu": 25.0360047,
                    "weiDu": 121.5749637,
                    "language": 2,
                    "verify": 1
                })
            }
            roomid = {
                "gameType": 800,
                "gameId": 1282357,
                "ChangeDesk": False,
                "is213Broadable": False,
                "isCoinQuick": True,
                "coinQuickLevel": 744
            }
            res = await send_and_receive(ws, login_msg)
            if res and res.get("msgId") == 201:
                reason = json.loads(res["msgBody"]).get("reason")
                logging.info(f"登入成功: {account[0]} - {reason}")
                res_1 = await send_and_receive( ws, {"msgId": 207, "msgBody": json.dumps(roomid)} )
                # logging.info(f"{account[0]} 進入房間 {res_1}")
                # 執行站起 (MsgId 214)
                res_2 = await send_and_receive(ws, {"msgId": 214, "msgBody": json.dumps({})})
                logging.info(f"{account[0]} 已退出牌桌 {res_2}")
                res_3 = await send_and_receive(ws, {"msgId": 209, "msgBody": json.dumps({})})
                logging.info(f"{account[0]} 已離開房間 {res_3}")
            else:
                logging.warning(f"登入失敗: {account[0]}")

    except Exception as e:
        logging.error(f"連線錯誤 - {account[0]} : {e}", exc_info=True)

async def main():
    robot_data = parser_Yaml("./data/NLH_robotData.yaml")
    uri = robot_data.get("url", "wss://web.qosuat.com/ws/")
    path = "./QAPokerMockClient/accounts.csv"
    robot_login_list ={}
    with open(path, 'r') as file:
        csvReader = csv.reader(file)
        listReport = list(csvReader)
    tasks = []
    for i, v in enumerate(listReport[1000:1200]):
        if i == 300:
            break
        # tasks.append(robot_quit(v, uri))
        await robot_quit(v, uri)
    # await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🔴 使用者手動中止")
    except Exception as e:
        logging.error(f"主程序錯誤: {e}", exc_info=True)
