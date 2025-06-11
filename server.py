from mcp.server.fastmcp import FastMCP
import asyncio
from aiohttp import ClientSession
from pathlib import Path
from typing import Tuple
import json
import shutil
import subprocess
import os
import sys
sys.dont_write_bytecode = True
os.chdir(os.path.dirname(os.path.abspath(__file__)))

mcp = FastMCP("国土数値情報ダウンロードサイト")

cache_dir = Path("cache")

@mcp.tool(description="ダウンロード可能なデータの一覧を取得")
def list_data() -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  return (cache_dir / "datasets.csv").read_text("utf-8")

@mcp.tool(description="指定したデータの詳細情報を取得")
def get_details(id: str) -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  
  path = cache_dir / f"metadata/{id}.md"
  if not path.exists():
    return "[ERROR] 指定されたデータが見つかりません"
  return path.read_text("utf-8")

@mcp.tool(description="""\
指定したデータにおけるダウンロード可能なファイルの一覧を取得。
各データの内容は、年度別に整備されており、全国一括のほか地方別や都道府県別に分割して提供されています。
そのため、まずはユーザにどの年度で、どの地域のデータをダウンロードするのか質問するべきです。
通常zipファイルとして提供されており、その中にシェープファイル形式やGML形式、GeoJSON形式のファイルが含まれています。
このツールの結果は長大な可能性があるため、慎重に使用を計画してください。""")
def get_available_files(id: str) -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  
  path = cache_dir / f"files/{id}_files.csv"
  if not path.exists():
    return "[ERROR] 指定されたデータが見つかりません"
  return path.read_text("utf-8")

async def _download(session: ClientSession, id: str, filename: str, output_dir: Path) -> str:
  path = cache_dir / f"files/{id}_links.json"
  if not path.exists():
    return f"[ERROR] 指定されたデータ({id})が見つかりません"
  files = json.loads(path.read_text("utf-8"))
  url = next((file["url"] for file in files if file["filename"] == filename), None)
  if url is None:
    return f"[ERROR] 指定されたファイル({filename})が見つかりません"
  
  zipfile = output_dir / filename
  extract_dir = zipfile.with_suffix("")
  with zipfile.open("wb") as f:
    async with session.get(url) as res:
      while True:
        chunk = await res.content.read(128)
        if not chunk:
          break
        f.write(chunk)
  shutil.unpack_archive(zipfile, extract_dir)
  return "OK"

@mcp.tool(description="""\
国土数値情報から単一のzipファイルをダウンロードしてさらに解凍する。
ユーザによる明示的な出力先フォルダの指定が無い場合使用できない。
シェープファイル形式をGeoJSON形式やGeoParquet形式に変換するにはDuckDBを使うと良いでしょう。""")
async def download(id: str, filename: str, output_dir: str) -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  
  output_dir: Path = Path(output_dir)
  output_dir.mkdir(exist_ok=True)
  async with ClientSession() as session:
    return await _download(session, id, filename, output_dir)

@mcp.tool(description="国土数値情報から複数のzipファイルをダウンロードして全て解凍する。")
async def download_all(files: list[Tuple[str, str]], output_dir: str) -> str:
  if not cache_dir.exists():
    return "[ERROR] キャッシュが見つからないため取得できません"
  
  output_dir: Path = Path(output_dir)
  output_dir.mkdir(exist_ok=True)
  results = {}
  async with ClientSession() as session:
    parallel = 4
    cur = 0
    while cur < len(files):
      chunk = files[cur:min(cur + parallel, len(files))]
      tasks = [_download(session, id, filename, output_dir) for id, filename in chunk]
      chunk_results = await asyncio.gather(*tasks)
      results.update({filename: result for (_, filename), result in zip(chunk, chunk_results)})
      cur += parallel
  return json.dumps(results)


@mcp.tool(description="""\
Shift-JIS(CP932)のshpファイルをUTF-8に変換、上書きします。
シェープファイル形式のデータに関して、比較的新しい年度のものはUTF-8であることが多いが、Shift-JIS(CP932)も存在します。
既にUTF-8となっている場合、このツールを使うとデータが壊れてしまいます。
そのため、まずは対象ファイルのエンコーディングを別の方法を使って確認してください。""")
def convert_shpfile_sjis_to_utf8(shpfile: str) -> str:
  shpfile: Path = Path(shpfile)
  if shutil.which("ogr2ogr") is None:
    return "[ERROR] ogr2ogrコマンドが見つかりません"
  if not shpfile.exists():
    return "[ERROR] 変換対象のファイルが見つかりません"
  if shpfile.suffix != ".shp":
    return "[ERROR] 許可されていないファイル形式です"
  shp_dir = shpfile.parent
  tmpfile = shp_dir / "tmp.shp"
  i = 1
  while tmpfile.exists():
    tmpfile = shp_dir / f"tmp_{i}.shp"
    i += 1
  
  result = subprocess.run([
    "ogr2ogr", "-oo", "ENCODING=CP932", "-lco", "ENCODING=UTF-8", tmpfile, shpfile
  ], capture_output=True, text=True)
  if result.returncode != 0:
    raise result.stderr
  if not tmpfile.exists():
    raise "変換に失敗しました"
  for p in shp_dir.glob(f"{shpfile.stem}.*"):
    p.unlink(missing_ok=True)
  for p in shp_dir.glob(f"{tmpfile.stem}.*"):
    p.replace(p.with_name(f"{shpfile.stem}{p.suffix}"))
  return "OK"

@mcp.tool(description="convert_shpfile_sjis_to_utf8の複数ファイルバージョン")
def convert_shpfile_all_sjis_to_utf8(shpfiles: list[str]) -> str:
  return json.dumps({shpfile: convert_shpfile_sjis_to_utf8(shpfile) for shpfile in shpfiles})

@mcp.tool(description="同様のデータ構造を持つシェープファイルやGeoJSONファイルを1つに結合するDuckDBのSQLを生成します")
def generate_merge_sql(files: list[str]):
  return "UNION ALL\n".join([f"SELECT * FROM ST_Read('{file}')\n" for file in files])

if __name__ == "__main__":
  mcp.run(transport="stdio")
