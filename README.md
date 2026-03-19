# RedbookAuto

定时从本地队列发布小红书图文（macOS + MCP）。

## 方案概览
本项目使用 MCP 的 CLI 工具发布小红书图文内容，并通过 `launchd` 在每天固定时间触发发布。
默认配置使用 `xhs-mcp`（npm）作为发布引擎；你也可以替换为其他 MCP 实现（如 Python 版）。

## 一次性准备
1. 安装 Node.js（用于 `npx`）。
2. 首次登录（需要人工扫码一次）：
```
sh
npx xhs-mcp login --timeout 120
```
3. 准备内容队列（见下文）。

`xhs-mcp` CLI 支持登录、状态检查和图文发布。

## 队列结构
把待发布内容放到 `queue/pending/` 下，每条内容一个目录：
```
queue/pending/
  2026-02-04_0800_sample/
    meta.json
    1.jpg
    2.jpg
```

`meta.json` 示例：
```json
{
  "title": "标题示例",
  "content": "正文示例",
  "tags": ["tag1", "tag2"],
  "images": ["1.jpg", "2.jpg"]
}
```

说明：
- `images` 可省略。省略时会自动扫描该目录下的图片文件（jpg/jpeg/png/gif/webp）。
- `images` 既可写相对路径，也可写绝对路径。

## 运行方式

### 手动测试发布
手动运行一次（用于测试）：
```sh
python3 publisher/run_once.py
```

### 发布模式选择
工具支持两种发布模式：

**1. 直接发布（默认）**
内容会立即发布到小红书：
```sh
npx xhs-mcp publish --title "标题" --content "内容" --images "图片1.jpg,图片2.jpg"
```

**2. 暂存草稿**
内容会保存为草稿，稍后可在小红书后台手动发布：
```sh
npx xhs-mcp publish --title "标题" --content "内容" --images "图片1.jpg,图片2.jpg" --draft
```

> 提示：使用 `--draft` 参数时，工具会自动点击"暂存离开"按钮，内容不会立即发布。

## 定时发布（macOS launchd）
本项目自带 `launchd` 配置模板（每天 08:00 和 15:00）。如移动仓库路径，需要同步修改 `launchd/com.redbookauto.publisher.plist` 与 `scripts/*.sh` 内的绝对路径。
安装：
```
sh
./scripts/install_launchd.sh
```

卸载：
```
sh
./scripts/uninstall_launchd.sh
```

日志：
- 发布日志：`logs/publisher.log`
- launchd 输出：`logs/launchd.out.log` / `logs/launchd.err.log`

## 切换到 Python 版 MCP（可选）
若你更想使用 Python 版 MCP，可在 `config.json` 里替换 `publish.command`。
Python 版 MCP 的 CLI 发布方式如下（参考）：
```
sh
uv run xiaohongshu-publish \
  --title "我的标题" \
  --content "这是正文内容" \
  --images "image1.jpg" "image2.png"
```
