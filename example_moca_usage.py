#!/usr/bin/env python3
"""
示例：如何使用 MoCA 认知测试功能

此脚本展示了 MoCA 测试功能的配置和基本使用流程。
注意：这只是演示代码，实际使用需要配置真实的小米账号和 OpenAI key。
"""

from xiaogpt.config import Config
from pathlib import Path

def create_moca_config_example():
    """创建一个启用 MoCA 功能的配置示例"""
    
    # 基本配置
    config = Config(
        # 小米设备配置
        hardware="LX06",
        account="your_xiaomi_account@example.com",
        password="your_password",
        mi_did="your_device_did",
        
        # AI Bot 配置
        bot="chatgptapi",
        openai_key="your_openai_key",
        
        # 启用 MoCA 测试功能
        enable_moca_test=True,
        moca_test_keyword="健康每一天",
        moca_test_prompt="你是一个专业的认知评估助手，请基于蒙特利尔认知评估量表(MoCA)进行阿兹海默症筛查测试。请逐步引导用户完成各项认知测试，包括视空间与执行功能、命名、记忆、注意力、语言、抽象思维、延迟回忆和定向力等测试项目。",
        moca_history_dir="moca_history",
        
        # 其他选项
        mute_xiaoai=True,
        stream=True,
        verbose=1
    )
    
    return config

def demonstrate_moca_usage():
    """演示 MoCA 功能的使用流程"""
    
    print("=" * 60)
    print("MoCA 认知测试功能使用示例")
    print("=" * 60)
    print()
    
    print("步骤 1: 创建配置")
    print("-" * 60)
    config = create_moca_config_example()
    print(f"✓ MoCA 功能已启用: {config.enable_moca_test}")
    print(f"✓ 触发关键词: {config.moca_test_keyword}")
    print(f"✓ 历史保存目录: {config.moca_history_dir}")
    print()
    
    print("步骤 2: 使用流程")
    print("-" * 60)
    print("1. 启动 xiaogpt:")
    print("   xiaogpt --config xiao_config.yaml")
    print()
    print("2. 对小爱同学说触发词:")
    print(f"   「{config.moca_test_keyword}」")
    print()
    print("3. 开始测试对话:")
    print("   - 系统会自动切换到 MoCA 测试模式")
    print("   - AI 助手会引导您完成认知测试")
    print("   - 所有对话会被自动记录")
    print()
    print("4. 结束测试:")
    print("   - 说「结束持续对话」")
    print("   - 测试历史会自动保存到本地")
    print()
    
    print("步骤 3: 查看测试结果")
    print("-" * 60)
    print(f"测试完成后，历史文件会保存在: ./{config.moca_history_dir}/")
    print("文件格式: moca_test_YYYYMMDD_HHMMSS.json")
    print()
    print("示例文件内容:")
    print("""
{
  "session_start_time": "2024-01-15 12:00:00",
  "session_end_time": "2024-01-15 12:30:00",
  "test_type": "MoCA阿兹海默症认知评估",
  "trigger_keyword": "健康每一天",
  "conversation_history": [
    {
      "timestamp": "2024-01-15 12:05:00",
      "user_query": "我今年65岁了",
      "bot_response": "好的，让我们开始认知评估..."
    }
  ],
  "total_exchanges": 1
}
    """)
    
    print("=" * 60)
    print("注意事项")
    print("=" * 60)
    print("⚠️  此功能仅供参考，不能替代专业医疗诊断")
    print("⚠️  测试历史包含健康信息，请妥善保管")
    print("⚠️  确保配置文件中 enable_moca_test 设置为 true")
    print("=" * 60)

if __name__ == "__main__":
    try:
        demonstrate_moca_usage()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
