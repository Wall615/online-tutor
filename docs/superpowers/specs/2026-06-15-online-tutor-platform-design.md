# 线上家教平台 — 设计文档

> **项目类型**: Python 小组学期项目  
> **日期**: 2026-06-15 (周一) | **截止**: 2026-06-18 (周四)  
> **团队**: 5人 | **交付物**: 可运行代码 + PPT答辩

---

## 1. 项目概述

一个线上家教平台，连接学生与教师，支持课程发布、预约、在线沟通、支付和评价。包含学生、教师、家长、管理员四种角色。

---

## 2. 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| Web 框架 | Flask + Blueprint | 课程教学内容，模块化拆分 |
| 模板引擎 | Jinja2 | Flask 内置，服务端渲染 |
| 前端 | Bootstrap 5 + 原生 JS | 快速出 UI，无前端框架学习成本 |
| 数据库 | SQLite + SQLAlchemy | 课程教学内容，零配置 |
| 认证 | Flask-Login + session | 轻量，适合单体应用 |
| 实时聊天 | 轮询 (setInterval) | 避免引入 WebSocket 复杂度 |

---

## 3. 系统架构

### 3.1 项目结构

```
online_tutor/
├── app.py                     # 应用入口、配置、蓝图注册
├── config.py                  # 配置文件
├── models.py                  # SQLAlchemy 数据模型（所有模块共享）
├── requirements.txt           # 依赖清单
├── auth/                      # 用户认证 Blueprint
│   ├── __init__.py
│   └── routes.py              # 注册/登录/登出/个人资料
├── course/                    # 课程管理 Blueprint
│   ├── __init__.py
│   └── routes.py              # 发布课程/搜索/浏览/详情
├── booking/                   # 预约管理 Blueprint
│   ├── __init__.py
│   └── routes.py              # 创建预约/确认/取消/状态跟踪
├── chat/                      # 在线聊天 Blueprint
│   ├── __init__.py
│   └── routes.py              # 发送消息/获取消息/聊天界面
├── review/                    # 评价系统 Blueprint
│   ├── __init__.py
│   └── routes.py              # 评分/评论/教师评价展示
├── parent/                    # 家长功能 Blueprint
│   ├── __init__.py
│   └── routes.py              # 绑定学生/学习记录/消费查看
├── payment/                   # 模拟支付 Blueprint
│   ├── __init__.py
│   └── routes.py              # 支付/余额/交易记录
├── admin/                     # 管理后台 Blueprint
│   ├── __init__.py
│   └── routes.py              # 教师审核/用户管理/仪表盘
├── templates/                 # Jinja2 模板
│   ├── base.html              # 基础布局（导航栏+页脚）
│   ├── auth/                  # 认证相关页面
│   ├── course/                # 课程相关页面
│   ├── booking/               # 预约相关页面
│   ├── chat/                  # 聊天页面
│   ├── review/                # 评价页面
│   ├── parent/                # 家长页面
│   ├── payment/               # 支付页面
│   └── admin/                 # 管理后台页面
└── static/                    # 静态资源
    ├── css/style.css
    └── js/main.js
```

### 3.2 Blueprint 路由前缀

| Blueprint | URL 前缀 | 说明 |
|-----------|----------|------|
| auth | `/auth` | 注册/登录/登出 |
| course | `/course` | 课程 CRUD + 搜索 |
| booking | `/booking` | 预约管理 |
| chat | `/chat` | 聊天界面 |
| review | `/review` | 评价系统 |
| parent | `/parent` | 家长专属 |
| payment | `/payment` | 模拟支付 |
| admin | `/admin` | 管理后台 |

### 3.3 导航设计（按角色）

登录后根据角色显示不同导航：

| 角色 | 导航菜单 |
|------|----------|
| 学生 | 首页 · 找课程 · 我的预约 · 我的消息 · 我的评价 |
| 教师 | 首页 · 我的课程 · 预约管理 · 我的消息 · 我的评价 |
| 家长 | 首页 · 绑定学生 · 学习记录 · 消费记录 |
| 管理员 | 首页 · 教师审核 · 用户管理 · 数据仪表盘 |

---

## 4. 数据模型

### 4.1 User（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| username | String(80) unique | 用户名 |
| email | String(120) unique | 邮箱 |
| password_hash | String(256) | 密码哈希 |
| role | String(20) | student / teacher / parent / admin |
| phone | String(20) | 手机号 |
| avatar | String(256) | 头像URL，默认值 |
| created_at | DateTime | 注册时间 |

### 4.2 TeacherProfile（教师资料表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| user_id | Integer (FK→User) | 关联用户 |
| subjects | String(256) | 擅长科目（逗号分隔） |
| bio | Text | 个人简介 |
| hourly_rate | Float | 每小时收费 |
| education | String(256) | 教育背景 |
| verified | Boolean | 是否通过审核，默认False |
| rating_avg | Float | 平均评分，默认0.0 |

### 4.3 Course（课程表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| teacher_id | Integer (FK→User) | 授课教师 |
| title | String(200) | 课程标题 |
| subject | String(50) | 科目分类 |
| description | Text | 课程描述 |
| price | Float | 课程价格 |
| duration | Integer | 时长（分钟） |
| status | String(20) | active / inactive |
| created_at | DateTime | 创建时间 |

### 4.4 Booking（预约表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| student_id | Integer (FK→User) | 学生 |
| course_id | Integer (FK→Course) | 课程 |
| scheduled_time | DateTime | 预约上课时间 |
| status | String(20) | pending / confirmed / cancelled / completed |
| created_at | DateTime | 创建时间 |

### 4.5 Message（消息表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| sender_id | Integer (FK→User) | 发送者 |
| receiver_id | Integer (FK→User) | 接收者 |
| booking_id | Integer (FK→Booking) | 关联预约（nullable） |
| content | Text | 消息内容 |
| sent_at | DateTime | 发送时间 |

### 4.6 Review（评价表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| booking_id | Integer (FK→Booking) | 关联预约 |
| student_id | Integer (FK→User) | 评价学生 |
| teacher_id | Integer (FK→User) | 被评教师 |
| rating | Integer | 评分 1-5 |
| comment | Text | 评论内容 |
| created_at | DateTime | 评价时间 |

### 4.7 ParentStudent（家长-学生绑定表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| parent_id | Integer (FK→User) | 家长 |
| student_id | Integer (FK→User) | 学生 |
| bound_at | DateTime | 绑定时间 |

唯一约束：(parent_id, student_id)

### 4.8 Payment（支付表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 主键 |
| booking_id | Integer (FK→Booking) | 关联预约 |
| student_id | Integer (FK→User) | 付款学生 |
| amount | Float | 支付金额 |
| status | String(20) | pending / paid / refunded |
| paid_at | DateTime | 支付时间 |

---

## 5. 用户流程

### 5.1 学生核心流程
注册(学生) → 搜索/浏览课程 → 查看课程详情 → 提交预约(选时间) → 模拟支付 → 教师确认 → 在线聊天 → 课后评价

### 5.2 教师核心流程
注册(教师) → 完善资料(科目/时薪/简介) → 发布课程 → 查看预约列表 → 确认/拒绝预约 → 授课 → 与学生沟通 → 获得评价

### 5.3 家长核心流程
注册(家长) → 输入学生用户名绑定 → 查看学生的预约记录 → 查看消费明细

### 5.4 管理员核心流程
登录(admin) → 审核教师(通过/驳回 verified) → 查看数据仪表盘(用户数/课程数/营收)

---

## 6. 5人分工

| 成员 | 负责模块 | 核心任务 |
|------|----------|----------|
| 成员1 | auth + models + 脚手架 | `app.py`、`config.py`、`models.py`、auth Blueprint、`base.html` 模板 |
| 成员2 | course + review | 课程 CRUD + 搜索过滤 + 评价评分 |
| 成员3 | booking + payment | 预约流程(创建/确认/取消/状态) + 模拟支付 |
| 成员4 | chat + parent | 聊天界面(轮询) + 家长绑定/查看记录 |
| 成员5 | admin + 前端统一 | 管理员后台 + 仪表盘图表 + Bootstrap 主题一致性 |

**关键依赖**：
- 成员1 必须第一优先完成 models.py 和 auth（其他人开发依赖这两个基础）
- course 模块完成 → booking 可对接；booking 完成 → payment/chat/review 可对接
- parent 和 admin 相对独立，可最早并行开发

---

## 7. 4天开发计划

| 阶段 | 时间 | 内容 |
|------|------|------|
| **基础搭建** | 周一上午 | 成员1完成 models.py + auth + 脚手架；其他人熟悉模型代码 |
| **并行开发** | 周一下午→周二全天 | 5人各自开发分配的 Blueprint + 模板 |
| **集成联调** | 周三上午 | 合并代码，走通全流程，修复接口对接问题 |
| **测试修复** | 周三下午 | 全角色流程测试，修 bug，填充演示数据 |
| **PPT+演示** | 周三晚→周四 | 制作PPT，准备演示脚本，彩排 |

---

## 8. 关键设计决策

1. **模拟支付而非真实支付** — 点击"支付"后直接标记为已支付，无需接入第三方
2. **聊天用轮询(3秒)** — 避免 Flask-SocketIO 的额外复杂度，5人团队不需要
3. **管理员账号预设** — 通过 seed 脚本创建 admin 账号，不开放管理员注册
4. **Bootstrap + 简单CSS** — 不做花哨UI，确保功能完整可用
5. **不做视频授课** — 确认移除，降低复杂度
6. **无分页(第一版)** — 数据量小，列表页直接全量展示
7. **所有表单不做前端JS校验** — 仅后端 Flask-WTF 校验，减少前端工作量

---

## 9. 演示场景建议

答辩时演示以下完整链路（约5分钟）：

1. 教师注册 → 登录 → 完善资料 → 发布一门"Python基础"课程
2. 学生注册 → 登录 → 搜索"Python" → 找到课程 → 提交预约
3. 教师登录 → 查看预约 → 点击"确认"
4. 学生端 → 模拟支付 → 进入聊天 → 发送消息
5. 教师端 → 查看消息并回复
6. 课程完成后 → 学生提交 5星评价
7. 家长注册 → 绑定学生 → 查看学习消费记录
8. 管理员登录 → 审核新注册教师 → 查看仪表盘

---

## 10. 依赖清单 (requirements.txt)

```
Flask==3.1.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.2
WTForms==3.2.1
email-validator==2.2.0
```

---

## 11. 风险与应对

| 风险 | 应对 |
|------|------|
| 集成时模块接口不匹配 | 提前在 models.py 中定义好所有关系，路由命名遵循 RESTful 约定 |
| 某成员进度落后 | admin/parent 模块相对独立，可优先裁减不影响主流程 |
| 答辩演示出bug | 准备预录 GIF + 本地 seed 数据确保环境稳定 |
| 5人 Git 冲突 | 每人只改自己的 Blueprint 目录和模板子目录，不碰他人文件 |
