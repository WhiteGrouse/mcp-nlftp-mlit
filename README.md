# MCP Server for 国土数値情報
国土数値情報（国土交通省提供）へのアクセスを提供するModel Context Protocol（MCP）サーバーです。[国土数値情報ダウンロードサイト](https://nlftp.mlit.go.jp/ksj/index.html)から公開されている地理空間データを簡単に検索・取得・活用できます。

[MotherDuck](https://github.com/motherduckdb/mcp-server-motherduck)や[Filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)といったMCPと組み合わせることで、ダウンロードからParquetやGeoJSONへの変換までを自動で動かすことも可能です。
変換後は[kepler.gl](https://kepler.gl/)で可視化しましょう！

スクレイピングの観点、LLMの入出力トークンの節約から事前にキャッシュを生成します。
その過程でClaudeを使った要約を行うためAnthropicのAPI Keyを用意してください。

## API
- **list_datasets** データセットのリストを取得
- **get_details** 指定したデータセットの詳細情報を取得
- **get_available_files** 指定したデータセットのダウンロード可能なファイルのリストを取得
- **download** 指定したファイルを指定したフォルダにダウンロード&解凍

## Setup
```
git clone https://github.com/WhiteGrouse/mcp-nlftp-mlit.git
cd mcp-nlftp-mlit
uv sync
```

update_cache.py冒頭のANTHROPIC_API_KEYにAPI Keyを記入してください。

※以前動かした際には7ドル弱かかりました。130個以上あるのでかなり時間かかります。

```
# キャッシュを生成、更新
uv run update_cache.py
```

## Example
```
国土数値情報から地価をダウンロードしてduckdbを使ってparquetにしたい。 ファイルはC:\Users\User\Desktop\地価に保存して。わからないことがあれば質問して。
```