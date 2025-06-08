import asyncio
from aiohttp import ClientSession, ClientTimeout
from bs4 import BeautifulSoup, Tag
from anthropic import AsyncAnthropic
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import json
import csv
import shutil
import os
import sys
sys.dont_write_bytecode = True
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ANTHROPIC_API_KEY = "Your API KEY"

async def get(session: ClientSession, url: str, headers=None, encoding="utf-8") -> str:
  async with session.get(url, headers=headers) as res:
    return (await res.read()).decode(encoding)

async def _llm_extract_metadata(html: BeautifulSoup) ->  str:
  async with AsyncAnthropic(api_key=ANTHROPIC_API_KEY) as client:
    info_html = str(html.find("li", class_="active"))
    prompt = Path("llm_tmpl/extract_metadata.tmpl").read_text("utf-8")
    message = await client.messages.create(
      model="claude-3-7-sonnet-20250219",
      temperature=0,
      max_tokens=8192,
      messages=[
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": prompt,
            },
            {
              "type": "text",
              "text": info_html,
            }
          ],
        }
      ],
    )
    metadata_markdown = message.content[0].text
    return metadata_markdown

def _extract_file_info(node: Tag):
  # javascript:DownLd('0.01MB','L03-b-14_3036.zip','/ksj/gml/data/L03-b_r/L03-b_r-14/L03-b-14_3036.zip' ,this);
  # javascript:DownLd_new
  js = node["onclick"]

  params_str = js[js.index("(")+1:-2]
  size, filename, path, _ = json.loads("[" + params_str.replace("this", "'this'").replace("'", '"') + "]")
  url = urljoin("https://nlftp.mlit.go.jp/ksj/gml/datalist/dummy.html", path)
  info = ",".join([
    td.text.replace("\n", "").strip()
    for td in node.find_parent("tr").find_all("td", recursive=False)
  ]).replace(",file_downloadstar,", "")

  return [filename, url, info]

def clear_cache():
  shutil.rmtree("cache")
  os.mkdir("cache")

async def main():
  clear_cache()
  cache_dir = Path("cache")
  html_dir = cache_dir / "html"
  html_dir.mkdir()
  metadata_dir = cache_dir / "metadata"
  metadata_dir.mkdir()
  files_dir = cache_dir / "files"
  files_dir.mkdir()

  (cache_dir / "created_at.txt").write_text(datetime.now().strftime("%Y%m%d%H%M%S"))

  url = "https://nlftp.mlit.go.jp/ksj/index.html"
  timeout = ClientTimeout(total=30*60)
  async with ClientSession(timeout=timeout) as session:
    res = await get(session, url)
    (html_dir / "index.html").write_text(res, encoding="utf-8")
    html = BeautifulSoup(res, "html.parser")

    # ./gml/datalist/KsjTmplt-*.html
    datasets = [
        (node["href"][24:-5], node.text.strip())
        for node in html.find_all("a", href=True)
        if node.string == node.text and "datalist/Ksj" in node["href"]
    ]
    with open("cache/datasets.csv" ,"w", encoding="utf-8") as f:
      writer = csv.writer(f)
      for dataset in datasets:
        writer.writerow(dataset)

    for id, _ in tqdm(datasets):
      url = f"https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-{id}.html"
      res = await get(session, url)
      (html_dir / f"{id}.html").write_text(res, encoding="utf-8")
      html = BeautifulSoup(res, "html.parser")
      files = [_extract_file_info(a) for a in html.select('a[onclick^="javascript:DownLd"]')]
      (files_dir / f"{id}_files.csv").write_text("\n".join([file[2] for file in files]), encoding="utf-8")
      links = [{"filename": file[0], "url": file[1]} for file in files]
      (files_dir / f"{id}_links.json").write_text(json.dumps(links), encoding="utf-8")
      tqdm.write(f"generating metadata for {id}...")
      metadata = await _llm_extract_metadata(html)
      (metadata_dir / f"{id}.md").write_text(metadata)

asyncio.run(main())
