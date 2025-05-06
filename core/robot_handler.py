import websockets
import logging
import json
import asyncio
import random
import copy
MSG_Handlerlist = {}
notplayAction_Handler = {}
user_points = {}
seat_lock = asyncio.Lock()


# msg回傳底牌轉換成數字，需優畫

def convert_card_readable(card_numbers):
    def filter_Cardtype(num):
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
            
    handcard_Log = []
    handcard_Suits = []
    handcard_Points = []
    handcard_Changemap = {'A':14, 'K':13, 'Q':12, 'J':11}
    try:
        for card in card_numbers:
            suit, point = filter_Cardtype(card)
            handcard_Suits.append(suit)
            if point in handcard_Changemap:
                handcard_Points.append(handcard_Changemap[point])
            else:
                handcard_Points.append(int(point))
            handcard_Log.append(f"{suit} {point}")
        sorted_Cards = sorted(zip(handcard_Points, handcard_Log, handcard_Suits), reverse = True)
        handcard_Points, handcard_Log, handcard_Suits = zip(*sorted_Cards)
        return list(handcard_Points), list(handcard_Log), list(handcard_Suits)
    except Exception as e:
        logging.info(f"[ERROR] 解析底牌: {e}")
        return [], [], []

# 機器人操作決策， 未來會想訓練model來判斷，目前就先簡單判斷

async def decide_robot_action(points, msg_body):
    # 跟注所需金額
    call_count = msg_body.get("callCount")
    # 加注所需金額
    raise_count = msg_body.get("raisCount")
    # 還沒調查
    min_raise = msg_body.get("minRaise")
    # 還沒調查
    min_call = msg_body.get("minCall")
    
    # action rule => {1:"弃牌", 2:"让牌", 3:"跟注", 4:"加注", 5:"全下", 6:"延时"}
    # AK, AQ, AJ, A10, KQ, KJ, K10, QJ, Q10, J10 or AA, KK, QQ, JJ, 1010
    if min_call == 0:
        if random.random() < 0.69:
            return 2, 0
        else:
            return 4, raise_count*2
    #強牌系列
    if (points[0]>=10 and points[1]>=10) or (points[0]==points[1] and points[0] >= 10):
        if random.random() < 0.78:
            return 4, raise_count*3
        else:
            return 4, raise_count*2
    #強牌系列
    if (points[0]>=10 and points[1]>=10):
        if random.random() < 0.69:
            return 3, call_count*2
        else:
            return 3, call_count

    # 55, 66, 77, 88, 99
    elif (points[0]==points[1]) and (5 <= points[0] < 10) and ((points[0]>=10)):
        return 3, call_count
    # 44, 33, 22
    elif (points[0]==points[1]) and (2 <= points[0] < 5):
        if random.random() < 0.5:
            return 3, call_count
        else:
            return 1, 0
    # 98, 87, 76, 65, 54, 43, 32 
    elif points[0]<10 and (points[0]-points[1]) < 1:
        if random.random() < 0.5:
            return 3, call_count
        else:
            return 1, 0
    # 弱到直接棄牌下一局
    else:
        return 1, 0


# match&case維護成本過高， 參考decorator寫法

def register_handler(msg_id):
    def wrapper(func):
        MSG_Handlerlist[msg_id] = func
        return func
    return wrapper

# 手牌資訊&心跳
@register_handler(913)
async def handle_913(websocket, msg_body, user_id, shared_data):
    try:
        if isinstance(msg_body, list) and len(msg_body) > 0:
            for table in msg_body:
                cards = table.get('cards', [])
                if cards:
                    points, card_readable, suits = convert_card_readable(cards)
                    user_points[user_id] = points
                    logging.info(f"Robot {shared_data.get(user_id, user_id)} , 手牌: {card_readable}")
        else:
            raise Exception(f"[ERROR] 玩家沒拿到2張牌阿!! ")
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 913: {e}", exc_info=True)
        # send heart-beat
    try:
        heartbeat_request = {
            "msgId": 202,
            "msgBody": json.dumps({})
            }
        await websocket.send(json.dumps(heartbeat_request))
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 202: {e}", exc_info=True)
    await asyncio.sleep(0.1)
# NLH, MTT 手牌操作
@register_handler(217)
async def handle_217(websocket, msg_body, user_id, shared_data):
    try:
        #牌力邏輯
        #1003093 1003091 1003088 1003082
        if msg_body.get('userId') == user_id:
            points = user_points.get(user_id)
            if not points or len(points) < 2:
                logging.warning(f"Robot:{user_id} 還沒到拿牌階段:{points} ， 跳過。")
                return
            
            # 每次操作的id流水
            cmd_id = msg_body.get('commandId')
            actionType, score= await decide_robot_action(points, msg_body)

            action = {
                "gameOpType": actionType,
                "score": score,
                "commandId": cmd_id
            }
            msg = msgbody_build(218, action)

            sleep_time = random.uniform(1, 2)  # 隨機等待1-3秒
            await asyncio.sleep(sleep_time)

            await websocket.send(json.dumps(msg))

            action_Map = {1:"弃牌", 2:"让牌", 3:"跟注", 4:"加注", 5:"全下", 6:"延时"}
            logging.info(f"Robot:{user_id} 的行動: {action_Map.get(action["gameOpType"], "無動作")}")
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 217: {e}", exc_info=True)
# 公共牌
@register_handler(219)
async def handle_219(websocket, msg_body, user_id, shared_data):
    try:
        center_cards = msg_body.get('centerCard', [])
        if center_cards:
            community_cards = convert_card_readable(center_cards)
            logging.info(f"[Observe] 公共牌: {community_cards}")
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 219: {e}", exc_info=True)
# 
@register_handler(221)
async def handle_221(websocket, msg_body, user_id, shared_data):
    try:
        winners = msg_body.get('winners', [])
        for winner in winners:
            win_userid = winner.get('userId')
            win_amount = winner.get('winScore', 0)
            logging.info(f"[Observe] Robot:{win_userid} 贏得 {win_amount} 籌碼")
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 221: {e}", exc_info=True)
#
@register_handler(216)
async def handle_216(websocket, msg_body, user_id, shared_data):
    try:
        # 公共牌信息
        community_cards = msg_body.get('publicCards', [])
        if community_cards:
            logging.info(f"[Observe] 公共牌: {community_cards}")
        
        # 當前池底
        pot = msg_body.get('pot', 0)
        if pot:
            logging.info(f"[Observe] 當前池底: {pot}")
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 216: {e}", exc_info=True)
#
@register_handler(220)
async def handle_220(websocket, msg_body, user_id, shared_data):
    try:
        winners = msg_body.get('winners', [])
        for winner in winners:
            player_id = winner.get('userId')
            win_amount = winner.get('winMoney', 0)
            cards = winner.get('cards', [])
            card_type = winner.get('cardType', '')
            logging.info(f"[Observe] Robot:{player_id} 贏得 {win_amount}，手牌: {cards}，牌型: {card_type}")
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 220: {e}", exc_info=True)
#
@register_handler(218)
async def handle_218(websocket, msg_body, user_id, shared_data):
    try:
        player_id = msg_body.get('userId')
        action = msg_body.get('action', {})
        bet_amount = action.get('bet', 0)
        if bet_amount:
            logging.info(f"[Observe] Robot:{player_id} 下注金額: {bet_amount}")
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 218: {e}", exc_info=True)
#Rebuy
@register_handler(279)
async def handle_279(websocket, msg_body, user_id, shared_data):
    try:
        rebuy_request = {
            "msgId": 210,
            "msgBody": json.dumps(
                    {
                    "take": 888,
                    "usePlatformCoins": 1,
                    "reason": "normal"
                    }
                )
            }
        await websocket.send(json.dumps(rebuy_request))
    except Exception as e:
        logging.warning(f"[ERROR] MsgId 218: {e}", exc_info=True)
#get user name
@register_handler(213)
async def handle_213(websocket, msg_body, user_id, shared_data):
    display_user = shared_data.get(user_id, None)

    if not display_user:
        shared_data[user_id]=msg_body.get('userInfo').get('nickname')

#  add params for shared

def add_shared_params(case_params: dict, shared_data: dict):
    try:
        for k, v in case_params['body'].items():
            if isinstance(v, str) and v.startswith('$'):
                var_name = v[1:]
                if var_name in shared_data:
                    case_params['body'][k] = shared_data[var_name]
                    # logging.info(f"[共享參數]:{shared_data}")
        return case_params
    except Exception as e:
        logging.warning(f"[WARNING] 新增共享參數ERROR:{e}")

def register_NotPlay_handler(msg_id):
    def wrapper(func):
        notplayAction_Handler[msg_id] = func
        return func
    return wrapper

@register_NotPlay_handler(201)
async def handle_201(websocket, body, expect, retry, shared_data):
    state, reps = await sendmsg_handler(websocket, 201, body, expect, retry)
    if state:
        shared_data["user_id"] = reps.get("userId")
        logging.info(f"{shared_data["user_id"]} 已成功登入!!")
    return state, reps

@register_NotPlay_handler(208)
async def handle_208(websocket, body, expect, retry, shared_data):
    async with seat_lock:
        for pos in range(8):
            body["pos"] = pos if "pos" in body else pos
            state, reps = await sendmsg_handler(websocket, 208, body, expect, retry)

            if state and reps.get("reason") == "success！":
                logging.info(f" {shared_data['user_id']} [入座成功] MsgId: {208}, Pos: {pos}")
                break
            await asyncio.sleep(0.3)

        return state, reps

@register_NotPlay_handler(2102)
async def handle_2102(websocket, body, expect, retry, shared_data):
    for pos in range(8):
        body["pos"] = pos if "pos" in body else pos
        logging.info(f" {shared_data["user_id"]} 嘗試坐下 {pos}")
        state, reps = await sendmsg_handler(websocket, 2102, body, expect, retry)

        if state and reps.get("reason") == "success！":
            logging.info(f" {shared_data['user_id']} [入座成功] MsgId: {2102}, Pos: {pos}")
            break
        await asyncio.sleep(0.3)

    return state, reps

# 工廠化所有機器人的各種操作函式，日後好維護

async def robot_play(websocket, user_id, shared_data):
    while True:
        try:
            reps = await websocket.recv()
            jsonify_Reps = json.loads(reps)
            msg_id = jsonify_Reps.get("msgId")
            msg_body = json.loads(jsonify_Reps.get('msgBody', '{}'))
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                pong = await websocket.ping()
                await asyncio.wait_for(pong, timeout=5)
                logging.debug('Ping OK, keeping connection alive...')
                continue
        except Exception as e:
            logging.error(f"機器人解析RECV時遇到ERROR:{e}")
            await asyncio.sleep(3)
        handler_Action = MSG_Handlerlist.get(msg_id, None)
        if handler_Action:
            await handler_Action(websocket, msg_body, user_id, shared_data)
        else:
            logging.debug(f"[DEBUG] 未處理過的 MsgId: {msg_id}")

# 簡化登入到買入流程   

async def connect_ws_retry(url, retries:int =5):
    for i in range(retries):
        try:
            return await websockets.connect(
                url,
                ping_interval=None,
                open_timeout=10,

            )
        except websockets.exceptions.ConnectionClosedError as wsconnecterror:
            logging.warning(f"Fail to connect, retry {i+1}{retries}, Error: {wsconnecterror}")
        except Exception as e:
            logging.warning(f"Fail to connect, Retry {i+1}{retries}, Error: {e}")

#  

async def robot_login(account, yamlData):
    url = yamlData.get('url', 'wss://web-pp2.pkxxz.com/ws/')
    cases = yamlData.get("cases", [])
    play = yamlData.get('play', False)
    shared_data = {}
    while True:
        try:
            ws = await connect_ws_retry(url, 3)
            async with ws:
                for i,case in enumerate(cases):
                    params = case.get('params')
                    expect = case.get('expect', None)
                    msg_id = params.get('msgid', 0)
                    body = params.get('body', {})
                    retry = params.get('retry', True)
                    keep = params.get('keep', "")

                    if msg_id == 201:
                        body["userName"], body["password"] = account[0], account[1]

                    # 因為是用一個檔案去跑多執行緒，帳密都要換
                    handler_Action = notplayAction_Handler.get(msg_id, None)
                    if handler_Action:
                        state, reps = await handler_Action(ws, body, expect, retry, shared_data)
                    else:
                        state, reps = await sendmsg_handler(ws, msg_id, body, expect, retry)

                    # 替換 game_id
                    if "gameId" in body and shared_data.get("game_id") and body['gameId'] == "":
                        body["gameId"] = shared_data["game_id"]

                    if state and keep:
                        if isinstance(reps, dict) and (keep in reps):
                            shared_data[keep] = reps[keep]

                    if state and msg_id == 201:
                        try:
                            shared_data["user_id"] = reps.get("userId")
                        except Exception as e:
                            logging.info(e)
                # raise ValueError("就是要錯啦")
                if play and "user_id" in shared_data:
                    logging.info(f"進入牌桌前所儲存的shared_data: {shared_data}")
                    await robot_play(ws, shared_data["user_id"], shared_data)
                else:
                    await ws.close()
                    logging.info(f"CASE任務完成 遊玩模式: {play}")
                    break
        except websockets.exceptions.ConnectionClosedError as wsconnecterror:
            logging.warning(f"Fail to connect, retry to connect, Error: {wsconnecterror}")
            await asyncio.sleep(3)
            continue
        except Exception as e:
            logging.warning(f"Reconnect...:{e}",exc_info=True)
            await asyncio.sleep(3)
            continue

# 將yaml的格式轉換成發送web socket api的format

def msgbody_build(msg_id: int, msg_body: str) -> str:
    return {
        "msgId": msg_id,
        "msgbody": json.dumps(msg_body)
    }

# 執行websocket的api發送，分為單次跟Retry

async def sendmsg_handler(
        websocket, msg_id: int, msg_body: str,
        msg_expect=None,
        retry=True,
        timeout=20,
        ):
        msg = msgbody_build(msg_id, msg_body)
        await websocket.send(json.dumps(msg))
        tys = 0
        while tys <= retry:
            try:
                reps = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                jsonify_Reps = json.loads(reps)

                reps_Msgid = jsonify_Reps.get("msgId", 0)
                reps_Msgbody = json.loads(jsonify_Reps.get("msgBody", "{}"))

                if msg_expect == None or (reps_Msgid == msg_expect[0] and msg_expect[1] in reps_Msgbody.get('reason', '')):
                    logging.info(f"[RECV] MsgId: {reps_Msgid} {reps_Msgbody['reason']}")
                    return True, reps_Msgbody
                if not retry:
                    return False, None
            except Exception as e:
                logging.error(f"[Error] Failed to receive/parse websocket message: {e}", exc_info=True)        
                tys+=1


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