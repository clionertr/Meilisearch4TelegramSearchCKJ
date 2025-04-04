import asyncio
import signal # Import signal module for handling termination signals
import sys

from Meilisearch4TelegramSearchCKJ.src.models.meilisearch_handler import MeiliSearchClient
from Meilisearch4TelegramSearchCKJ.src.models.logger import setup_logger

# Import the new BOT handler/orchestrator
from Meilisearch4TelegramSearchCKJ.src.models.telegram_bot import TelegramBot
from Meilisearch4TelegramSearchCKJ.src.config.env import MEILI_HOST, MEILI_PASS, reload_config
from Meilisearch4TelegramSearchCKJ.src.utils.record_lastest_msg_id import load_config

logger = setup_logger()
meili = MeiliSearchClient(MEILI_HOST, MEILI_PASS)
user_bot_client_instance = None # Global instance for cleanup
telegram_bot_instance = None # Global instance for cleanup

# 添加关闭标志，防止多次触发关闭流程
shutdown_in_progress = False
# 添加强制关闭标志
force_shutdown_triggered = False

# --- User Bot Download/Listen Logic ---
async def download_and_listen_task():
    """The core task run by the UserBot (downloading and listening)."""
    # Import the USER bot handler
    from Meilisearch4TelegramSearchCKJ.src.models.telegram_client_handler import TelegramUserBot
    from Meilisearch4TelegramSearchCKJ.src.config.env import WHITE_LIST, BLACK_LIST
    global user_bot_client_instance

    # 重新加载配置文件，确保使用最新的配置
    try:
        logger.info("重新加载配置文件...")
        reload_config()
        logger.info("配置文件重新加载成功")
    except Exception as e:
        logger.error(f"重新加载配置文件失败: {e}", exc_info=True)

    user_bot_client_instance = TelegramUserBot(meili) # Assign to global var
    try:
        await user_bot_client_instance.start()
        logger.info("UserBot 已启动")
        config = load_config()
        logger.info(f"当前白名单: {WHITE_LIST}")
        logger.info(f"当前黑名单: {BLACK_LIST}")

        tasks = []
        dialog_count = 0
        async for dialog in user_bot_client_instance.client.iter_dialogs():
            dialog_count += 1
            dialog_name = dialog.title or dialog.name or f"Dialog {dialog.id}"
            logger.debug(f"检查 Dialog: ID={dialog.id}, Name='{dialog_name}'") # More detailed log

            # Determine if dialog should be processed
            should_process = False
            if WHITE_LIST: # Whitelist mode
                 if dialog.id in WHITE_LIST:
                      should_process = True
                      logger.debug(f"Dialog {dialog.id} in whitelist, processing.")
                 else:
                      logger.debug(f"Dialog {dialog.id} not in whitelist, skipping.")
            elif dialog.id not in BLACK_LIST: # Blacklist mode (only if whitelist is not active)
                 should_process = True
                 logger.debug(f"Dialog {dialog.id} not in blacklist, processing.")
            else: # Blacklist mode and dialog is in blacklist
                 logger.debug(f"Dialog {dialog.id} in blacklist, skipping.")

            if should_process:
                try:
                    peer = await user_bot_client_instance.client.get_entity(dialog.id)
                    offset_id = config.get('download_incremental', {}).get(str(dialog.id), 0)
                    logger.info(f"准备下载历史消息: Dialog ID={dialog.id}, Name='{dialog_name}', Offset ID={offset_id}")
                    tasks.append(
                        user_bot_client_instance.download_history(
                            peer,
                            limit=None, # Download all new messages
                            offset_id=offset_id,
                            latest_msg_config=config, # Pass the whole config for saving
                            dialog_id=dialog.id
                         )
                    )
                except ValueError as ve:
                     # Often happens for deleted accounts or inaccessible chats
                     logger.warning(f"无法获取实体或处理 Dialog {dialog.id} ('{dialog_name}'): {ve}. 跳过。")
                except Exception as e:
                     logger.error(f"处理 Dialog {dialog.id} ('{dialog_name}') 时出错: {e}", exc_info=True)

        logger.info(f"检查了 {dialog_count} 个对话框，将为 {len(tasks)} 个对话框下载/更新历史记录。")
        if tasks:
            # Run download tasks concurrently
            await asyncio.gather(*tasks, return_exceptions=True) # Log exceptions from gather
            logger.info("所有历史消息下载/更新任务完成。")
        else:
             logger.info("没有需要下载/更新历史消息的对话框。")

        logger.info("开始监听新消息...")
        # The run_until_disconnected call keeps the UserBot listening for new messages
        await user_bot_client_instance.client.run_until_disconnected()

    except asyncio.CancelledError:
        logger.info("UserBot 下载/监听任务被取消。")
    except Exception as e:
        # Log exceptions that occur outside the dialog loop (e.g., connection issues)
        logger.error(f"UserBot 运行出错: {e}", exc_info=True)
    finally:
        logger.info("UserBot 任务结束，执行清理...")
        if user_bot_client_instance:
            await user_bot_client_instance.cleanup()
        logger.info("UserBot 清理完成。")


# --- Main Application Logic ---
async def main():
    global telegram_bot_instance
    # The main_callback passed to TelegramBot is our download_and_listen_task
    telegram_bot_instance = TelegramBot(meili, download_and_listen_task)
    await telegram_bot_instance.run() # This runs the BOT client

# --- Graceful Shutdown Logic ---
async def shutdown(sig, loop):
    global shutdown_in_progress, force_shutdown_triggered

    # 防止多次触发关闭流程
    if shutdown_in_progress:
        if not force_shutdown_triggered:
            logger.warning(f"再次收到信号 {sig.name}，将在3秒后强制退出...")
            force_shutdown_triggered = True
            # 设置强制退出定时器
            loop.call_later(3, force_exit)
        return

    shutdown_in_progress = True
    logger.info(f"收到信号 {sig.name}, 开始优雅关闭...")

    # 设置强制退出超时（10秒后如果还未完成关闭，则强制退出）
    force_shutdown_timer = loop.call_later(10, force_exit)

    try:
        tasks = []
        # 1. Cancel UserBot task first (if running via Bot)
        if telegram_bot_instance and telegram_bot_instance.download_task and not telegram_bot_instance.download_task.done():
            logger.info("请求停止 UserBot 下载/监听任务...")
            telegram_bot_instance.download_task.cancel()
            # 添加等待任务取消的超时
            tasks.append(asyncio.create_task(wait_for_task_cancellation(telegram_bot_instance.download_task, 5)))

        # 2. Stop the Bot client loop
        if telegram_bot_instance and telegram_bot_instance.bot_client.is_connected():
            logger.info("请求断开 Bot 客户端连接...")
            # Disconnect should trigger run_until_disconnected to return
            tasks.append(asyncio.create_task(safe_disconnect(telegram_bot_instance.bot_client)))

        # Wait for disconnection/cancellation tasks (with timeout)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"关闭过程中出错: {result}", exc_info=True)

        # 3. Perform final cleanup (redundant but safe)
        if telegram_bot_instance:
            await telegram_bot_instance.cleanup()
        # Explicitly cleanup user bot if it wasn't stopped via task cancellation properly
        elif user_bot_client_instance:
            await user_bot_client_instance.cleanup()

        # 取消所有剩余任务
        await cancel_all_tasks(loop)

        # 取消强制退出定时器
        force_shutdown_timer.cancel()

        # 4. Stop the asyncio loop
        logger.info("关闭完成。")
    except Exception as e:
        logger.error(f"关闭过程中发生异常: {e}", exc_info=True)
        # 确保即使出现异常也会退出
        force_exit()

# 安全断开连接的辅助函数
async def safe_disconnect(client):
    try:
        await asyncio.wait_for(client.disconnect(), timeout=5.0)
        return True
    except asyncio.TimeoutError:
        logger.warning("断开连接超时，将强制断开")
        return False
    except Exception as e:
        logger.error(f"断开连接时出错: {e}", exc_info=True)
        return False

# 等待任务取消的辅助函数
async def wait_for_task_cancellation(task, timeout):
    try:
        await asyncio.wait_for(task, timeout=timeout)
        return True
    except asyncio.CancelledError:
        return True  # 正常取消
    except asyncio.TimeoutError:
        logger.warning(f"等待任务取消超时")
        return False
    except Exception as e:
        logger.error(f"等待任务取消时出错: {e}", exc_info=True)
        return False

# 取消所有剩余任务
async def cancel_all_tasks(loop):
    tasks = [t for t in asyncio.all_tasks(loop=loop)
             if t is not asyncio.current_task(loop=loop)]

    if not tasks:
        return

    logger.info(f"取消 {len(tasks)} 个剩余任务...")
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("所有剩余任务已取消")

# 强制退出函数
def force_exit():
    logger.critical("强制退出程序！")
    sys.exit(1)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Add signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))

    try:
        logger.info("启动应用程序...")
        loop.run_until_complete(main())
    except asyncio.CancelledError:
        logger.info("主事件循环被取消。")
    # except KeyboardInterrupt: # Should be handled by SIGINT
    #     logger.info("程序被用户中断 (KeyboardInterrupt)")
    finally:
        # Final cleanup attempt if shutdown handler didn't run or fully complete
        if not loop.is_closed():
            # 如果没有通过正常的关闭流程，尝试最后的清理
            if not shutdown_in_progress:
                logger.info("执行最终清理...")
                # 取消所有任务
                pending = asyncio.all_tasks(loop=loop)
                if pending:
                    logger.info(f"等待 {len(pending)} 个未完成的任务...")
                    for task in pending:
                        if task != asyncio.current_task(loop=loop):
                            task.cancel()

                    try:
                        # 设置超时，防止无限等待
                        loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*pending, return_exceptions=True),
                                timeout=5
                            )
                        )
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        logger.warning("等待任务取消超时或被取消")
                    except Exception as e:
                        logger.error(f"等待未完成任务时出错: {e}", exc_info=True)

            logger.info("关闭事件循环。")
            loop.close()
        logger.info("应用程序已退出。")
