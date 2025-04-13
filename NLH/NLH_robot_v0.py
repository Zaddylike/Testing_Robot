import asyncio
import websockets
import json
import time
import random
import logging
import base64
from datetime import datetime

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s ",
    datefmt="%Y-%m-%d %H:%M:%S",
    )

def convert_cards_to_readable(card_numbers):
    def get_card_info(num):
        # 方塊 2-A: 2-14
        if 2 <= num <= 14:
            rank = num if num <= 10 else {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}[num]
            return '♦', str(rank)
        # 梅花 2-A: 18-30
        elif 18 <= num <= 30:
            rank = num - 16 if num <= 26 else {27: 'J', 28: 'Q', 29: 'K', 30: 'A'}[num]
            return '♣', str(rank)
        # 紅心 2-A: 34-46
        elif 34 <= num <= 46:
            rank = num - 32 if num <= 42 else {43: 'J', 44: 'Q', 45: 'K', 46: 'A'}[num]
            return '♥', str(rank)
        # 黑桃 2-A: 50-62
        elif 50 <= num <= 62:
            rank = num - 48 if num <= 58 else {59: 'J', 60: 'Q', 61: 'K', 62: 'A'}[num]
            return '♠', str(rank)
        else:
            return '?', str(num)

    readable_cards = []
    for card in card_numbers:
        suit, rank = get_card_info(card)
        readable_cards.append(f"{suit}_{rank}")

    return readable_cards
#
def convert_card_type(type_number):
    card_types = {
        1: "High Card",
        2: "One Pair",
        3: "Two Pair",
        4: "Three of a Kind",
        5: "Straight",
        6: "Flush",
        7: "Full House",
        8: "Four of a Kind",
        9: "Straight Flush",
        10: "Royal Flush"
    }
    return card_types.get(type_number, "Unknown")

async def login_and_play(account):
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

async def handle_game_operations(websocket, userid):
    try:
        # 入桌請求
        table_request = {
            "msgId": 207,
            "msgBody": json.dumps({
                "gameType": 800,
                "gameId": 1282300,
                "ChangeDesk": False,
                "is213Broadable": False,
                "isCoinQuick": True,
                "coinQuickLevel": 176
            })
        }
        await websocket.send(json.dumps(table_request))
        # 嘗試所有座位
        for pos in range(8):
            getseat_request = {
                "msgId": 208,
                "msgBody": json.dumps({"pos": pos})
            }
            await websocket.send(json.dumps(getseat_request))
        # 買入請求
        buyin_request = {
            "msgId": 210,
            "msgBody": json.dumps({
                "take": 200,
                "usePlatformCoins": 1,
                "reason": "normal"
            })
        }
        await websocket.send(json.dumps(buyin_request))

        # 遊戲循環
        while True:
            try:
                message = await websocket.recv()
                msg = json.loads(message)
                msg_id = msg.get('msgId')

                if isinstance(msg, dict):
                    msg_body = json.loads(msg.get('msgBody', '{}'))
                    # 只記錄重要的遊戲信息
                    # 1. 手牌信息
                    if msg_id == 913:
                        if isinstance(msg_body, list) and len(msg_body) > 0:
                            cards = msg_body[0].get('cards', [])
                            if cards:
                                hand_cards = convert_cards_to_readable(cards)
                                logging.info(f">>> Player {userid} 的手牌是: {hand_cards}")
                        # send heart-beat
                        heartbeat_request = {
                            "msgId": 202,
                            "msgBody": json.dumps({})
                            }
                        await websocket.send(json.dumps(heartbeat_request))
                        # if msg_id == 202:
                        #     await asyncio.sleep(0.5)
                    # 2. 公共牌信息
                    elif msg_id == 219:
                        center_cards = msg_body.get('centerCard', [])
                        if center_cards:
                            community_cards = convert_cards_to_readable(center_cards)
                            logging.info(f">>> 公共牌: {community_cards}")
                    
                    # 3. 遊戲結果
                    elif msg_id == 220:  # 假設220是結算消���
                        winners = msg_body.get('winners', [])
                        for winner in winners:
                            win_userid = winner.get('userId')
                            win_amount = winner.get('winScore', 0)
                            logging.info(f">>> Player {win_userid} 贏得 {win_amount} 籌碼")
                    
                    # 4. 
                    elif msg_id == 217 and msg_body.get('userId') == userid:
                        cmd_id = msg_body.get('commandId', 0)
                        call_count = msg_body.get("callCount", 0)
                        raise_count = msg_body.get("raisCount", 0)
                        min_raise = msg_body.get("minRaise", 0)
                        fold_ = msg_body.get("fold",0)

                        suits = []
                        points = []
                        point_changeMap = {"A":14, "K":13, "Q":12, "J":11}
                        try:
                            for i in hand_cards:
                                suit, point = i.split('_')
                                suits.append(suit)
                                if point in point_changeMap:
                                    points.append(point_changeMap.get(point))
                                else:
                                    points.append(int(point))
                        except Exception as e:
                            logging.info(f"目前尚未拿到手牌訊息: {e}")

                        if points[0]>=11:
                            actionType = 4
                        elif points[0]==points[1] and points[0] >= 10:
                            actionType = 4
                        elif points[0]==points[1] and points[0] >=4:
                            actionType = 4
                        elif points[0]>7 and (points[0]-points[1]) < 2:
                            actionType = 2
                        else:
                            actionType = 1

                        #一直raise會太快打光
                        if raise_count>5:
                            actionType = 3

                        if actionType == 1:  
                            score = 0
                        elif actionType == 2:  
                            score = 0
                        elif actionType == 3:  
                            score = call_count
                        elif actionType == 4: 
                            score = raise_count

                        action_Map = {1:"弃牌", 2:"让牌", 3:"跟注", 4:"加注", 5:"全下", 6:"延时"}
                        # 玩家動作  操作：1 弃牌 2 让牌 3 跟注 4 加注 5 全下：6延时  {"msgId":218,"msgBody":"{\"gameOpType\":2,\"score\":0,\"commandId\":140}"}
                        action = {
                            "gameOpType": actionType,
                            "score": score,
                            "commandId": cmd_id
                        }
                        bet_request = {
                            "msgId": 218,
                            "msgBody": json.dumps(action)
                        }
                        #Json -> dict

                        sleep_time = random.uniform(1, 2)  # 隨機等待1-3秒
                        time.sleep(sleep_time)
                        actName = action_Map.get(action["gameOpType"], "無動作")
                        logging.info(f">>> Player {userid} 的行動: {actName}")
                        await websocket.send(json.dumps(bet_request))
                        await asyncio.sleep(0.5)
                    # 遊戲狀態更新
                    elif msg_id == 216:
                        # 公共牌信息
                        community_cards = msg_body.get('publicCards', [])
                        if community_cards:
                            logging.info(f">>> 公共牌: {community_cards}")
                        
                        # 當前池底
                        pot = msg_body.get('pot', 0)
                        if pot:
                            logging.info(f">>> 當前池底: {pot}")
                            
                    # 遊戲結果
                    elif msg_id == 219:
                        winners = msg_body.get('winners', [])
                        for winner in winners:
                            player_id = winner.get('userId')
                            win_amount = winner.get('winMoney', 0)
                            cards = winner.get('cards', [])
                            card_type = winner.get('cardType', '')
                            logging.info(f">>> 玩家 {player_id} 贏得 {win_amount}，手牌: {cards}，牌型: {card_type}")
                            
                    # 玩家行動結果
                    elif msg_id == 218:
                        player_id = msg_body.get('userId')
                        action = msg_body.get('action', {})
                        bet_amount = action.get('bet', 0)
                        if bet_amount:
                            logging.info(f">>> 玩家 {player_id} 下注金額: {bet_amount}")

            except Exception as e:
                logging.error(f"Game Loop Error: {str(e)}", exc_info=True)
                break       
    except Exception as e:
        logging.error(f"Game Operation Error: {str(e)}", exc_info=True)

def encodePassword(user_id: str, password: str) -> str:
    validate_code = "qazwsx"
    encode_step1 = base64.b64encode(password.encode()).decode()
    encode_step2 = base64.b64encode((encode_step1 + user_id).encode()).decode()

    encode_final = base64.b64encode((encode_step2 + validate_code).encode()).decode()
    return encode_final

async def main():
    logging.info("Starting poker bot...")

    userData = [
        {"Acc":"+852 0911223344556", "PW":"aaaa1234"},
        {"Acc":"+852 091122334455", "PW":"aaaa1234"},
        {"Acc":"+852 0922", "PW":"aaaa1234"},
        ]
    for i in userData:
        i["PW"] = encodePassword(i.get("Acc", "+852 0922"),i.get("PW", "aaaa1234"))
        
    if userData:
        tasks = [login_and_play(account) for account in userData]
        await asyncio.gather(*tasks)
    else:
        logging.error("No accounts loaded, exiting...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Poker bot stopped by user")
    except Exception as e:
        logging.error(f"Main error: {str(e)}", exc_info=True)
