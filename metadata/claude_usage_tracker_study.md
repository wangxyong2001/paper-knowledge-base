# Claude Usage Tracker 学习笔记

> 项目地址: https://github.com/hamed-elfayome/Claude-Usage-Tracker
> 学习日期: 2026-05-24

---

## 一、项目概述

**定位**: macOS原生菜单栏应用，实时监控Claude AI使用限制

**技术栈**:
- Swift 5.0+
- SwiftUI 5.0+
- macOS 14.0+ (Sonoma)

**版本**: v3.1.1 (2026-04-14)

**特色**:
- 原生Swift/SwiftUI实现
- 官方签名 + 自动更新
- ~6MB轻量级
- 支持13种语言

---

## 二、核心功能

### 2.1 监控能力

| 功能 | 说明 |
|-----|------|
| **Session监控** | 5小时会话窗口追踪 |
| **Weekly限制** | 每周使用限制监控 |
| **Opus消耗** | Opus专属消费追踪 |
| **API成本** | API调用成本统计 |
| **使用历史** | 交互式图表展示 |

### 2.2 多账户管理

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Multi-Profile架构                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ├─ 无限账户管理                                                                │
│  ├─ 隔离凭证存储                                                                │
│  ├─ 独立设置配置                                                                │
│  ├─ 菜单栏同步显示                                                              │
│  └─ Claude Code集成 (CLI账户同步)                                               │
│                                                                                 │
│  Profile切换:                                                                   │
│  ├─ 手动切换                                                                    │
│  ├─ 自动切换                                                                    │
│  └─ CLI凭证联动                                                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Statusline集成

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Terminal Statusline设计                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  显示元素:                                                                      │
│  ├─ 目录 (directory)                                                            │
│  ├─ 分支 (branch)                                                               │
│  ├─ 模型 (model)                                                                │
│  ├─ 上下文 (context)                                                            │
│  ├─ Profile指示                                                                 │
│  ├─ Weekly使用段                                                                │
│  ├─ Extra使用段                                                                 │
│  └─ Pace标记 (6-tier pace system)                                              │
│                                                                                 │
│  颜色模式:                                                                      │
│  ├─ Multi-Color (多彩)                                                          │
│  ├─ Greyscale (灰度)                                                            │
│  └─ Single Color (单色)                                                         │
│                                                                                 │
│  自定义:                                                                        │
│  ├─ 每元素颜色定制                                                              │
│  ├─ Remaining/Used百分比切换                                                    │
│  └─ Peak Hours火焰图标                                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Peak Hours指示器 (v3.1.0新功能)

- 火焰图标 + 倒计时popover
- 高峰时段可视化提醒
- 右键上下文菜单

---

## 三、技术架构

### 3.1 代码结构

```
Claude Usage/
├── App/                     # 应用核心
│   ├── AppDelegate.swift
│   └── ClaudeUsageTrackerApp.swift
│
├── MenuBar/                 # 菜单栏UI
│   ├── MenuBarIconRenderer.swift    # 图标渲染
│   ├── MenuBarManager.swift         # 状态管理
│   ├── PeakHoursPopoverView.swift   # 高峰时段
│   ├── PopoverContentView.swift     # Popover内容
│   ├── StatusBarUIManager.swift     # UI管理
│   ├── UsageRefreshCoordinator.swift # 刷新协调
│   └── WindowCoordinator.swift      # 窗口协调
│
├── Views/                   # 视图层
│   ├── APISettingsView.swift
│   ├── FeedbackPromptView.swift
│   ├── GitHubStarPromptView.swift
│   ├── Settings/
│   ├── SettingsView.swift
│   ├── SetupWizardView.swift
│
├── Shared/                  # 共享模块
├── Resources/               # 资源文件
└── Assets.xcassets         # 图片资源
```

### 3.2 设计模式

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    核心设计模式                                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. Coordinator模式                                                            │
│     ├─ UsageRefreshCoordinator: 刷新协调                                       │
│     ├─ WindowCoordinator: 窗口协调                                              │
│     └─ StatusBarUIManager: UI管理                                              │
│                                                                                 │
│  2. Manager模式                                                                │
│     ├─ MenuBarManager: 菜单栏状态管理                                           │
│     ├─ 统一管理状态变化                                                         │
│     └─ 协调UI更新                                                               │
│                                                                                 │
│  3. Renderer模式                                                               │
│     ├─ MenuBarIconRenderer: 图标渲染                                           │
│     ├─ 分离渲染逻辑                                                             │
│     └─ 支持多种图标样式                                                         │
│                                                                                 │
│  4. MVVM (SwiftUI标准)                                                         │
│     ├─ View: SwiftUI视图                                                       │
│     ├─ ViewModel: @Observable                                                   │
│     └─ Model: 数据结构                                                          │
│                                                                                 │
│  5. Singleton (App生命周期)                                                    │
│     ├─ AppDelegate: 应用生命周期                                                │
│     ├─ 全局状态管理                                                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 四、设计亮点

### 4.1 隐私优先

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Privacy-First设计                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ├─ 本地存储 (无云同步)                                                         │
│  ├─ Keychain安全存储                                                            │
│  ├─ 最小匿名分析 (仅版本心跳)                                                   │
│  └─ 无第三方数据收集                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 原生性能

- Swift/SwiftUI轻量设计
- ~6MB安装包
- 低CPU占用
- 内存高效

### 4.3 用户体验

| 特性 | 说明 |
|-----|------|
| **Global Shortcuts** | 系统级快捷键（无需Accessibility权限） |
| **Headless Mode** | 远程桌面支持 |
| **Auto-start** | 自动启动会话 |
| **Auto-switch** | 自动切换Profile |
| **Threshold Notifications** | 阈值通知 |
| **Customizable Interface** | 5种图标 + 3种颜色模式 |

### 4.4 国际化

支持13种语言：
- 🇬🇧 English
- 🇪🇸 Español
- 🇫🇷 Français
- 🇩🇪 Deutsch
- 🇮🇹 Italiano
- 🇵🇹 Português
- 🇧🇷 Português (BR)
- 🇯🇵 日本語
- 🇰🇷 한국어
- 🇨🇳 简体中文
- 🇹🇼 繁體中文
- 🇹🇷 Türkçe
- 🇺🇦 Українська

---

## 五、认证与安全

### 5.1 认证方式

| 方式 | 说明 | 难度 |
|-----|------|-----|
| **Claude Code OAuth** | CLI自动凭证 | 最简单 |
| **Browser Sign-In** | 内置浏览器提取 | 简单 |
| **Manual** | 手动提取Session Key | 复杂 |

### 5.2 Keychain集成

- 凭证安全存储
- Apple安全框架
- 加密保护

---

## 六、可借鉴设计

### 6.1 对论文知识库系统的启发

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    Claude Usage Tracker → 论文知识库借鉴                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  1. Statusline设计                                                             │
│     ├─ 多元素显示 (模型/上下文/仓库)                                            │
│     ├─ 颜色模式切换                                                             │
│     ├─ Pace标记系统                                                             │
│     └─ Peak Hours可视化                                                         │
│                                                                                 │
│     论文知识库应用:                                                              │
│     ├─ 显示检索状态 (检索中/完成)                                               │
│     ├─ 显示Token消耗                                                            │
│     ├─ 显示幻觉风险等级                                                         │
│     └─ 显示当前Agent角色                                                        │
│                                                                                 │
│  2. Coordinator模式                                                             │
│     ├─ UsageRefreshCoordinator → Agent状态协调                                 │
│     ├─ WindowCoordinator → 多窗口管理                                          │
│     └─ StatusBarUIManager → Dashboard UI                                       │
│                                                                                 │
│     论文知识库应用:                                                              │
│     ├─ RetrievalCoordinator: 检索协调                                          │
│     ├─ GenerationCoordinator: 生成协调                                         │
│     └─ QualityCoordinator: 质量检查协调                                        │
│                                                                                 │
│  3. 多Profile管理                                                               │
│     ├─ 隔离凭证 → 多用户支持                                                    │
│     ├─ 自动切换 → 上下文感知                                                    │
│     └─ CLI集成 → Claude Code联动                                               │
│                                                                                 │
│     论文知识库应用:                                                              │
│     ├─ 多论文项目隔离                                                          │
│     ├─ 多Agent角色切换                                                          │
│     └─ 云端/本地模型切换                                                        │
│                                                                                 │
│  4. 隐私优先设计                                                                │
│     ├─ 本地存储 → SQLite审计                                                    │
│     ├─ Keychain → 凭证安全                                                      │
│     └─ 最小分析 → 仅必要指标                                                    │
│                                                                                 │
│     论文知识库应用:                                                              │
│     ├─ 已实现: SQLite 14表审计                                                 │
│     ├─ 已实现: 本地Token审计                                                   │
│     └─ 可借鉴: Keychain API密钥存储                                            │
│                                                                                 │
│  5. 国际化架构                                                                  │
│     ├─ 13语言 → 多语言支持                                                      │
│     ├─ 本地化资源 → 结构化文档                                                  │
│                                                                                 │
│     论文知识库应用:                                                              │
│     ├─ Prompt模板多语言                                                         │
│     ├─ 输出格式本地化                                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 具体改进建议

| 模块 | Claude Usage Tracker设计 | 论文知识库改进 |
|-----|-------------------------|--------------|
| Statusline | Pace标记 + 颜色模式 | 添加Agent状态颜色指示 |
| Coordinator | 刷新协调器 | 添加RetrievalCoordinator |
| Profile | 多账户隔离 | 多论文项目隔离 |
| Keychain | 凭证安全存储 | API密钥Keychain存储 |
| Peak Hours | 高峰时段提示 | API成本高峰提醒 |

---

## 七、技术细节

### 7.1 Pace System (v3.0.3)

```
6-tier pace system:
├─ Very Slow (灰色)
├─ Slow (浅色)
├─ Normal (蓝色)
├─ Fast (绿色)
├─ Very Fast (黄色)
└─ Extreme (红色)
```

### 7.2 Icon Styles

```
5种图标样式:
├─ Circle
├─ Square
├─ Minimal
├─ Classic
└─ Custom
```

### 7.3 Color Modes

```
3种颜色模式:
├─ Multi-Color: 多彩
├─ Greyscale: 灰度
└─ Single Color: 单色
```

---

## 八、安装方式

| 方式 | 命令 |
|-----|------|
| **Homebrew** | `brew install --cask hamed-elfayome/claude-usage/claude-usage-tracker` |
| **Manual** | 下载 .dmg 安装 |
| **Nix** | nix package (v3.1.0+) |

---

## 九、版本演进

| 版本 | 主要功能 |
|-----|---------|
| v1.0 | 基础监控 |
| v2.0 | Apple签名 + 自动更新 |
| v2.2 | Multi-profile + CLI集成 |
| v2.3 | 菜单栏多Profile显示 |
| v3.0 | Headless + 历史图表 + 全局快捷键 |
| v3.0.2 | API成本追踪 + 浏览器认证 |
| v3.0.3 | 6-tier pace + 3颜色模式 |
| v3.1 | Peak Hours + 右键菜单 + 12语言 |

---

## 十、总结

**核心学习点**:

1. **SwiftUI原生开发** - 轻量高效
2. **Coordinator模式** - 状态协调最佳实践
3. **Statusline设计** - 多元素 + 颜色 + 标记
4. **隐私优先** - 本地存储 + Keychain
5. **国际化** - 13语言支持
6. **版本迭代** - 持续功能增强

**可应用到论文知识库**:

- Coordinator模式应用到Agent协调
- Statusline增强Agent状态显示
- Keychain存储API密钥
- Peak Hours思路应用到成本监控
- 多Profile思路应用到多项目隔离

---

*学习日期: 2026-05-24*