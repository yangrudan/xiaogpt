# MoCA 认知测试功能说明

## 功能介绍

MoCA (Montreal Cognitive Assessment) 认知测试功能允许通过小爱同学进行阿兹海默症筛查测试。该功能基于蒙特利尔认知评估量表，可以记录整个测试过程的对话内容和状态，并将其保存到本地文件中。

## 主要特性

- **触发词启动**: 使用配置的关键词（默认为"健康每一天"）即可启动 MoCA 测试会话
- **专业提示词**: 自动切换到 MoCA 测试专用的提示词，引导进行认知评估
- **对话记录**: 自动记录测试过程中的所有问答交互
- **本地存储**: 将完整的测试历史保存为 JSON 格式的文件
- **会话状态管理**: 跟踪测试的开始和结束时间

## 配置方法

在 `xiao_config.yaml` 配置文件中添加以下配置项：

```yaml
# 启用 MoCA 认知测试功能
enable_moca_test: true

# MoCA 测试触发关键词
moca_test_keyword: "健康每一天"

# MoCA 测试的默认提示词
moca_test_prompt: "你是一个专业的认知评估助手，请基于蒙特利尔认知评估量表(MoCA)进行阿兹海默症筛查测试。请逐步引导用户完成各项认知测试，包括视空间与执行功能、命名、记忆、注意力、语言、抽象思维、延迟回忆和定向力等测试项目。"

# MoCA 测试历史保存目录
moca_history_dir: "moca_history"
```

## 使用方法

1. **启动测试**
   - 对小爱同学说出触发关键词（默认："健康每一天"）
   - 系统会自动开始 MoCA 认知测试会话
   - 进入持续对话模式

2. **进行测试**
   - 与 AI 助手进行对话，完成各项认知测试
   - 所有问答将被自动记录

3. **结束测试**
   - 说出结束持续对话的关键词（默认："结束持续对话"）
   - 系统会自动保存测试历史到本地文件

## 测试历史文件格式

测试完成后，会在配置的 `moca_history_dir` 目录下生成 JSON 格式的历史文件，文件名格式为 `moca_test_YYYYMMDD_HHMMSS.json`。

文件内容示例：

```json
{
  "session_start_time": "2024-01-15 12:00:00",
  "session_end_time": "2024-01-15 12:30:00",
  "test_type": "MoCA阿兹海默症认知评估",
  "trigger_keyword": "健康每一天",
  "conversation_history": [
    {
      "timestamp": "2024-01-15 12:05:00",
      "user_query": "我今年65岁了",
      "bot_response": "好的，让我们开始认知评估测试。首先进行视空间测试..."
    },
    {
      "timestamp": "2024-01-15 12:10:00",
      "user_query": "画了一个立方体",
      "bot_response": "很好。现在让我们进行命名测试..."
    }
  ],
  "total_exchanges": 2
}
```

## 字段说明

- `session_start_time`: 测试会话开始时间
- `session_end_time`: 测试会话结束时间
- `test_type`: 测试类型标识
- `trigger_keyword`: 触发该测试的关键词
- `conversation_history`: 对话历史数组
  - `timestamp`: 每次交互的时间戳
  - `user_query`: 用户的问题/回答
  - `bot_response`: AI 助手的回复
- `total_exchanges`: 总对话轮数

## 注意事项

1. 确保 `enable_moca_test` 设置为 `true` 才能使用此功能
2. 测试历史文件会持续累积，建议定期整理
3. 历史文件包含敏感的健康信息，请妥善保管
4. 此功能仅供参考，不能替代专业医疗诊断
5. `moca_history` 目录已自动添加到 `.gitignore`，不会被提交到版本控制

## 测试验证

可以运行提供的测试脚本验证配置是否正确：

```bash
python test_moca.py
```

该脚本会验证：
- 配置项的默认值
- 从 YAML 文件加载配置
- JSON 历史文件格式
- 目录创建功能

## 技术实现

MoCA 测试功能的主要实现包括：

1. **配置扩展** (`xiaogpt/config.py`)
   - 新增 MoCA 相关配置项
   - 定义默认提示词和关键词

2. **会话管理** (`xiaogpt/xiaogpt.py`)
   - `_start_moca_test()`: 开始测试会话
   - `_end_moca_test()`: 结束测试会话并保存
   - `_record_moca_exchange()`: 记录问答交互
   - `_save_moca_history()`: 保存历史到本地文件

3. **对话集成**
   - 在主对话循环中集成 MoCA 关键词检测
   - 在响应生成时自动记录对话内容
