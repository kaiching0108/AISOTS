# AI Futures Trading System - 文檔目錄

本目錄包含 AISOTS 系統的完整技術文檔。

## 文檔結構

| 文件 | 說明 |
|------|------|
| [README.md](README.md) | 文檔目錄索引（本文件） |
| [AGENTS.md](../AGENTS.md) | Agent 開發指南（精簡版，~150 行） |
| [Features.md](Features.md) | 功能說明、模擬模式、策略管理 |
| [Web_Interface.md](Web_Interface.md) | Web 介面開發指南、API 端點 |
| [System_Architecture.md](System_Architecture.md) | 系統架構，技術堆疊 |
| [User_Manual.md](User_Manual.md) | 使用手冊、安裝指南 |
| [SQLite_Storage.md](SQLite_Storage.md) | SQLite 存儲規範、數據來源標記 |

## 文檔內容簡介

### AGENTS.md (精簡版)

提供 AI Agent 開發所需的關鍵資訊：
- Build/Lint/Test 指令
- Code Style Guidelines
- Strategy Framework 範例
- Backtest Engine 使用方式
- 重要筆記（Technical Indicators、LLM Strategy Generation）

### Features.md

系統功能詳細說明：
- 啟動方式（命令行參數）
- 模擬模式價格生成機制
- Fallback 命令處理機制
- 多策略管理、策略 ID 系統
- 策略驗證系統（兩階段驗證）
- LLM 策略生成功能
- 訊號記錄系統
- 績效分析
- Strategy Reviewer
- 策略優化流程
- 自動 LLM Review 排程
- 版本資訊

### Web_Interface.md

Web 介面開發完整指南：
- 系統需求與安裝
- 架構設計
- API 端點完整列表
- 前端模板說明
- 策略管理頁面功能
- 績效分析頁面功能
- 策略建立頁面功能
- 訂單查詢頁面功能
- 交易日誌功能
- 回測引擎 K 棒數量限制

### System_Architecture.md

系統架構深度解析：
- 系統目標與技術堆疊
- 8 層架構圖
- 各模組詳細說明
- 數據流設計
- 錯誤處理機制
- 安全性考量
- 部署建議

### User_Manual.md

用戶操作手冊：
- 安裝指南
- 快速開始
- 配置說明
- 策略撰寫教學
- 使用教學（命令列表）
- 故障排除
- FAQ

### SQLite_Storage.md

SQLite 存儲規範：
- Symbol Mapping 規則
- SQL 查詢規範
- API 方法總覽
- 數據來源標記（historical/initial/recovery/realtime）
- 實盤即時 K 棒寫入說明

## 快速連結

- [系統總覽](System_Architecture.md#1-系統概述)
- [啟動方式](Features.md#啟動方式)
- [策略建立流程](Web_Interface.md#策略建立頁面功能)
- [API 端點](Web_Interface.md#api-列表)
- [版本歷史](Features.md#13-版本資訊)
- [SQLite 存儲規範](SQLite_Storage.md)
