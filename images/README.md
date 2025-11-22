# 图像识别按钮图片目录

## ⚠️ 重要说明

**此应用使用自定义渲染，UI Automation 无法识别控件，必须使用图像识别！**

## 必须截取的图片

### 1. 公式搜索按钮（已完成 ✅）
- **文件名**：`search_formula_button.png`
- **位置**：主界面 → 时时彩标签下
- **状态**：已截取

### 2. 开始搜索按钮（必需 ❗）
- **文件名**：`start_search_button.png`
- **位置**：公式搜索界面 → 配置参数区域
- **作用**：点击后开始搜索
- **外观**：通常显示"开始搜索"或"搜索"

### 3. 其他可选图片

如果配置参数也无法通过 UI Automation 识别，可能需要：
- 输入框位置图片（用于定位点击）
- 下拉框图片

---

## 截图步骤

### 方法1：Windows 截图工具（推荐）
1. 打开应用到目标界面
2. 按 `Win + Shift + S`
3. 框选按钮区域（只截按钮本身）
4. 保存到 `d:\PC-Test\images\`

### 方法2：QQ/微信截图
1. 按 `Ctrl + Alt + A` (QQ)
2. 框选按钮
3. 保存到 `d:\PC-Test\images\`

---

## 图片要求

✅ **只截按钮本身**，不要包含周围空白  
✅ **文字清晰可读**  
✅ **PNG 格式**  
✅ **按照上面的文件名保存**

---

## 测试图像识别

截图完成后测试：

```bash
# 测试公式搜索按钮
python -c "import pyautogui; print(pyautogui.locateOnScreen('images/search_formula_button.png', confidence=0.8))"

# 测试开始搜索按钮
python -c "import pyautogui; print(pyautogui.locateOnScreen('images/start_search_button.png', confidence=0.8))"
```

如果返回坐标（如 `Box(left=307, top=291, width=129, height=109)`），说明可以识别。

---

## 当前状态

- ✅ `search_formula_button.png` - 已完成
- ❌ `start_search_button.png` - **待截取**

**请先截取"开始搜索"按钮，然后重新运行测试！**
