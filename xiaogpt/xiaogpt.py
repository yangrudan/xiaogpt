#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import functools
import json
import logging
import re
import time
from pathlib import Path
from typing import AsyncIterator

from aiohttp import ClientSession, ClientTimeout
from miservice import MiAccount, MiIOService, MiNAService, miio_command
from rich import print
from rich.logging import RichHandler

from xiaogpt.bot import get_bot
from xiaogpt.config import (
    COOKIE_TEMPLATE,
    LATEST_ASK_API,
    MI_ASK_SIMULATE_DATA,
    WAKEUP_KEYWORD,
    Config,
)
from xiaogpt.tts import TTS, MiTTS, TetosFileTTS
from xiaogpt.tts.live import TetosLiveTTS
from xiaogpt.utils import detect_language, parse_cookie_string

EOF = object()


class MiGPT:
    def __init__(self, config: Config):
        self.config = config

        self.mi_token_home = Path.home() / ".mi.token"
        self.last_timestamp = int(time.time() * 1000)  # timestamp last call mi speaker
        self.cookie_jar = None
        self.device_id = ""
        self.mina_service = None
        self.miio_service = None
        self.in_conversation = False
        self.polling_event = asyncio.Event()
        self.last_record = asyncio.Queue(1)
        # setup logger
        self.log = logging.getLogger("xiaogpt")
        self.log.setLevel(logging.DEBUG if config.verbose else logging.INFO)
        self.log.addHandler(RichHandler())
        self.log.debug(config)
        self.mi_session = ClientSession()
        
        # MoCA test tracking
        self.in_moca_test = False
        self.moca_chat_history = []
        self.moca_session_start_time = None

    async def close(self):
        await self.mi_session.close()
    
    def _save_moca_history(self):
        """Save MoCA chat history to a local JSON file"""
        if not self.config.enable_moca_test or not self.moca_chat_history:
            self.log.debug("跳过MoCA历史保存：测试未启用或无对话历史")
            return
        
        self.log.info("开始保存MoCA测试历史...")
        # Create history directory if it doesn't exist
        history_dir = Path(self.config.moca_history_dir)
        history_dir.mkdir(exist_ok=True)
        self.log.debug(f"确认历史目录存在: {history_dir}")
        
        # Generate filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = history_dir / f"moca_test_{timestamp}.json"
        
        # Prepare data to save
        session_data = {
            "session_start_time": self.moca_session_start_time,
            "session_end_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_type": "MoCA阿兹海默症认知评估",
            "trigger_keyword": self.config.moca_test_keyword,
            "conversation_history": self.moca_chat_history,
            "total_exchanges": len(self.moca_chat_history),
            "assessment_note": "专业评估结果和得分应由医疗专业人员根据对话内容进行评定。此记录仅供参考，不作为诊断依据。"
        }
        
        # Save to file
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            self.log.info(f"MoCA测试历史保存成功: {filename} (共{len(self.moca_chat_history)}条对话)")
            print(f"[green]MoCA测试历史已保存到: {filename}[/]")
        except Exception as e:
            self.log.error(f"保存MoCA测试历史失败: {str(e)}")
            print(f"[red]保存MoCA测试历史失败: {str(e)}[/]")
    
    def _start_moca_test(self):
        """Start a new MoCA test session"""
        self.in_moca_test = True
        self.moca_chat_history = []
        self.moca_session_start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log.info(f"MoCA认知测试会话已开始 (开始时间: {self.moca_session_start_time})")
    
    def _end_moca_test(self):
        """End the current MoCA test session and save history"""
        if self.in_moca_test:
            self.log.info(f"结束MoCA认知测试会话 (共进行了{len(self.moca_chat_history)}轮对话)")
            self._save_moca_history()
            self.in_moca_test = False
            self.moca_chat_history = []
            self.moca_session_start_time = None
            self.log.info("MoCA认知测试会话状态已清理")
        else:
            self.log.debug("尝试结束MoCA测试，但当前未在测试状态")
    
    def _record_moca_exchange(self, query: str, response: str):
        """Record a question-answer exchange in MoCA test"""
        if self.in_moca_test:
            exchange = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "user_query": query,
                "bot_response": response
            }
            self.moca_chat_history.append(exchange)
            self.log.debug(f"记录MoCA对话 #{len(self.moca_chat_history)}: 用户='{query[:30]}...', 回答='{response[:30]}...'")
        else:
            self.log.warning("尝试记录MoCA对话，但当前未在MoCA测试状态")


    async def poll_latest_ask(self):
        self.log.info("启动小爱音箱消息轮询服务...")
        async with ClientSession() as session:
            session._cookie_jar = self.cookie_jar
            log_polling = int(self.config.verbose) >= 1
            poll_count = 0
            while True:
                poll_count += 1
                if log_polling:
                    self.log.debug(
                        "轮询新消息 #%d, 时间戳: %s", poll_count, self.last_timestamp
                    )
                new_record = await self.get_latest_ask_from_xiaoai(session)
                start = time.perf_counter()
                if log_polling:
                    self.log.debug(
                        "轮询事件等待, 时间戳: %s, 记录: %s",
                        self.last_timestamp,
                        new_record,
                    )
                await self.polling_event.wait()
                if (
                    self.config.mute_xiaoai
                    and new_record
                    and self.need_ask_gpt(new_record)
                ):
                    await self.stop_if_xiaoai_is_playing()
                if (d := time.perf_counter() - start) < 1:
                    # sleep to avoid too many request
                    if log_polling:
                        self.log.debug(
                            "防止过频请求，休眠 %f 秒, 时间戳: %s", 1-d, self.last_timestamp
                        )
                    # if you want force mute xiaoai, comment this line below.
                    await asyncio.sleep(1 - d)

    async def init_all_data(self):
        self.log.info("开始初始化系统数据...")
        await self.login_miboy()
        self.log.info("小米账号登录完成")
        await self._init_data_hardware()
        self.log.info("硬件设备初始化完成")
        self.mi_session.cookie_jar.update_cookies(self.get_cookie())
        self.cookie_jar = self.mi_session.cookie_jar
        self.log.info("Cookie配置完成")
        self.tts  # init tts
        self.log.info("TTS语音合成初始化完成")
        self.log.info("系统初始化完成，准备开始服务")

    async def login_miboy(self):
        self.log.debug("正在登录小米账号...")
        account = MiAccount(
            self.mi_session,
            self.config.account,
            self.config.password,
            str(self.mi_token_home),
        )
        # Forced login to refresh to refresh token
        self.log.debug(f"使用账号: {self.config.account}")
        await account.login("micoapi")
        self.log.debug("小米账号登录成功")
        self.mina_service = MiNAService(account)
        self.miio_service = MiIOService(account)
        self.log.debug("小米服务实例创建完成")

    async def _init_data_hardware(self):
        if self.config.cookie:
            # if use cookie do not need init
            self.log.debug("使用Cookie方式，跳过硬件初始化")
            return
        
        self.log.debug("开始获取硬件设备列表...")
        hardware_data = await self.mina_service.device_list()
        self.log.debug(f"获取到 {len(hardware_data)} 个设备")
        
        # fix multi xiaoai problems we check did first
        # why we use this way to fix?
        # some videos and articles already in the Internet
        # we do not want to change old way, so we check if miotDID in `env` first
        # to set device id

        for h in hardware_data:
            if did := self.config.mi_did:
                self.log.debug(f"查找指定DID设备: {did}")
                if h.get("miotDID", "") == str(did):
                    self.device_id = h.get("deviceID")
                    self.log.info(f"找到指定DID设备: {h.get('name', 'Unknown')}, ID: {self.device_id}")
                    break
                else:
                    continue
            if h.get("hardware", "") == self.config.hardware:
                self.device_id = h.get("deviceID")
                self.log.info(f"找到硬件设备: {h.get('name', 'Unknown')}, 型号: {self.config.hardware}, ID: {self.device_id}")
                break
        else:
            self.log.error(f"未找到硬件设备: {self.config.hardware}")
            raise Exception(
                f"we have no hardware: {self.config.hardware} please use `micli mina` to check"
            )
        if not self.config.mi_did:
            self.log.debug("开始获取设备DID...")
            devices = await self.miio_service.device_list()
            try:
                self.config.mi_did = next(
                    d["did"]
                    for d in devices
                    if d["model"].endswith(self.config.hardware.lower())
                )
                self.log.debug(f"获取到设备DID: {self.config.mi_did}")
            except StopIteration:
                self.log.error(f"无法找到硬件 {self.config.hardware} 对应的DID")
                raise Exception(
                    f"cannot find did for hardware: {self.config.hardware} "
                    "please set it via MI_DID env"
                )

    def get_cookie(self):
        if self.config.cookie:
            self.log.debug("使用配置的Cookie")
            cookie_jar = parse_cookie_string(self.config.cookie)
            # set attr from cookie fix #134
            cookie_dict = cookie_jar.get_dict()
            self.device_id = cookie_dict["deviceId"]
            self.log.debug(f"从Cookie获取设备ID: {self.device_id}")
            return cookie_jar
        else:
            self.log.debug("从token文件读取Cookie信息")
            with open(self.mi_token_home) as f:
                user_data = json.loads(f.read())
            user_id = user_data.get("userId")
            service_token = user_data.get("micoapi")[1]
            self.log.debug(f"用户ID: {user_id}")
            cookie_string = COOKIE_TEMPLATE.format(
                device_id=self.device_id, service_token=service_token, user_id=user_id
            )
            return parse_cookie_string(cookie_string)

    @functools.cached_property
    def chatbot(self):
        self.log.info(f"初始化 {self.config.bot} 聊天机器人...")
        bot = get_bot(self.config)
        self.log.info(f"{self.config.bot} 聊天机器人初始化完成")
        return bot

    async def simulate_xiaoai_question(self):
        data = MI_ASK_SIMULATE_DATA
        # Convert the data['data'] value from a string to a dictionary
        data_dict = json.loads(data["data"])
        # Get the first item in the records list
        record = data_dict["records"][0]
        # Replace the query and time values with user input
        record["query"] = input("Enter the new query: ")
        record["time"] = int(time.time() * 1000)
        # Convert the updated data_dict back to a string and update the data['data'] value
        data["data"] = json.dumps(data_dict)
        await asyncio.sleep(1)

        return data

    def need_ask_gpt(self, record):
        if not record:
            self.log.debug("无新记录，跳过GPT请求")
            return False
        query = record.get("query", "")
        should_ask = (
            self.in_conversation
            and not query.startswith(WAKEUP_KEYWORD)
            or query.lower().startswith(tuple(w.lower() for w in self.config.keyword))
        )
        if should_ask:
            self.log.debug(f"识别到有效查询: {query}")
        else:
            self.log.debug(f"跳过查询: {query} (不满足触发条件)")
        return should_ask

    def need_change_prompt(self, record):
        query = record.get("query", "")
        should_change = query.startswith(tuple(self.config.change_prompt_keyword))
        if should_change:
            self.log.info(f"检测到更改提示词请求: {query}")
        return should_change

    def _change_prompt(self, new_prompt):
        old_prompt = self.config.prompt
        new_prompt = re.sub(
            rf"^({'|'.join(self.config.change_prompt_keyword)})", "", new_prompt
        )
        new_prompt = "以下都" + new_prompt
        self.log.info(f"提示词从 '{old_prompt}' 更改为 '{new_prompt}'")
        print(f"Prompt from {old_prompt} change to {new_prompt}")
        self.config.prompt = new_prompt
        self.chatbot.change_prompt(new_prompt)

    async def get_latest_ask_from_xiaoai(self, session: ClientSession) -> dict | None:
        retries = 3
        for i in range(retries):
            try:
                timeout = ClientTimeout(total=15)
                r = await session.get(
                    LATEST_ASK_API.format(
                        hardware=self.config.hardware,
                        timestamp=str(int(time.time() * 1000)),
                    ),
                    timeout=timeout,
                )
                self.log.debug(f"成功获取小爱音箱API响应 (第{i+1}次尝试)")
            except Exception as e:
                self.log.warning(
                    "获取小爱音箱最新询问时发生异常 (第%d次尝试): %s", i+1, str(e)
                )
                continue
            try:
                data = await r.json()
                self.log.debug("成功解析API响应数据")
            except Exception:
                self.log.warning("解析小爱音箱API响应失败，重试中... (第%d次尝试)", i+1)
                if i == 1:
                    # tricky way to fix #282 #272 # if it is the third time we re init all data
                    self.log.warning("多次失败，尝试重新初始化连接")
                    print("Maybe outof date trying to re init it")
                    await self._retry()
            else:
                result = self._get_last_query(data)
                if result:
                    self.log.debug(f"获取到新的查询记录: {result.get('query', '')}")
                return result
        self.log.error("获取小爱音箱最新询问失败，已达到最大重试次数")
        return None

    async def _retry(self):
        self.log.info("开始重新初始化系统连接...")
        await self.init_all_data()
        self.log.info("系统连接重新初始化完成")

    def _get_last_query(self, data: dict) -> dict | None:
        if d := data.get("data"):
            records = json.loads(d).get("records")
            if not records:
                self.log.debug("API响应中无查询记录")
                return None
            last_record = records[0]
            timestamp = last_record.get("time")
            if timestamp > self.last_timestamp:
                try:
                    self.last_record.put_nowait(last_record)
                    self.last_timestamp = timestamp
                    query = last_record.get("query", "")
                    self.log.info(f"接收到新查询: '{query}' (时间戳: {timestamp})")
                    return last_record
                except asyncio.QueueFull:
                    self.log.warning("查询队列已满，跳过此查询")
                    pass
        return None

    async def do_tts(self, value):
        self.log.debug(f"开始TTS播放: {value[:50]}...")
        if not self.config.use_command:
            try:
                await self.mina_service.text_to_speech(self.device_id, value)
                self.log.debug("TTS播放成功 (mina_service)")
            except Exception as e:
                self.log.error(f"TTS播放失败 (mina_service): {str(e)}")
                pass
        else:
            try:
                await miio_command(
                    self.miio_service,
                    self.config.mi_did,
                    f"{self.config.tts_command} {value}",
                )
                self.log.debug("TTS播放成功 (miio_command)")
            except Exception as e:
                self.log.error(f"TTS播放失败 (miio_command): {str(e)}")

    @functools.cached_property
    def tts(self) -> TTS:
        self.log.debug(f"初始化TTS服务: {self.config.tts}")
        if self.config.tts == "mi":
            tts_instance = MiTTS(self.mina_service, self.device_id, self.config)
        elif self.config.tts == "fish":
            tts_instance = TetosLiveTTS(self.mina_service, self.device_id, self.config)
        else:
            tts_instance = TetosFileTTS(self.mina_service, self.device_id, self.config)
        self.log.info(f"TTS服务初始化完成: {self.config.tts}")
        return tts_instance

    async def wait_for_tts_finish(self):
        while True:
            if not await self.get_if_xiaoai_is_playing():
                break
            await asyncio.sleep(1)

    @staticmethod
    def _normalize(message: str) -> str:
        message = message.strip().replace(" ", "--")
        message = message.replace("\n", "，")
        message = message.replace('"', "，")
        message = message.replace("*", "")
        return message

    async def ask_gpt(self, query: str) -> AsyncIterator[str]:
        self.log.info(f"开始向{self.config.bot}发送查询: {query[:100]}...")
        if not self.config.stream:
            self.log.debug("使用非流式模式")
            if self.config.bot == "glm":
                answer = self.chatbot.ask(query, **self.config.gpt_options)
            else:
                answer = await self.chatbot.ask(query, **self.config.gpt_options)
            message = self._normalize(answer) if answer else ""
            if answer:
                self.log.info(f"收到{self.config.bot}回答: {message[:100]}...")
            else:
                self.log.warning(f"{self.config.bot}返回空回答")
            yield message
            return

        self.log.debug("使用流式模式")
        async def collect_stream(queue):
            try:
                async for message in self.chatbot.ask_stream(
                    query, **self.config.gpt_options
                ):
                    await queue.put(message)
                self.log.debug("流式响应收集完成")
            except Exception as e:
                self.log.error(f"流式响应收集异常: {str(e)}")
                raise

        def done_callback(future):
            queue.put_nowait(EOF)
            if future.exception():
                self.log.error(f"流式响应任务异常: {future.exception()}")

        self.polling_event.set()
        queue = asyncio.Queue()
        is_eof = False
        task = asyncio.create_task(collect_stream(queue))
        task.add_done_callback(done_callback)
        
        message_count = 0
        while True:
            if is_eof or not self.last_record.empty():
                break
            message = await queue.get()
            if message is EOF:
                break
            while not queue.empty():
                if (next_msg := queue.get_nowait()) is EOF:
                    is_eof = True
                    break
                message += next_msg
            if message:
                message_count += 1
                normalized_msg = self._normalize(message)
                if message_count == 1:
                    self.log.debug(f"开始流式输出: {normalized_msg[:50]}...")
                yield normalized_msg
        
        self.log.debug(f"流式响应完成，共输出 {message_count} 个消息块")
        self.polling_event.clear()
        task.cancel()

    async def get_if_xiaoai_is_playing(self):
        try:
            playing_info = await self.mina_service.player_get_status(self.device_id)
            # WTF xiaomi api
            is_playing = (
                json.loads(playing_info.get("data", {}).get("info", "{}")).get("status", -1)
                == 1
            )
            self.log.debug(f"小爱音箱播放状态: {'播放中' if is_playing else '未播放'}")
            return is_playing
        except Exception as e:
            self.log.error(f"获取小爱音箱播放状态失败: {str(e)}")
            return False

    async def stop_if_xiaoai_is_playing(self):
        is_playing = await self.get_if_xiaoai_is_playing()
        if is_playing:
            self.log.debug("检测到小爱音箱正在播放，执行静音操作")
            # stop it
            try:
                await self.mina_service.player_pause(self.device_id)
                self.log.debug("小爱音箱静音成功")
            except Exception as e:
                self.log.error(f"小爱音箱静音失败: {str(e)}")
        else:
            self.log.debug("小爱音箱未在播放，无需静音")

    async def wakeup_xiaoai(self):
        self.log.debug("唤醒小爱音箱")
        try:
            result = await miio_command(
                self.miio_service,
                self.config.mi_did,
                f"{self.config.wakeup_command} {WAKEUP_KEYWORD} 0",
            )
            self.log.debug("小爱音箱唤醒成功")
            return result
        except Exception as e:
            self.log.error(f"小爱音箱唤醒失败: {str(e)}")
            raise

    async def run_forever(self):
        self.log.info("启动XiaoGPT主服务...")
        await self.init_all_data()
        task = asyncio.create_task(self.poll_latest_ask())
        assert task is not None  # to keep the reference to task, do not remove this
        
        self.log.info("XiaoGPT服务启动完成，开始监听用户输入")
        print(
            f"Running xiaogpt now, 用 [green]{'/'.join(self.config.keyword)}[/] 开头来提问"
        )
        print(f"或用 [green]{self.config.start_conversation}[/] 开始持续对话")
        if self.config.enable_moca_test:
            print(f"或用 [green]{self.config.moca_test_keyword}[/] 开始MoCA认知测试")
        
        while True:
            self.polling_event.set()
            new_record = await self.last_record.get()
            self.polling_event.clear()  # stop polling when processing the question
            query = new_record.get("query", "").strip()
            
            self.log.info(f"处理用户查询: '{query}'")
            
            # Handle MoCA test keyword
            if self.config.enable_moca_test and query == self.config.moca_test_keyword:
                if not self.in_moca_test:
                    self.log.info("用户请求开始MoCA认知测试")
                    print("开始MoCA认知测试")
                    self._start_moca_test()
                    self.in_conversation = True
                    # Change prompt to MoCA test mode
                    self.chatbot.change_prompt(self.config.moca_test_prompt)
                    await self.stop_if_xiaoai_is_playing()
                    # Send initial MoCA greeting
                    await self.do_tts(f"正在启动MoCA认知评估，请耐心等待")
                    print("-" * 20)
                    print("问题：开始MoCA认知测试")
                    initial_query = "开始MoCA认知测试，请简短介绍并开始第一个问题。"
                    self.log.debug(f"发送MoCA测试初始查询: {initial_query}")
                    print(f"以下是 {self.chatbot.name} 的回答：", end="")
                    try:
                        await self.speak(self.ask_gpt(initial_query), initial_query)
                    except Exception as e:
                        print(f"{self.chatbot.name} 回答出错 {str(e)}")
                    else:
                        print("回答完毕")
                        print(f"继续对话，或用 `{self.config.end_conversation}` 结束对话")
                    await self.wakeup_xiaoai()
                else:
                    await self.stop_if_xiaoai_is_playing()
                continue
            
            if query == self.config.start_conversation:
                if not self.in_conversation:
                    self.log.info("用户请求开始持续对话模式")
                    print("开始对话")
                    self.in_conversation = True
                    await self.wakeup_xiaoai()
                else:
                    self.log.debug("用户重复请求开始对话，已在对话模式")
                await self.stop_if_xiaoai_is_playing()
                continue
            elif query == self.config.end_conversation:
                if self.in_conversation:
                    self.log.info("用户请求结束对话模式")
                    print("结束对话")
                    self.in_conversation = False
                    # End MoCA test if active
                    if self.in_moca_test:
                        self.log.info("同时结束MoCA测试会话")
                        self._end_moca_test()
                else:
                    self.log.debug("用户请求结束对话，但未在对话模式")
                await self.stop_if_xiaoai_is_playing()
                continue

            # we can change prompt
            if self.need_change_prompt(new_record):
                self.log.info("检测到更改提示词请求")
                print(new_record)
                self._change_prompt(new_record.get("query", ""))

            if not self.need_ask_gpt(new_record):
                self.log.debug("查询不满足GPT处理条件，跳过")
                continue

            # drop key words
            original_query_with_keywords = query
            query = re.sub(rf"^({'|'.join(self.config.keyword)})", "", query)
            self.log.debug(f"移除关键词后的查询: '{query}' (原始: '{original_query_with_keywords}')")
            
            # Save original query for MoCA recording
            original_query = query
            # llama3 is not good at Chinese, so we need to add prompt in it.
            if self.config.bot == "llama":
                self.log.debug("为llama模型添加中文提示")
                query = f"你是一个基于 llama3 的智能助手，请你跟我对话时，一定使用中文，不要夹杂一些英文单词，甚至英语短语也不能随意使用，但类似于 llama3 这样的专属名词除外，问题是：{query}"

            print("-" * 20)
            print("问题：" + query + "？")
            if not self.chatbot.has_history():
                # Use MoCA prompt if in MoCA test mode, otherwise use default prompt
                prompt_to_use = self.config.moca_test_prompt if self.in_moca_test else self.config.prompt
                query = f"{query},{prompt_to_use}"
                self.log.debug(f"无历史记录，添加提示词: {'MoCA测试' if self.in_moca_test else '默认'}")
            # some model can not detect the language code, so we need to add it

            if self.config.mute_xiaoai:
                self.log.debug("配置为静音模式，先停止小爱播放")
                await self.stop_if_xiaoai_is_playing()
            else:
                # waiting for xiaoai speaker done
                self.log.debug("非静音模式，等待8秒让小爱完成播放")
                await asyncio.sleep(8)
                
            await self.do_tts(f"正在问{self.chatbot.name}请耐心等待")
            
            try:
                xiaoai_response = new_record.get("answers", [])[0].get("tts", {}).get("text")
                self.log.debug(f"小爱原始回答: {xiaoai_response}")
                print(
                    "以下是小爱的回答：",
                    xiaoai_response,
                )
            except IndexError:
                self.log.debug("小爱没有返回回答")
                print("小爱没回")
            print(f"以下是 {self.chatbot.name} 的回答：", end="")
            try:
                self.log.info(f"开始处理{self.config.bot}的回答")
                await self.speak(self.ask_gpt(query), original_query)
            except Exception as e:
                self.log.error(f"{self.config.bot}回答时发生错误: {str(e)}")
                print(f"{self.chatbot.name} 回答出错 {str(e)}")
            else:
                self.log.info(f"{self.config.bot}回答处理完成")
                print("回答完毕")
            if self.in_conversation:
                self.log.debug("当前在对话模式，准备唤醒小爱等待下次输入")
                print(f"继续对话，或用 `{self.config.end_conversation}` 结束对话")
                await self.wakeup_xiaoai()

    async def speak(self, text_stream: AsyncIterator[str], query: str = "") -> None:
        self.log.debug(f"开始语音合成和播放 (查询: {query[:50]}...)")
        first_chunk = await text_stream.__anext__()
        # Detect the language from the first chunk
        # Add suffix '-' because tetos expects it to exist when selecting voices
        # however, the nation code is never used.
        lang = detect_language(first_chunk) + "-"
        self.log.debug(f"检测语言: {lang}, 首个文本块: {first_chunk[:50]}...")
        
        # Collect full response for MoCA test using list for efficiency
        response_chunks = [first_chunk] if self.in_moca_test else None

        async def gen():  # reconstruct the generator
            nonlocal response_chunks
            yield first_chunk
            async for text in text_stream:
                if self.in_moca_test and response_chunks is not None:
                    response_chunks.append(text)
                yield text

        try:
            await self.tts.synthesize(lang, gen())
            self.log.debug("语音合成和播放完成")
        except Exception as e:
            self.log.error(f"语音合成失败: {str(e)}")
            raise
        
        # Record the exchange in MoCA history
        if self.in_moca_test and query and response_chunks:
            full_response = "".join(response_chunks)
            self.log.debug(f"记录MoCA测试对话: 查询={query[:30]}..., 回答={full_response[:30]}...")
            self._record_moca_exchange(query, full_response)
