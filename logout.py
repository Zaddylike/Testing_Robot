from core import (
    parser_Yaml
    )
from utils import encodePassword
import asyncio
import logging
import websockets
import json

async def robot_in_and_out(account):
    uri = "wss://web-pp2.pkxxz.com/ws/"
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            async with websockets.connect(
                uri,
                ping_interval=None,
                ping_timeout=10,
                close_timeout=10,
                max_size=2**20
            ) as websocket:
                logging.info(f"WebSocket Connected - Account {account['Acc']}")
                
                # 登入請求
                login_request = {
                    "msgId": 201,
                    "msgBody": json.dumps({
                        "userName": account["Acc"],
                        "password": account["PW"],
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
                logging.info(f"SEND - MsgId 201: { account['Acc'] } ")

                try:
                    await asyncio.wait_for(
                        websocket.send(json.dumps(login_request)),
                        timeout=5
                    )
                    
                    login_recv = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5
                    )
                    login_response = json.loads(login_recv)
                    recv_body = json.loads(login_response.get('msgBody'))
                    logging.info(f"RECV - MsgId {login_response.get('msgId')}: {recv_body.get('reason')}")
                    
                    if isinstance(login_response, dict):
                        login_msg_id = login_response.get('msgId')
                        login_msg_body = json.loads(login_response.get('msgBody', '{}'))

                        if login_msg_id == 201:
                            userid = login_msg_body['userId']
                            logging.info(f"Player {userid} - Login successful")
                            seatup_request = {
                                "msgId": 214,
                                "msgBody": json.dumps({})
                            }
                            await websocket.send(json.dumps(seatup_request))
                            logging.info("已退出所設定之測試帳號")
                            break
                
                except asyncio.TimeoutError:
                    logging.error(f"Timeout - Operation timeout for account {account['Acc']}")
                    retry_count += 1
                    await asyncio.sleep(2)
                    continue
                    
        except Exception as e:
            logging.error(f"Connection Error - Account {account['Acc']}: {str(e)}", exc_info=True)
            retry_count += 1
            await asyncio.sleep(2)
            continue

    if retry_count >= max_retries:
        logging.error(f"Max Retries - Failed after {max_retries} attempts for account {account['Acc']}")


async def main():
    logging.info("Starting poker bot...")
    robot_data = parser_Yaml("./data/NLH_robotData.yaml")
    robot_login_list = robot_data['loginData']
    for i in robot_login_list:
        i["PW"] = encodePassword(i.get("Acc", "+852 0922"),i.get("PW", "aaaa1234"))

    tasks = [robot_in_and_out(account) for account in robot_login_list]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    logging.info("已退出所設定之測試帳號")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Poker bot stopped by user")
    except Exception as e:
        logging.error(f"Main error: {str(e)}", exc_info=True)