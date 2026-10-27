# 班主任工具箱 / 家长会助手 V0.1

一个以“本地 Excel -> 自动生成家长会材料”为核心的 Windows 桌面原型。

## 当前功能

- 导入本次考试 Excel
- 可选导入上次考试 Excel
- 自动识别表头、姓名列、成绩科目
- 提供“字段确认”界面，手动纠正自动识别结果
- 计算班级概览、各科平均分、及格率、优秀率、分数段
- 按学生姓名匹配两次考试并计算进退步
- 生成 `班级成绩分析.xlsx`
- 生成基础版 `家长会PPT.pptx`
- 生成 `学生个人报告.docx`
- 默认全部核心计算在本机完成
- 可选接入 OpenAI-compatible AI 接口生成班级总结；未配置或调用失败时自动回退离线模板

## 为什么 V0.1 先做本地版

成绩数据涉及学生隐私。当前版本不需要数据库、服务器、登录系统，也不会把原始 Excel 自动上传到云端。

AI 只应该接收匿名化后的班级统计事实。正式商业版不应把长期 API Key 写进客户端，应改为国内云端 AI 网关/Serverless 代理。

## Windows 本地运行

建议 Python 3.12。

直接双击：

```text
scripts/run_windows.bat
```

脚本会自动创建 `.venv`、安装依赖并启动程序。

也可以手动：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## AI 配置（可选）

复制 `config/ai.example.json` 为 `config/ai.json`，填写兼容 OpenAI Chat Completions 的 API。

```json
{
  "enabled": true,
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "api_key": "YOUR_API_KEY",
  "model": "qwen-plus"
}
```

也可以使用环境变量 `TEACHER_AI_BASE_URL`、`TEACHER_AI_API_KEY`、`TEACHER_AI_MODEL`。

> `config/ai.json` 已被 `.gitignore` 忽略，不要把真实 API Key 提交到 GitHub。

## 打 Windows EXE

Windows 上双击 `scripts/build_windows.bat`，生成：

```text
dist/ClassTeacherToolbox.exe
```

仓库同时包含 GitHub Actions：每次 push 到 `main`，或者手动运行 `Build Windows EXE`，都会在 Windows Runner 上构建 EXE，并上传为 Actions Artifact。

## 当前输出目录

程序默认写到：

```text
用户目录/Documents/家长会助手输出/
```

包含：

```text
班级成绩分析.xlsx
家长会PPT.pptx
学生个人报告.docx
```

## 推荐后续顺序

1. 找 3-5 位真实老师测试不同格式的成绩表
2. 增强“脏 Excel”识别和字段映射
3. 做 2-3 套更好看的 PPT 模板
4. 再接 AI：家长会发言稿、班级总结、学生评语
5. 做离线授权码/淘宝交付
6. 再做正式安装包、代码签名、自动更新

## 目录

```text
app/
  models.py
  excel_service.py
  analysis_service.py
  ai_service.py
  excel_report_service.py
  ppt_service.py
  student_report_service.py
  sample_data.py
  gui.py
config/
  ai.example.json
scripts/
  run_windows.bat
  build_windows.bat
.github/workflows/
  build-windows.yml
```

## 当前阶段说明

这是可运行 MVP，不是正式商业发行版。当前重点是验证：老师的 Excel 能不能顺利导入、自动生成的材料是否真的节省时间、哪些输出最值得付费。
