# MoCA 测试快速开始指南 - 使用 Qwen API

本指南专门针对使用通义千问(Qwen) API 和小爱音箱Pro2 (OH2P) 进行 MoCA 认知测试。

## 前提条件

1. 小爱音箱Pro2 (OH2P) 设备
2. 通义千问 API Key ([获取地址](https://help.aliyun.com/zh/dashscope/developer-reference/api-details))
3. 小米账号和密码
4. Python 3.8+

## 快速开始

### 方法一：使用命令行参数

```bash
# 直接在命令行指定所有参数
python3 xiaogpt.py \
  --hardware OH2P \
  --mute_xiaoai \
  --use_qwen \
  --qwen_key YOUR_QWEN_API_KEY \
  --account your_xiaomi_account@example.com \
  --password your_password \
  --mi_did your_device_did
```

**注意**: 这种方式需要每次都输入完整参数，不太方便。

### 方法二：使用配置文件（推荐）

1. **创建配置文件**

复制 `moca_qwen_config.yaml` 到 `xiao_config.yaml`：

```bash
cp moca_qwen_config.yaml xiao_config.yaml
```

2. **编辑配置文件**

在 `xiao_config.yaml` 中填写您的信息：

```yaml
# 小米账号信息
account: "your_account@example.com"
password: "your_password"
mi_did: "your_device_did"

# Qwen API Key
qwen_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxx"

# MoCA 测试已启用
enable_moca_test: true
```

3. **运行程序**

```bash
python3 xiaogpt.py --hardware OH2P --mute_xiaoai --use_qwen
```

或者使用配置文件中的所有设置：

```bash
python3 xiaogpt.py --config xiao_config.yaml
```

## 使用 MoCA 测试

程序启动后，您会看到类似以下提示：

```
Running xiaogpt now, 用 请 开头来提问
或用 开始持续对话 开始持续对话
或用 健康每一天 开始MoCA认知测试
```

### 开始测试

对小爱音箱说：**"健康每一天"**

系统会：
1. 自动启动 MoCA 认知测试模式
2. 切换到专业的认知评估提示词
3. 开始记录所有对话内容

### 进行测试

与小爱音箱进行对话，AI 助手会基于 MoCA 量表引导您完成测试：

- 视空间与执行功能测试
- 命名测试
- 记忆测试
- 注意力测试
- 语言测试
- 抽象思维测试
- 延迟回忆测试
- 定向力测试

所有问答都会被自动记录。

### 结束测试

对小爱音箱说：**"结束持续对话"**

系统会：
1. 自动结束 MoCA 测试会话
2. 保存完整的对话历史到 JSON 文件
3. 显示保存路径

## 查看测试结果

测试结果保存在 `moca_history/` 目录下：

```bash
ls -lh moca_history/
# 输出示例：
# moca_test_20240115_143025.json
```

查看测试记录：

```bash
cat moca_history/moca_test_20240115_143025.json
```

文件格式：

```json
{
  "session_start_time": "2024-01-15 14:30:00",
  "session_end_time": "2024-01-15 15:00:00",
  "test_type": "MoCA阿兹海默症认知评估",
  "trigger_keyword": "健康每一天",
  "conversation_history": [
    {
      "timestamp": "2024-01-15 14:32:15",
      "user_query": "我今年70岁了",
      "bot_response": "好的，了解您的年龄了。现在让我们开始认知评估测试..."
    }
  ],
  "total_exchanges": 15
}
```

## 配置说明

### 核心配置项

- `hardware: OH2P` - 小爱音箱Pro2 硬件型号
- `bot: qwen` - 使用通义千问作为 AI 引擎
- `qwen_key` - 您的通义千问 API Key
- `mute_xiaoai: true` - 快速停止小爱的默认回答
- `enable_moca_test: true` - 启用 MoCA 测试功能

### MoCA 专用配置

- `moca_test_keyword: "健康每一天"` - 触发测试的关键词
- `moca_test_prompt` - MoCA 测试的专业提示词
- `moca_history_dir: "moca_history"` - 测试历史保存目录

## 常见问题

### 1. 如何获取 device DID?

```bash
pip install miservice_fork
export MI_USER=your_account@example.com
export MI_PASS=your_password
micli list
```

### 2. Qwen API 调用失败？

检查：
- API Key 是否正确
- 账户余额是否充足
- 网络连接是否正常

### 3. 小爱音箱没有响应？

检查：
- 硬件型号是否正确 (OH2P)
- 账号密码是否正确
- Device DID 是否正确
- 网络连接是否正常

### 4. 如何自定义触发词？

修改配置文件中的 `moca_test_keyword`：

```yaml
moca_test_keyword: "开始认知测试"  # 自定义触发词
```

## 完整命令示例

```bash
# 示例1：命令行方式（所有参数）
python3 xiaogpt.py \
  --hardware OH2P \
  --mute_xiaoai \
  --use_qwen \
  --qwen_key sk-xxxxxxxxxxxx \
  --account user@example.com \
  --password mypassword \
  --mi_did 123456789

# 示例2：配置文件方式（推荐）
python3 xiaogpt.py --config xiao_config.yaml

# 示例3：混合方式（配置文件 + 命令行覆盖）
python3 xiaogpt.py \
  --config xiao_config.yaml \
  --hardware OH2P \
  --use_qwen
```

## 安全提示

⚠️ **重要提示**：
- MoCA 测试结果仅供参考，不能替代专业医疗诊断
- 测试历史包含健康隐私信息，请妥善保管
- 不要将包含真实数据的配置文件上传到公共仓库
- 建议将 `xiao_config.yaml` 添加到 `.gitignore`

## 技术支持

如遇问题，请查看：
- [完整文档](MOCA_README.md)
- [示例代码](example_moca_usage.py)
- [实现总结](IMPLEMENTATION_SUMMARY.md)
