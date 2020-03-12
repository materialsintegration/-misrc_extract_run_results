# 入出力ファイル一括取得プログラム
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
mode を iourlと指定したとき
          workflow_id : Mで始まる15桁のワークフローID
               token  : 64文字のAPIトークン
             misystem : dev-u-tokyo.mintsys.jpのようなMIntシステムのURL
              siteid  : siteで＋５桁の数字。site00002など
              reload  : 一度実行すればキャッシュが作成される。次回以降キャッシュから読み込みたい場合に指定する。
mode を fileと指定したとき
               conf   : iourlで取得したGPDB情報を変換するテーブルの指定
                dat   : fileモードで作成される結果ファイル。機械学習用
```

