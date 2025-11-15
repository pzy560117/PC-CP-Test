# /start - 快速了解项目状态

1. 识别项目类型与技术栈
   - 读取 CLAUDE.md / package.json / pom.xml
2. 查看最近 3 条 Git 提交
   - `git log -3 --oneline --date=relative`
3. 检查代码状态
   - `git status -sb`，列出未提交文件
4. 扫描业务模块
   - 查看后端/前端/移动端目录，统计模块数量
5. 统计 TODO/FIXME
   - `rg --no-heading --line-number "TODO|FIXME"`
6. 读取项目文档
   - `docs/项目状态.md`、`docs/待办清单.md`

## 输出格式
```
# 👋 欢迎回到项目

## 📂 项目信息
- 项目名称：<>
- 技术栈：<>
- 主要功能：<>

## 🕐 最近动态
- <commit1> - <time>
- <commit2> - <time>
- <commit3> - <time>

## 📊 当前状态
- 代码状态：✅ / ⚠️ (<文件列表>)
- 业务模块：<模块概览>
- TODO/FIXME：后端 X、前端 Y
- 框架状态：<稳定/开发中/待初始化>

## 🎯 你可以：
1. `/progress`
2. `/next`
3. “继续开发 <功能>”
```
