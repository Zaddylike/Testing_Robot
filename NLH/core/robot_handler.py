import websockets
import logging
import json
import asyncio

async def robot_login(account):
    uri = "wss://web.qosuat.com/ws/"
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
                            await handle_game_operations(websocket, userid)
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
