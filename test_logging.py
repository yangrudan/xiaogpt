#!/usr/bin/env python3
"""
测试脚本：演示XiaoGPT的日志功能

这个脚本展示了我们在XiaoGPT中新增的日志记录功能，
包括系统初始化、消息处理、MoCA测试等各个环节的日志。
"""

import logging
import asyncio
from pathlib import Path

# 模拟导入XiaoGPT相关模块（实际使用时需要正确的导入）
try:
    from xiaogpt.config import Config
    from xiaogpt.xiaogpt import MiGPT
except ImportError:
    print("请确保XiaoGPT模块正确安装")
    exit(1)

def setup_test_logging():
    """设置测试日志配置"""
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'xiaogpt_test.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

async def test_xiaogpt_logging():
    """测试XiaoGPT的日志功能"""
    
    print("🔍 XiaoGPT日志功能演示")
    print("=" * 50)
    
    # 加载配置
    try:
        config = Config.load_config()
        config.verbose = True  # 启用详细日志
        print("✅ 配置加载完成")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return

    # 创建MiGPT实例
    try:
        migpt = MiGPT(config)
        print("✅ MiGPT实例创建完成")
        print(f"📊 日志级别: {logging.getLevelName(migpt.log.level)}")
    except Exception as e:
        print(f"❌ MiGPT实例创建失败: {e}")
        return

    print("\n📋 日志功能说明:")
    print("1. 系统初始化日志：显示账号登录、硬件检测、TTS初始化等过程")
    print("2. 消息处理日志：记录用户查询的接收、处理和响应过程")
    print("3. MoCA测试日志：跟踪认知测试的开始、进行和结束")
    print("4. 设备控制日志：小爱音箱的唤醒、静音、播放状态等")
    print("5. 错误处理日志：网络异常、API错误、重试机制等")

    print("\n🎯 主要日志特性:")
    print("- INFO级别：记录主要业务流程和状态变化")
    print("- DEBUG级别：记录详细的技术细节和调试信息")
    print("- WARNING级别：记录警告和可恢复的错误")
    print("- ERROR级别：记录严重错误和异常")

    print("\n📁 MoCA测试日志:")
    print(f"- 历史保存目录: {config.moca_history_dir if hasattr(config, 'moca_history_dir') else 'moca_history/'}")
    print("- 自动记录测试会话的完整对话")
    print("- 包含时间戳、用户问题和机器人回答")
    print("- 生成结构化JSON文件便于分析")

    print("\n💡 日志使用建议:")
    print("1. 开发调试时使用DEBUG级别：config.verbose = True")
    print("2. 生产环境使用INFO级别：config.verbose = False")  
    print("3. 定期清理日志文件避免占用过多存储空间")
    print("4. 可以通过grep等工具快速搜索特定日志信息")

    print("\n🔧 常用日志搜索命令:")
    print("- 查看错误: grep 'ERROR' xiaogpt_test.log")
    print("- 查看MoCA测试: grep 'MoCA' xiaogpt_test.log") 
    print("- 查看用户查询: grep '处理用户查询' xiaogpt_test.log")
    print("- 查看TTS播放: grep 'TTS' xiaogpt_test.log")

def main():
    """主函数"""
    setup_test_logging()
    
    print("🚀 开始XiaoGPT日志功能演示...")
    
    # 创建事件循环并运行测试
    try:
        asyncio.run(test_xiaogpt_logging())
    except KeyboardInterrupt:
        print("\n⏹️  用户中断测试")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        logging.exception("测试执行异常")
    
    print("\n✨ 日志功能演示完成!")
    print("📄 详细日志已保存到 logs/xiaogpt_test.log")

if __name__ == "__main__":
    main()