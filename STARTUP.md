# NutriSnap 项目启动文档

## 项目简介

NutriSnap 是一款 **AI 智能营养管家** Web 应用。用户可以拍照上传食物图片进行营养分析，也可以与 AI 营养师对话获取个性化饮食建议。核心理念：**拍一拍，吃得更明白**。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.x | 后端语言 |
| Flask | 3.0.0 | Web 框架 |
| Flask-SQLAlchemy | 3.1.1 | ORM 数据库操作 |
| Flask-Login | 0.6.3 | 用户认证与会话管理 |
| Werkzeug | 3.0.1 | WSGI 工具库（密码哈希） |
| Pillow | >=11.0 | 图片处理 |
| OpenAI | 1.12.0 | AI 视觉识别 / LLM 对话（API 模式） |
| python-dotenv | 1.0.0 | 环境变量加载 |
| SQLite | - | 默认数据库 |

## 项目结构

```
nutrisnap/
├── app.py                    # 应用工厂入口，创建 Flask 实例
├── config.py                 # 全局配置（密钥、数据库、AI 参数）
├── models.py                 # 数据模型（User / MealRecord / DailyGoal / ChatHistory / MealPlan）
├── requirements.txt          # Python 依赖清单
├── index.html                # 登录/注册首页（Jinja2 模板）
├── ai/                       # AI 核心模块
│   ├── __init__.py
│   ├── food_recognition.py   # 食物图像识别（含 200+ 种中式食物营养数据库）
│   ├── nutrition_analysis.py # 营养分析引擎（逐餐分析 + 每日汇总）
│   └── ai_nutritionist.py    # AI 营养师聊天智能体
├── routes/                   # 路由蓝图
│   ├── __init__.py
│   ├── auth.py               # 登录 / 注册 / 登出
│   ├── main.py               # 仪表盘 / AI 营养师页面 / 营养报告
│   ├── meal.py               # 餐食上传 / 记录 / 删除 / 跳过 / 饮食计划
│   └── api.py                # REST API（食物搜索 / 图片分析 / 聊天 / 统计）
├── templates/                # Jinja2 前端模板
│   ├── base.html             # 基础布局
│   ├── index.html            # 登录页
│   ├── register.html         # 注册页
│   ├── dashboard.html        # 仪表盘（今日汇总 + 7 天趋势图）
│   ├── meal_upload.html      # 餐食上传页
│   ├── meal_log.html         # 餐食记录列表
│   ├── meal_detail.html      # 单餐详情
│   ├── nutritionist.html     # AI 营养师对话页
│   ├── meal_plan.html        # 个性化饮食计划
│   └── report.html           # 30 天营养趋势报告
├── static/                   # 静态资源 (CSS / JS / 图片)
├── uploads/                  # 用户上传的食物图片
├── instance/                 # Flask 实例文件夹
└── nutrisnap.db              # SQLite 数据库文件
```

## 功能概览

### 1. 用户系统
- 注册（用户名 + 邮箱 + 密码 + 身体数据 + 健康目标）
- 登录 / 登出（Flask-Login 会话管理）
- 健康目标：减重 / 增肌 / 维持体重

### 2. 餐食记录（两种方式）
- **拍照识别**：上传食物照片，AI 自动识别食物并计算营养
- **手动输入**：从内置食物数据库搜索并添加食物和分量
- 支持标记跳过某餐（如睡过头没吃早餐）
- 记录每餐花费，统计饮食开销

### 3. 仪表盘
- 今日营养摄入汇总（热量 / 蛋白质 / 脂肪 / 碳水 / 纤维）
- 三餐完成状态跟踪（已记录 / 已跳过 / 缺失）
- 近 7 天营养摄入趋势折线图
- 今日饮食计划展示

### 4. AI 营养师
- 多轮对话聊天机器人「小营」
- 结合用户身体数据和当日饮食记录提供个性化建议
- 支持离线规则模式（无需 API Key 也可使用）

### 5. 个性化饮食计划
- 根据用户目标（减重/增肌/维持）自动生成三餐食谱
- 展示每餐食物、分量、热量和营养小贴士

### 6. 营养报告
- 近 30 天营养摄入趋势
- 日均营养摄入统计
- 三餐完成率统计
- 各类餐食平均花费

## 运行模式

项目支持两种 AI 运行模式，通过环境变量 `AI_MODE` 切换：

| 模式 | AI_MODE 值 | 说明 |
|------|-----------|------|
| 模拟模式（默认） | `simulation` | 使用内置食物数据库 + 颜色启发式识别，无需 API Key，可离线运行 |
| API 模式 | `api` | 调用 OpenAI 兼容 API 进行真实视觉识别和 LLM 对话 |

## 快速启动

### 环境要求
- Python 3.8+
- pip

### 1. 克隆项目并进入目录
```bash
cd nutrisnap
```

### 2. 创建虚拟环境（推荐）
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量（可选）

模拟模式无需任何配置即可启动。如需启用 AI API 模式，创建 `.env` 文件：

```env
AI_MODE=api
LLM_API_KEY=your-api-key-here
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o
VISION_MODEL=gpt-4o
```

> `LLM_API_BASE` 支持任何 OpenAI 兼容接口（如 Azure OpenAI、本地 LLM 等）。

### 5. 启动应用
```bash
python app.py
```

应用将在 `http://localhost:5000` 启动，默认以 Debug 模式运行，监听 `0.0.0.0`。

### 6. 访问应用
浏览器打开 `http://localhost:5000`，注册账号后即可使用。

## 数据库

默认使用 SQLite，数据库文件为项目根目录的 `nutrisnap.db`，首次启动时自动创建表结构。

### 核心数据表
| 表名 | 说明 |
|------|------|
| users | 用户账号与身体数据 |
| meal_records | 餐食记录（含识别结果 JSON、营养数据 JSON） |
| daily_goals | 每日营养目标 |
| chat_history | AI 营养师对话历史 |
| meal_plans | 生成的饮食计划 |

## API 接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/search-food?q=关键词` | 搜索食物数据库 | 需要登录 |
| POST | `/api/manual-record` | 手动记录餐食 (JSON) | 需要登录 |
| POST | `/api/analyze-food` | 上传图片分析食物 (multipart) | 需要登录 |
| POST | `/api/chat` | AI 营养师对话 | 需要登录 |
| POST | `/api/generate-plan` | 生成饮食计划 | 需要登录 |
| GET | `/api/daily-stats` | 获取今日营养统计 | 需要登录 |

## 内置食物数据库

`ai/food_recognition.py` 中 `FOOD_DB` 字典包含 **200+ 种中式食物** 的营养数据（每 100g），涵盖：

- 主食 / 粉面 / 早餐（米饭、面条、肠粉、包子等）
- 肉类 / 蛋白质（鸡胸肉、牛肉、猪肉、鸡蛋等）
- 水产海鲜（三文鱼、虾、鱼片等）
- 豆制品 / 素菜
- 蔬菜（30+ 种）
- 中式热菜（红烧肉、宫保鸡丁、麻婆豆腐等）
- 汤品
- 煲仔饭 / 盖饭 / 炒饭
- 麻辣烫 / 火锅 / 干锅
- 烧烤 / 油炸
- 饺子 / 馄饨
- 日韩料理
- 西式快餐
- 水果（15+ 种）
- 饮品（咖啡、茶、奶茶、酒类等）
- 甜品 / 零食

## 常见问题

**Q: 模拟模式下食物识别不准确？**
模拟模式使用图片颜色分析做启发式识别，结果仅供参考。切换至 API 模式可获得真实的视觉 AI 识别效果。

**Q: 如何切换至 API 模式？**
设置环境变量 `AI_MODE=api` 并配置 `LLM_API_KEY` 即可。支持任何 OpenAI 兼容的 API 端点。

**Q: 数据库如何迁移？**
SQLite 数据库在首次启动时自动创建。如需重置，删除 `nutrisnap.db` 文件后重启应用即可。

**Q: 上传的图片存储在哪里？**
存储在 `uploads/` 目录，文件名使用 UUID 避免冲突。
