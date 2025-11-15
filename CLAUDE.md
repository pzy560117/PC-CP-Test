# 项目配置文档

## 📚 项目资源概览

### 项目基本信息
- **项目名称**：<Project Name>
- **技术栈**：<Tech Stack>
- **项目类型**：<Backend | Frontend | Fullstack>

### 后端已有功能模块
| 模块 | 说明 | 位置 |
|------|------|------|
| <Module Name> | <Summary> | <path/to/module> |

### 前端已有页面
| 页面 | 路由 | 位置 |
|------|------|------|
| <Page Name> | </route> | <path/to/view> |

### 移动端已有页面
| 页面 | 路径 | 位置 |
|------|------|------|
| <Page Name> | pages/... | <path/to/page> |

## 🔧 开发规范

### 项目结构
- 运行逻辑：`src/<domain>`，按业务域划分
- 共用工具：`src/shared`
- 测试：`tests/` 镜像业务目录
- 静态：`assets/`
- 构建脚本：`scripts/`
- 文档：`docs/`

### 编码规范
- 默认语言：<TypeScript/Java/...>
- 缩进：2 空格；字符串使用 <单/双> 引号
- 文件名 kebab-case；类 PascalCase；函数/变量 camelCase；常量 SCREAMING_SNAKE_CASE
- 导出函数或类需在定义上方写 TSDoc 注释

### 测试规范
- 测试框架：<Jest/Vitest/...>
- 文件命名：`*.spec.<ext>`
- 覆盖率：行 >= 80%，分支 >= 75%

### 提交规范
- `type(scope): summary`
- 一次提交只包含单一逻辑

## 📝 项目管理命令
- `/start`：快速了解项目状态
- `/progress`：生成详细进度
- `/next`：得到下一步建议
- `/update-status`：更新项目状态文档
- `/init-docs`：初始化标准文档

> 详细说明参考 `.claude/commands/` 目录。
