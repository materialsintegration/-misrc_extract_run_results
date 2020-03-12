# 入出力ファイル一括取得プログラム

当プログラムは機械学習用に指定したワークフローの計算結果を取得する。

## 概要　

このプログラムは二段階で実行する。まず、ワークフローIDを指定してこのワークフローを実行したランの情報を全て取得する。その後その情報からラン毎の入出力ファイル内容を取得する。

必要なものは以下となる。

* ワークフローID
* APIトークンまたはログイン情報
* siteID
* 入出力情報の変換対応テーブル

## システム構成

本スクリプトを実行するために必要なシステム構成を記述する。

* OS
  + python3.6が実行できれば特定のOSに縛られない。
* python
  + Version3.6以降
  + requests package
  + misrc_workflow_python_lib(from gitlab)


## 使い方

本プログラムは２段階で使用する。そのためにmodeをしてする必要がある。modeによって与えるパラメータも違ってくる。

下記ヘルプの補足である。

* modeの指定:基本的には初回、mode:iourlで実行し、正常終了すれば、mode:fileで目的のCSVファイルを作成する。
* therad : 情報はラン毎に取得するので並列化が可能である。このための並列数を指定する。ただしシステム的な上限があるので、１０から２０くらいが妥当である。
* reload : 初めてmode:iourlを実行する時は全ラン情報のなかから指定されたワークフローのランを取得するので、時間がかかる。reoadを指定しない場合、ワークフローのラン情報のみをキャッシュファイルに保存する。二回め以降、reloadを指定すれば、このキャッシュを元に情報収集が行われるので実行時間の短縮が期待できる。ただしキャッシュ作成後の新たなランの情報は再取得するしか方法はない。
* conf : 後述する。
* table : 後述する。

## confパラメータ詳細

いくつかのパラメータを書いておける。現状は以下のようなパラメータに対応している。

フォーマットはJSON形式。

```
{
"token":"13bedfd69583faa62be240fcbcd0c0c0b542bc92e1352070f150f8a309f441ed",
"misystem":"dev-u-tokyo.mintsys.jp",
"siteid":"site00002",
"workflow_id":"W000020000000197",
"csv_file":"W000020000000197.csv",
"table":"result_table_W000020000000197.conf",
"dat":"W000020000000197.dat"
}
```

## tableパラメータ詳細

mode:iourlで取得したCSVの内容からヘッダーに対応する項目の扱いを設定する。

```
{
"ニッケル熱処理計算のカウント数":{"filetype":"delete", "default":"None"},
"初期組成":{"filetype":"csv", "default":"1.306e-001"},
"平衡組成":{"filetype":"csv", "default":"2.375e-001"},
"析出相の体積分率":{"filetype":"csv", "default":"0.165"},
"等温時効":{"filetype":"csv", "default":"973.0"},
"計算時間":{"filetype":"csv", "default":"0.002"},
"計算領域のサイズ":{"filetype":"csv", "default":"1.0E-06"},
"オーダーパラメータ":{"filetype":"delete", "default":"None"},
"オーダーパラメータ時間発展":{"filetype":"delete", "default":"None"},
"オーダーパラメータ画像配置場所":{"filetype":"delete", "default":"None"},
"ニッケル熱処理計算の結果をまとめたファイル":{"filetype":"delete", "default":"None"},
"ニッケル熱処理計算の結果ファイル":{"filetype":"delete", "default":"None"},
"濃度場":{"filetype":"delete", "default":"None"},
"濃度場時間発展":{"filetype":"delete", "default":"None"},
"濃度場画像配置場所":{"filetype":"delete", "default":"None"}
}
```

ヘッダーをキーに、filetypeキーとdefaultキーを設定します。

* filetypeキー：deleteは削除する。csvはdatに記載することを示す。
* defaultキー ：None以外が書いてあればそれが採用される。

フォーマットはJSONである。

## ヘルプの表示

```
ワークフローIDの計算結果データを取得する。

Usage:  $ python run_results_m.py workflow_id:Mxxxx token:yyyy misystem:URL mode:[iourl/file] [options]

必須パラメータ
               mode   : 動作モード。
                        iourl : 計算結果データをGPDBへのURLとして取得し、
                        入出力名をヘッダーとしたランIDごとのCSVファイルを作成する。
                        file : iourlモードで作成したテーブルと別途用意した構成ファイルを使い、
                        機械学習向けのCSVファイルを作成する。 
                csv   : iourlモードで作成されるCSVファイルの名前
                        fileモードではiourlモードで作成したCSVとして指定する。
              thread  : API呼び出しの並列数（デフォルト10個）
               conf   : いくつかのパラメータを書いておける便利な構成ファイル
                        README.mdを参照
mode を iourlと指定したとき
          workflow_id : Mで始まる15桁のワークフローID
               token  : 64文字のAPIトークン
             misystem : dev-u-tokyo.mintsys.jpのようなMIntシステムのURL
              siteid  : siteで＋５桁の数字。site00002など
              reload  : 一度実行すればキャッシュが作成される。次回以降キャッシュから読み込みたい場合に指定する。
mode を fileと指定したとき
               table  : iourlで取得したGPDB情報を変換するテーブルの指定
                dat   : fileモードで作成される結果ファイル。機械学習用
```

