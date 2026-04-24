import os
import sys
import uuid
import logging
import asyncio
import websockets
from datetime import datetime, timezone
from websockets.exceptions import ConnectionClosed, InvalidStatus, InvalidURI
from app.config import Config

logging.info("[volcano_translator] 模块加载成功")

# Protobuf 路径：从 app/services/ 向上两级到项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
protogen_dir = os.path.join(project_root, "python_protogen")
if protogen_dir not in sys.path:
    sys.path.append(protogen_dir)

from products.understanding.ast.ast_service_pb2 import TranslateRequest, TranslateResponse
from common.events_pb2 import Type

WS_CONNECT_TIMEOUT = 30
WS_PING_INTERVAL = 20
WS_PING_TIMEOUT = 10
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2

async def doubao_translator(socketio, sid, lang_from, lang_to, audio_queue, stop_event, event_prefix, mode, glossary=None, speaker_id=None, transcript_collector=None, billing_collector=None):
    # 最基础的入口调试
    print(f"[DEBUG][{event_prefix}][{sid}] doubao_translator 函数被调用", flush=True)
    logging.info(f"[DEBUG][{event_prefix}][{sid}] doubao_translator 函数被调用 - logging")

    if not Config.VOLCANO_APP_KEY or not Config.VOLCANO_ACCESS_KEY:
        error_msg = "火山引擎API密钥未配置"
        logging.error(f"[{event_prefix}][{sid}] {error_msg}")
        socketio.emit('translation_service_status',
                     {'status': 'error', 'message': error_msg, 'channel': event_prefix},
                     to=sid)
        return

    session_id = str(uuid.uuid4())
    conn_id = str(uuid.uuid4())

    # 计费统计 - 使用传入的 billing_collector 或创建新的
    if billing_collector is not None:
        billing_stats = billing_collector
    else:
        billing_stats = {
            'input_audio_tokens': 0,
            'output_text_tokens': 0,
            'output_audio_tokens': 0,
            'duration_msec': 0
        }
    ws_url = "wss://openspeech.bytedance.com/api/v4/ast/v2/translate"
    resource_id = "volc.service_type.10053"

    headers = {
        "X-Api-App-Key": Config.VOLCANO_APP_KEY,
        "X-Api-Access-Key": Config.VOLCANO_ACCESS_KEY,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Connect-Id": conn_id
    }

    socketio.emit('translation_service_status',
                  {'status': 'connecting', 'message': '连接翻译服务...', 'channel': event_prefix},
                  to=sid)

    last_error = None
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            async with websockets.connect(
                ws_url,
                additional_headers=headers,
                ping_interval=WS_PING_INTERVAL,
                ping_timeout=WS_PING_TIMEOUT,
                close_timeout=10
            ) as ws:
                logging.info(f"[{event_prefix}][{sid}] 翻译WebSocket连接成功 (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS})")
                print(f"[DEBUG][{event_prefix}][{sid}] WebSocket连接成功，准备发送StartSession", flush=True)

                request_payload = {'mode': mode, 'source_language': lang_from, 'target_language': lang_to}

                if speaker_id:
                    request_payload['speaker_id'] = speaker_id

                if glossary:
                    request_payload['corpus'] = {'glossary_list': glossary}

                start_req = TranslateRequest(
                    event=Type.StartSession,
                    request_meta={'SessionID': session_id},
                    user={'uid': "web_client"},
                    source_audio={'format': 'wav', 'codec': 'raw', 'rate': 16000, 'bits': 16, 'channel': 1},
                    # PCM原始格式（float32）：无编码延迟，前端可逐帧流式播放
                    target_audio={'format': 'pcm', 'rate': 24000},
                    request=request_payload)

                # 服务端降噪：让火山引擎对输入音频降噪，提升ASR识别准确度
                start_req.denoise = True

                try:
                    await asyncio.wait_for(ws.send(start_req.SerializeToString()), timeout=10)
                except asyncio.TimeoutError:
                    raise Exception("发送启动请求超时")

                try:
                    first_resp_msg = await asyncio.wait_for(ws.recv(), timeout=10)
                except asyncio.TimeoutError:
                    raise Exception("接收启动响应超时")

                first_resp = TranslateResponse()
                first_resp.ParseFromString(first_resp_msg)

                if first_resp.event != Type.SessionStarted:
                    error_code = getattr(first_resp.response_meta, 'Code', 'UNKNOWN')
                    error_message = getattr(first_resp.response_meta, 'Message', '会话启动失败')

                    if error_code in ['AUTH_FAILED', 'INVALID_KEY', 'UNAUTHORIZED']:
                        logging.error(f"[{event_prefix}][{sid}] 认证失败: {error_message} (错误码: {error_code})")
                        socketio.emit('translation_service_status',
                                     {'status': 'error', 'message': f'认证失败: {error_message}', 'channel': event_prefix},
                                     to=sid)
                        return

                    raise Exception(f"会话启动失败: {error_message} (错误码: {error_code})")

                logging.info(f"[{event_prefix}][{sid}] 会话成功启动")
                socketio.emit('translation_service_status',
                             {'status': 'connected', 'message': '翻译服务已连接', 'channel': event_prefix},
                             to=sid)

                async def sender():
                    try:
                        while not stop_event.is_set():
                            try:
                                chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                                task_req = TranslateRequest(
                                    event=Type.TaskRequest,
                                    request_meta={'SessionID': session_id},
                                    source_audio={'binary_data': chunk}
                                )
                                await ws.send(task_req.SerializeToString())
                            except asyncio.TimeoutError:
                                continue
                            except ConnectionClosed:
                                logging.warning(f"[{event_prefix}][{sid}] WebSocket连接已关闭（发送端）")
                                break
                            except Exception as e:
                                logging.error(f"[{event_prefix}][{sid}] Sender Error: {e}")
                                break
                    finally:
                        try:
                            if not ws.closed:
                                finish_req = TranslateRequest(
                                    event=Type.FinishSession,
                                    request_meta={'SessionID': session_id}
                                )
                                await asyncio.wait_for(ws.send(finish_req.SerializeToString()), timeout=5)
                                logging.info(f"[{event_prefix}][{sid}] 已发送结束信号")
                        except (ConnectionClosed, asyncio.TimeoutError, Exception) as e:
                            logging.debug(f"[{event_prefix}][{sid}] 发送结束信号失败（连接可能已断开）: {e}")

                async def receiver():
                    try:
                        msg_count = 0
                        while not stop_event.is_set():
                            try:
                                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                                msg_count += 1
                                response = TranslateResponse()
                                response.ParseFromString(message)
                                event_type = response.event

                                # 打印所有事件类型的原始值
                                logging.info(f"[{event_prefix}][{sid}] 收到消息 #{msg_count}, 事件类型: {event_type} (原始值={int(event_type)})")

                                # 打印 TranslateResponse 的所有字段
                                try:
                                    fields = {}
                                    for field in response.DESCRIPTOR.fields:
                                        val = getattr(response, field.name)
                                        if field.name == 'response_meta' and val:
                                            meta_fields = {}
                                            for mf in val.DESCRIPTOR.fields:
                                                meta_fields[mf.name] = str(getattr(val, mf.name))[:100]
                                            fields[field.name] = meta_fields
                                        elif field.name not in ['data', 'text']:
                                            fields[field.name] = str(val)[:100]
                                    logging.info(f"[{event_prefix}][{sid}] 消息字段: {fields}")
                                except Exception as e:
                                    logging.info(f"[{event_prefix}][{sid}] 获取字段失败: {e}")

                                if event_type == Type.SessionFinished:
                                    logging.info(f"[{event_prefix}][{sid}] 会话正常结束")
                                    # 调试：打印完整的 response_meta
                                    response_meta = response.response_meta
                                    logging.info(f"[{event_prefix}][{sid}] SessionFinished response_meta: {response_meta}")
                                    logging.info(f"[{event_prefix}][{sid}] response_meta 字段: {dir(response_meta)}")
                                    # 会话结束时获取最终计费信息
                                    billing = response.response_meta.billing if hasattr(response.response_meta, 'billing') else None
                                    if billing:
                                        logging.info(f"[{event_prefix}][{sid}] 会话结束计费信息: {billing}")
                                        logging.info(f"[{event_prefix}][{sid}] billing 字段: {dir(billing)}")
                                        duration_ms = getattr(billing, 'duration_msec', 0)
                                        billing_stats['duration_msec'] += duration_ms
                                        if hasattr(billing, 'items'):
                                            logging.info(f"[{event_prefix}][{sid}] billing items: {list(billing.items)}")
                                            for item in billing.items:
                                                unit = getattr(item, 'unit', '')
                                                quantity = getattr(item, 'quantity', 0)
                                                logging.info(f"[{event_prefix}][{sid}] billing item: unit={unit}, quantity={quantity}")
                                                if unit == 'input_audio_tokens':
                                                    billing_stats['input_audio_tokens'] += quantity
                                                elif unit == 'output_text_tokens':
                                                    billing_stats['output_text_tokens'] += quantity
                                                elif unit == 'output_audio_tokens':
                                                    billing_stats['output_audio_tokens'] += quantity
                                    else:
                                        logging.warning(f"[{event_prefix}][{sid}] SessionFinished 中没有 billing 信息")
                                    break
                                elif event_type == Type.SessionFailed:
                                    error_msg = getattr(response.response_meta, 'Message', '会话失败')
                                    error_code = getattr(response.response_meta, 'Code', 'UNKNOWN')
                                    logging.error(f"[{event_prefix}][{sid}] 会话失败: {error_msg} (错误码: {error_code})")
                                    socketio.emit('translation_service_status',
                                                 {'status': 'error', 'message': f'会话失败: {error_msg}', 'channel': event_prefix},
                                                 to=sid)
                                    break
                                elif event_type == Type.SourceSubtitleResponse:
                                    socketio.emit(f'text_update_{event_prefix}',
                                                 {'type': 'original', 'text': response.text, 'isFinal': False},
                                                 to=sid)
                                elif event_type == Type.SourceSubtitleEnd:
                                    socketio.emit(f'text_update_{event_prefix}',
                                                 {'type': 'original', 'text': response.text, 'isFinal': True},
                                                 to=sid)
                                    if transcript_collector is not None and response.text:
                                        transcript_collector.append({
                                            'channel': event_prefix,
                                            'type': 'original',
                                            'text': response.text,
                                            'timestamp': datetime.now(timezone.utc).isoformat()
                                        })
                                elif event_type == Type.TranslationSubtitleResponse:
                                    socketio.emit(f'text_update_{event_prefix}',
                                                 {'type': 'translated', 'text': response.text, 'isFinal': False},
                                                 to=sid)
                                elif event_type == Type.TranslationSubtitleEnd:
                                    socketio.emit(f'text_update_{event_prefix}',
                                                 {'type': 'translated', 'text': response.text, 'isFinal': True},
                                                 to=sid)
                                    if transcript_collector is not None and response.text:
                                        transcript_collector.append({
                                            'channel': event_prefix,
                                            'type': 'translated',
                                            'text': response.text,
                                            'timestamp': datetime.now(timezone.utc).isoformat()
                                        })
                                elif event_type == Type.TTSResponse and response.data:
                                    socketio.emit(f'audio_data_{event_prefix}', response.data, to=sid)
                                elif event_type == Type.TTSSentenceEnd:
                                    socketio.emit(f'tts_sentence_end_{event_prefix}', to=sid)
                                elif event_type == Type.UsageResponse:
                                    # 计量事件：记录实际音频时长和token消耗
                                    logging.info(f"[{event_prefix}][{sid}] 收到 UsageResponse 事件")
                                    logging.info(f"[{event_prefix}][{sid}] UsageResponse response_meta: {response.response_meta}")
                                    billing = response.response_meta.billing if hasattr(response.response_meta, 'billing') else None
                                    if billing:
                                        logging.info(f"[{event_prefix}][{sid}] billing 对象存在: {billing}")
                                        logging.info(f"[{event_prefix}][{sid}] billing 字段: {dir(billing)}")
                                        if hasattr(billing, 'items'):
                                            logging.info(f"[{event_prefix}][{sid}] billing items 内容: {list(billing.items)}")
                                        # 累计音频时长
                                        duration_ms = getattr(billing, 'duration_msec', 0)
                                        billing_stats['duration_msec'] += duration_ms

                                        # 累计token消耗
                                        if hasattr(billing, 'items'):
                                            for item in billing.items:
                                                unit = getattr(item, 'unit', '')
                                                quantity = getattr(item, 'quantity', 0)
                                                if unit == 'input_audio_tokens':
                                                    billing_stats['input_audio_tokens'] += quantity
                                                elif unit == 'output_text_tokens':
                                                    billing_stats['output_text_tokens'] += quantity
                                                elif unit == 'output_audio_tokens':
                                                    billing_stats['output_audio_tokens'] += quantity

                                        # 发送到计费收集器（用于多通道合并）
                                        if billing_collector is not None:
                                            billing_collector[billing_stats['duration_msec']] = billing_stats.copy()

                                        # 立即推送计费更新到前端
                                        total_tokens = (
                                            billing_stats['input_audio_tokens'] +
                                            billing_stats['output_text_tokens'] +
                                            billing_stats['output_audio_tokens']
                                        )
                                        socketio.emit('billing_update', {
                                            'total_tokens': int(total_tokens),
                                            'duration_sec': round(billing_stats['duration_msec'] / 1000, 1),
                                            'input_audio_tokens': int(billing_stats['input_audio_tokens']),
                                            'output_text_tokens': int(billing_stats['output_text_tokens']),
                                            'output_audio_tokens': int(billing_stats['output_audio_tokens'])
                                        }, to=sid)

                                        socketio.emit(f'usage_update_{event_prefix}',
                                                     {'duration_ms': duration_ms},
                                                     to=sid)
                                        logging.info(f"[{event_prefix}][{sid}] 计量: audio_in={billing_stats['input_audio_tokens']:.0f}, text_out={billing_stats['output_text_tokens']:.0f}, audio_out={billing_stats['output_audio_tokens']:.0f}, duration={duration_ms}ms")
                                elif event_type == Type.AudioMuted:
                                    # 静音检测事件：通知前端显示"检测到静音"提示
                                    muted_ms = getattr(response, 'muted_duration_ms', 0)
                                    socketio.emit(f'audio_muted_{event_prefix}',
                                                 {'muted_ms': muted_ms},
                                                 to=sid)
                                else:
                                    # 记录未处理的事件类型及其详细信息
                                    logging.info(f"[{event_prefix}][{sid}] 未处理的事件类型: {event_type} (值={event_type})")
                                    try:
                                        meta = response.response_meta
                                        logging.info(f"[{event_prefix}][{sid}] 该事件的 response_meta: {meta}, dir={dir(meta)}")
                                        if hasattr(meta, 'billing'):
                                            logging.info(f"[{event_prefix}][{sid}] 该事件的 billing: {meta.billing}")
                                    except Exception as e:
                                        logging.info(f"[{event_prefix}][{sid}] 获取 response_meta 失败: {e}")

                            except asyncio.TimeoutError:
                                continue
                            except ConnectionClosed:
                                logging.warning(f"[{event_prefix}][{sid}] WebSocket连接已关闭（接收端）")
                                break
                            except Exception as e:
                                logging.error(f"[{event_prefix}][{sid}] Receiver Error: {e}")
                                break
                    except Exception as e:
                        logging.error(f"[{event_prefix}][{sid}] Receiver outer error: {e}")

                print(f"[DEBUG][{event_prefix}][{sid}] 准备启动 sender 和 receiver 协程", flush=True)
                try:
                    await asyncio.gather(sender(), receiver(), return_exceptions=True)
                    print(f"[DEBUG][{event_prefix}][{sid}] sender 和 receiver 协程已完成", flush=True)
                except Exception as e:
                    print(f"[DEBUG][{event_prefix}][{sid}] sender/receiver 异常: {e}", flush=True)
                    logging.error(f"[{event_prefix}][{sid}] sender/receiver 异常: {e}")
                break

        except (ConnectionClosed, InvalidStatus, InvalidURI) as e:
            last_error = f"WebSocket连接错误: {str(e)}"
            logging.warning(f"[{event_prefix}][{sid}] {last_error} (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS})")

            if attempt < MAX_RETRY_ATTEMPTS - 1:
                socketio.emit('translation_service_status',
                             {'status': 'connecting', 'message': f'连接失败，正在重试 ({attempt + 1}/{MAX_RETRY_ATTEMPTS})...', 'channel': event_prefix},
                             to=sid)
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                socketio.emit('translation_service_status',
                             {'status': 'error', 'message': f'连接失败，已重试{MAX_RETRY_ATTEMPTS}次', 'channel': event_prefix},
                             to=sid)

        except asyncio.TimeoutError:
            last_error = "连接超时"
            logging.warning(f"[{event_prefix}][{sid}] {last_error} (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS})")

            if attempt < MAX_RETRY_ATTEMPTS - 1:
                socketio.emit('translation_service_status',
                             {'status': 'connecting', 'message': f'连接超时，正在重试 ({attempt + 1}/{MAX_RETRY_ATTEMPTS})...', 'channel': event_prefix},
                             to=sid)
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                socketio.emit('translation_service_status',
                             {'status': 'error', 'message': '连接超时，请检查网络连接', 'channel': event_prefix},
                             to=sid)

        except Exception as e:
            last_error = f"翻译服务异常: {str(e)}"
            error_type = type(e).__name__
            logging.error(f"[{event_prefix}][{sid}] {last_error} (类型: {error_type})")

            if error_type in ['ConnectionError', 'OSError', 'TimeoutError'] and attempt < MAX_RETRY_ATTEMPTS - 1:
                socketio.emit('translation_service_status',
                             {'status': 'connecting', 'message': f'连接异常，正在重试 ({attempt + 1}/{MAX_RETRY_ATTEMPTS})...', 'channel': event_prefix},
                             to=sid)
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            else:
                socketio.emit('translation_service_status',
                             {'status': 'error', 'message': f'连接AI服务失败: {str(e)}', 'channel': event_prefix},
                             to=sid)
                break

    if last_error and attempt == MAX_RETRY_ATTEMPTS - 1:
        logging.error(f"[{event_prefix}][{sid}] 翻译服务连接失败，已重试{MAX_RETRY_ATTEMPTS}次。最后错误: {last_error}")

    logging.info(f"[{event_prefix}][{sid}] 翻译任务结束")
    stop_event.set()
