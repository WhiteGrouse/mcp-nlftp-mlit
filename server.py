from mcp.server.fastmcp import FastMCP
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
from pathlib import Path
import json
import os
import sys
sys.dont_write_bytecode = True
os.chdir(os.path.dirname(os.path.abspath(__file__)))

mcp = FastMCP("国土数値情報")

cache_dir = Path("cache")

@mcp.tool(description="データセットの一覧をcsv形式で取得")
def list_datasets() -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  return (cache_dir / "datasets.csv").read_text("utf-8")

@mcp.tool(description="データセットの詳細情報をマークダウン形式で取得")
def get_details(id: str) -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  
  path = cache_dir / f"metadata/{id}.md"
  if not path.exists():
    return "[ERROR] 指定されたデータセットが見つかりません"
  return path.read_text("utf-8")

@mcp.tool(description="ダウンロード可能なファイルの一覧を取得")
def get_available_files(id: str) -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  
  path = cache_dir / f"files/{id}_files.csv"
  if not path.exists():
    return "[ERROR] 指定されたデータセットが見つかりません"
  return path.read_text("utf-8")

@mcp.tool(description="データセットIDとファイル名からダウンロード用URLを取得")
def get_download_url(id: str, filename: str) -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  
  path = cache_dir / f"files/{id}_links.json"
  if not path.exists():
    return "[ERROR] 指定されたデータセットが見つかりません"
  files = json.loads(path.read_text("utf-8"))
  url = next((file["url"] for file in files if file["filename"] == filename), None)
  if url is None:
    return "[ERROR] 指定されたファイルが見つかりません"
  return url

if __name__ == "__main__":
  mcp.run(transport="stdio")
