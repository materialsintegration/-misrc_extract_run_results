# 入出力ファイル一括取得プログラム

当プログラムは機械学習用に指定したワークフローの計算結果を取得する。

## 概要　

このプログラムは二段階で実行する。まず、ワークフローIDを指定してこのワークフローを実行したランの情報を全て取得する。その後その情報からラン毎の入出力ファイル内容を取得する。

必要なものは以下となる。

* ワークフローID
* APIトークンまたはログイン情報
* 環境名
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
詳細は、[リポジトリのWIKIページ](https://gitlab.mintsys.jp/midev/extract_run_results/-/wikis/%E5%8B%95%E4%BD%9C%E4%BB%95%E6%A7%98)を参照。

### 使い方の例
* IOURL取得
```
$ python3.6 ~/extract_run_results/run_results_m.py token:６４文字のトークン misystem:dev-u-tokyo.mintsys.jp workflow_id:W000020000000300 mode:iourl csv:results.csv siteid:site00002
```
* 編集
```
$ vi table_template.tbl
```
* 機械学習データ構築
```
$ python3.6 ~/extract_run_results/run_results_m.py mode:file csv:results.csv table:table_template.tbl dat:W000020000000300.csv
```
 
## ヘルプの表示

```
ワークフローIDの計算結果データを取得する。

Usage:  $ python /home/misystem/extract_run_results/run_results_m.py workflow_id:Mxxxx token:yyyy misystem:URL mode:[iourl/file] [options]

必須パラメータ
               mode   : 動作モード。
                        iourl : 計算結果データをGPDBへのURLとして取得し、
                        入出力名をヘッダーとしたランIDごとのCSVファイルを作成する。
                        file : iourlモードで作成したテーブルと別途用意した構成ファイルを使い、
                        機械学習向けのCSVファイルを作成する。 
                csv   : iourlモードで作成されるCSVファイルの名前
                        fileモードではiourlモードで作成したCSVとして指定する。
               conf   : いくつかのパラメータを書いておける便利な構成ファイル
                        README.mdを参照

     mode を iourlと指定したとき
          workflow_id : Mで始まる15桁のワークフローID
               token  : 64文字のAPIトークン
             misystem : dev-u-tokyo.mintsys.jpのようなMIntシステムのURL
              siteid  : siteで＋５桁の数字。site00002など
              thread  : API呼び出しの並列数（デフォルト10個）
             usecash  : 次回以降キャッシュから読み込みたい場合に指定する。
                        未指定で実行すればキャッシュは作成される。

     mode を fileと指定したとき
               table  : iourlで取得したGPDB情報を変換するテーブルの指定
                dat   : fileモードで作成される結果ファイル。機械学習用

```

