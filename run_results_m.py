#!/usr/local/python2.7/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) The University of Tokyo and
# National Institute for Materials Science (NIMS). All rights reserved.
# This document may not be reproduced or transmitted in any form,
# in whole or in part, without the express written permission of
# the copyright owners.

'''
ワークフローIDからランのリストを取得して、特定の作業をする(マルチセッション版)
'''

import sys, os
from glob import glob
import threading
import datetime
import pickle
import requests
import random
import time
import json

sys.path.append("/home/misystem/assets/modules/workflow_python_lib")
from workflow_runlist import *
from workflow_iourl import *

# 文字コード
CHARSET_DEF = 'utf-8'

counter_bar = ""

class debug_struct(object):
    '''
    デバッグ用のストラクチャー
    '''

    def __init__(self):
        '''
        '''

        self.text = None

def debug_random(from_value, to_value):
    '''
    '''

    random.seed(datetime.datetime.now())
    d = debug_struct()
    d.text = random.uniform(from_value, to_value)

    return d

def counterBar(count, nperiod, lines):
    '''
    カウンターバー進捗表示の更新
    @param count(int)
    @param nperiod(int)
    @param lines(int)
    @retval なし
    '''

    global counter_bar

    if (count % nperiod) == 0:
        counter_bar = counter_bar.replace("-", "*", 1)
        sys.stdout.write("\r%s [%d/%d]"%(counter_bar, count, len(lines)))
        sys.stdout.flush()

class job_get_iourl(threading.Thread):
    '''
    スレッドによる入出力ファイル一覧取得
    '''

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, daemon=None):
        '''
        コンストラクタ
        '''

        threading.Thread.__init__(self, group=group, target=target, name=name, daemon=daemon)
        self.token = args[0]
        self.url = args[1]
        self.siteid = args[2]
        self.runlist = args[3]
        self.thread_num = args[4]
        self.result = args[5]
        self.results = args[6]
        self.csv_log = args[7]
        self.run_status = args[8]
        self.list_num = len(self.runlist)
        self.status = {"canceled":"キャンセル", "failure":"起動失敗", "running":"実行中",
                       "waiting":"待機中", "paused":"一時停止", "abend":"異常終了"}

    def run(self):
        '''
        スレッド実行
        '''

        sys.stdout.write("%s -- %03d : %10d 個のランを処理します。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, self.list_num))
        sys.stderr.flush()
        i = 1
        results = []
        for run in self.runlist:
            if (i % 500) == 0:
                sys.stdout.write("%s -- %03d : %d 個処理しました。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, i))
                sys.stderr.flush()
            i += 1

            #if run["status"] == "completed":
            # if run["status"] != "canceled" and run["status"] != "failure":
            if run["status"] in self.run_status:
                self.csv_log.write("%s -- %03d : %sのランIDを処理中\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, run["run_id"]))
                self.csv_log.flush()
                ret, ret_dict = get_runiofile(self.token, self.url, self.siteid, run["run_id"], self.result, thread_num=self.thread_num, timeout=(2.0, 120.0))
                if ret is False:
                    self.csv_log.write(ret_dict)
                    self.csv_log.flush()
                    continue
                ret_dict[run["run_id"]]["description"] = run["description"]
                ret_dict[run["run_id"]]["status"] = run["status"]
                results.append(ret_dict)
            else:
                print("ラン番号(%s)は実行完了していない(%s)ので、処理しません。"%(run["run_id"], self.status[run["status"]]))
                self.csv_log.write("%s -- %03d : ラン番号(%s)は実行完了していない(%s)ので、処理しません。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, run["run_id"], self.status[run["status"]]))
                self.csv_log.flush()
                continue

        sys.stdout.write("%s -- %03d : %d 個処理終了しました。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, self.list_num))
        sys.stdout.flush()
        self.csv_log.write("%s -- %03d : %d 個処理終了しました。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, self.list_num))
        self.csv_log.flush()
        self.results[threading.current_thread().name] = results


def generate_csv(token, url, siteid, workflow_id, csv_file, tablefile, result, thread_num, load_cash, run_list, run_status):
    '''
    まずはGPDBからファイルの実体を取得するIOURLを取得し、CSVを作成する。
    @param token(string)
    @param url(string)
    @param siteid(string)
    @param workflow_id(string)
    @param csv_file(string)
    @param tablefile(string)
    @param result(string)
    @param thread_num(int)
    @param load_cash(bool)
    @param run_list(list)
    @param run_status(string)
    @retval なし
    '''
    # キャッシュを使う指定だが、キャッシュが無い場合、リスト取得へ
    if load_cash is True:
        if os.path.exists("run_result_cash.dat") is False:
            load_cash = False

    if load_cash is False:
        print("%s - ワークフローID(%s)の全ランのリストを取得します。"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), workflow_id))
        retval, ret = get_runlist(token, url, siteid, workflow_id, True)
        if retval is False:
            print("%s - ラン一覧の取得に失敗しました。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
            sys.exit(1)

        outfile = open("run_result_cash.dat", "wb")
        pickle.dump(ret, outfile)
        outfile.close()
        print("%s - 全ランのリストをキャッシュファイルに保存しました。"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")))
    else:
        print("%s - 全ランのリストをキャッシュファイルから取り出します。"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")))
        infile = open("run_result_cash.dat", "rb")
        ret = pickle.load(infile)
        infile.close()
    #print("%s - ランは %d ありました。"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), len(ret)))
    if run_list is not None:
        infile = open(run_list, encoding=CHARSET_DEF)
        lines = infile.read().split("\n")
        infile.close()
        run_list = []
        for runinfo in lines:
            if runinfo == "":
                continue
            run_list.append(runinfo.split()[3])

        newlist = []
        for item in ret:
            for run in run_list:
                if item["run_id"] == run:
                    newlist.append(item)
                    break
        ret = newlist

    print("%s - 対象となるランは %d ありました。"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), len(ret)))
    periodn = int(len(ret) / 80)
    results = []
    i = 1
    csv_log = open("create_csv.log", "w", encoding=CHARSET_DEF)

    # 指定した数で入出力ファイルURL一覧取得をスレッド処理する。
    ths = []
    results = {}
    init = 0
    num = num1 = int(len(ret) / thread_num)
    for i in range(thread_num):
        if i == thread_num - 1:
            runlist = ret[init:]
        else:
            runlist = ret[init:num1]
        init += num
        num1 += num
        t = job_get_iourl(args=(token, url, siteid, runlist, i + 1, result, results, csv_log, run_status))
        ths.append(t)
        t.start()
        time.sleep(1)

    # 実行待ち合わせ
    for th in ths:
        th.join()

    print("%s - ヘッダーとなる入出力ポート名を取り出しています。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    threads = list(results.keys())
    #sys.stderr.write("%s\n"%str(threads))
    headers = []
    for t in threads:
        #sys.stderr.write("%s - %s\n"%(t, results[t]))
        if len(results[t]) == 0:
            continue
        for runs in results[t]:
            for runid in runs:
                for item in runs[runid]:
                    if (item in headers) is False:
                        headers.append(item)

    if tablefile is not None:
        print("%s - tableファイルは作成しません。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    else:
        print("%s - tableファイルを作成しています。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        outfile = open("table_template.tbl", "w", encoding=CHARSET_DEF)
        outfile.write("{\n")
        outflg = False
        for i in range(len(headers)):
        #for item in headers:
            if headers[i] == "loop" or headers[i] == "description" or headers[i] == "status":
            #if item == "loop":
                continue
            #outfile.write('"%s":{"filetype":"csv", "default":"None", "ext":""},\n'%item)
            if outflg:
                outfile.write(",\n")
            # ===> 2021/03/02 JSON変換用にキーを増やす
            #outfile.write('"%s":{"filetype":"csv", "default":"None", "ext":""}'%headers[i])
            outfile.write('"%s":{"filetype":"csv", "default":"None", "ext":"", "bayes_type":"params", "param_name":"", "ratio":""}'%headers[i])
            # <=== 2021/03/02
    
            outflg = True
            # if i < len(headers) - 1:
            #     outfile.write(",\n")
        outfile.write("\n}\n")
        outfile.close()

    print("%s - ヘッダーは以下のとおりです。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    outfile = open(csv_file, "w", encoding=CHARSET_DEF)
    total_file_amount = {}
    out_dat = []
#    outfile.write("run_id          ,")
    out_dat.append("run_id          ")
    for item in headers:
#        outfile.write("%s,"%item)
        out_dat.append(item)
        sys.stderr.write("%s\n"%item)
        sys.stderr.flush()
        if item != "loop" and item != "description" and item != "status":
            total_file_amount[item] = 0
    outfile.write(','.join(out_dat))

    # 結果（JSON）の一時保存
    routfile = open("results_cach.dat", "w", encoding=CHARSET_DEF)
    json.dump(results, routfile, ensure_ascii=False, indent=4)
    routfile.close()

    print("%s - データファイル(CSV)を構築しています。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    #print("%s"%str(results))
    outfile.write("\n")
    out_dat = []
    excluded_num = 0
    for thread in results:
        for items in results[thread]:
            for item in items:
                isNoPorts = False                                   # ポートが不完全なランがあるとTrueとする
                for key in headers:
                    if (key in items[item]) is False:
                        sys.stderr.write("ランID(R%s)はヘッダー(%s)と同じポートがありませんでした。\n"%(item[1:], key))
                        sys.stderr.flush()
                        isNoPorts = True

                if isNoPorts is True:                               # 不完全なポートがあった
                    sys.stderr.write("ランID(R%s)はポート情報が不完全なのでリストから除外します。\n"%item[1:])
                    sys.stderr.flush()
                    excluded_num += 1
                    continue                                        # 次のランの処理へ
                for key in headers:
                    #print(item)
                    #print(str(items[item]))
                    # preチェック
                    if (key in items[item]) is True:
                        #print(key)
                        if key == "loop":
                            # outfile.write("%d,"%int(item[1:]))                   # run_idを先頭に記入
                            # outfile.write("%d"%items[item][key])
                            out_dat.append(str(item[1:]))
                            out_dat.append(str(items[item][key]))
                        elif key == "description":
                            # 改行コード、","を半角スペースに置換
                            out_dat.append(' '.join(items[item][key].replace(',', ' ').splitlines()))
                        elif key == "status":
                            out_dat.append(items[item][key])
                        else:
                            if items[item][key][0] == "null":
                                # outfile.write("null:0")
                                out_dat.append("null:0")
                            else:
                                # outfile.write("%s;%s"%(items[item][key][0], items[item][key][1]))
                                out_dat.append("%s;%s"%(items[item][key][0], items[item][key][1]))
                                if items[item][key][1] is None or items[item][key][1] == "None":
                                    pass
                                else:
                                    total_file_amount[key] += items[item][key][1] 
                    else:
                        out_dat.append("")
                    # outfile.write(",")

            if len(out_dat) != 0:
                outfile.write(','.join(out_dat))
                outfile.write("\n")
                out_dat = []

    outfile.close()
    print("%s - データファイル(CSV)を構築終了。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    if excluded_num != 0:
        print("%s - 除外されたデータは %d 個ありました。"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), excluded_num))
    print("%s - 予想される各パラメータのデータ量は以下のとおりです。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    units=["byte", "kbyte", "Mbyte", "Gbyte", "Tbyte"]
    for item in total_file_amount:
        amount = total_file_amount[item]
        units_count = 0
        while amount > 1024:
            amount /= 1024
            units_count += 1

        print("%s - %.2f(%s)"%(item, amount, units[units_count]))

    csv_log.close()

def generate_dat(conffile, csv_file, dat_file, workflow_id="", siteid=""):
    '''
    generete_csvで作成されたcsv_fileをconffileの設定に従い、dat_fileに再構成する。
    @param conffile (string) テンプレートファイル名
    @param csv_file (string) mode:iourlで作成されたCSVファイル名
    @param dat_file (string) 上記２ファイルから作成されるCSVファイル名
    @param workflow_id (string) テンプレートファイル内のdefaultがNoneで無い場合に使用するワークフローID
    @param siteid (string) 同、サイトID
    '''

    global counter_bar

    # セッション
    session = requests.Session()

    # テンプレートファイルの読み込み
    infile = open(conffile, "r", encoding=CHARSET_DEF)
    try:
        config = json.load(infile)
    except json.decoder.JSONDecodeError as e:
        sys.stderr.write("%sを読み込み中の例外キャッチ\n"%conffile)
        sys.stderr.write("%s\n"%e)
        sys.exit(1)
    infile.close()

    # テンプレートファイルの確認
    for item in config:
        if config[item]["default"] != None:
            if workflow_id == "" or siteid == "":
                sys.stderr.write("直接ファイル取得の指定がされているが、ワークフローID(%s)またはサイトID(%s)の指定が無い"%(workflow_id, siteid))
                sys.stderr.flush()
                sys.exit(1)

    # CSVファイルの解析
    infile = open(csv_file, "r", encoding=CHARSET_DEF)
    # 改行コードで分割して読み込むと最終行が空行となるため、読み込み方法を変更
    # lines = infile.read().split("\n")
    lines = [s.strip() for s in infile.readlines()]
    infile.close()
    headers = lines.pop(0).split(",")

    # datファイルの作成
    outfile = open(dat_file, "w", encoding=CHARSET_DEF)
    count = 1
    results_order = []
    results_order.append("loop")
    outfile.write("loop,")
    for header in config:
        if (header in headers) is True:
            print(header)
            if config[header]["filetype"] == "delete" or config[header]["filetype"].startswith("file"):          # ポート名に"delete"の指示があれば、使用しない。
                print("カラム(%s)はdelete指定またはfile指定があったので、削除します。"%header)
                continue
            if count == 1:
                outfile.write("%s"%header)
            else:
                outfile.write(",%s"%header)
            count += 1
            results_order.append(header)
    outfile.write("\n")

    # for debug
    #outfile.close()
    #sys.exit(0)

    print("%s - URLから内容を取り出しています。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    # 初期進捗バーの作成
    counter_bar = "-"
    for i in range(79):
        counter_bar += "-"
    sys.stdout.write("\r%s"%counter_bar)
    sys.stdout.flush()
    if len(lines) > 80:
        nperiod = int(len(lines) / 80)
    else:
        nperiod = int(80 / len(lines))
        #print("lines = %d / nperiod = %d"%(len(lines), nperiod))
    #sys.exit(0)
    # デバッグログの出力
    logout = open("run_results.log", "w", encoding=CHARSET_DEF)

    count = 1
    current_runid = None
    for aline in lines:
        aline = aline.split(",")
        csv_line = {}
        for i in range(len(results_order)):
            csv_line[results_order[i]] = None
        for i in range(len(aline)):
            items = aline[i].split(";")
            if headers[i] == "":
                continue
            elif headers[i] == "run_id          ":
                #csv_line += "%s,"%aline[i]
                csv_line["loop"] = "%s"%aline[i]
                current_runid = aline[i]
                continue
            elif headers[i] == "loop":
                continue
            elif headers[i] == "description":
                continue
            elif headers[i] == "status":
                continue
            elif (";" in aline[i]) is False:
                logout.write("%s - - invalid file contents(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                continue
            item1 = items[0]
            item2 = items[1]
            if item1 == "None":              # 初期値を使う
                #csv_line += "%s,"%config[headers[i]]["default"]
                csv_line[headers[i]] = "%s"%config[headers[i]]["default"]
                continue
            if  config[headers[i]]["filetype"].startswith("file"):    # スカラー値ではないので、ファイルにする
                if ("values" in aline[i]) is False:         # URLが不完全？
                    logout.write("%s - - invalid URL found(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                    logout.flush()
                    break
                if config[headers[i]]["filetype"] == "file":
                    dataout = open("%s_%s.%s"%(aline[0], headers[i], config[headers[i]]["ext"]), "w", encoding=CHARSET_DEF)
                else:
                    dataout = open("%s_%s.%s"%(aline[0], headers[i], config[headers[i]]["ext"]), "wb")
                #outfile.write("%s_%s,"%(aline[0], headers[i]))
                #csv_line += "%s_%s.%s,"%(aline[0], headers[i], config[headers[i]]["ext"])
                logout.write("%s - - getting scalar value for run_id:%s\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), current_runid))
                logout.flush()
                res = session.get(aline[i])
                if res.status_code != 200:
                    logout.write("%s -- failed get data(%s) for run_id:%s(1st)\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                    res.session.get(aline[i])
                    if res.status_code != 200:
                        logout.write("%s -- failed get data(%s) for run_id:%s(2nd)\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                #res = debug_random(-3.0, 3.0)
                time.sleep(0.05)
                if config[headers[i]]["filetype"] == "file":
                    dataout.write(res.text)
                else:
                    dataout.write(res.content)
                dataout.close()
            elif config[headers[i]]["filetype"] == "csv":   # スカラー値なのでCSVを取得した値で、構成する。
                if ("values" in aline[i]) is False:         # URLが不完全？
                    logout.write("%s - - invalid URL found(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                    logout.flush()
                    break
                    break
                logout.write("%s - - getting file contents for run_id:%s\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), current_runid))
                logout.flush()
                if config[headers[i]]["default"] == "None":  # GPDB URLに従って値を取得
                    res = session.get(aline[i])
                    #csv_line += "%s,"%res.text.split("\n")[0]
                    #csv_line[headers[i]] = "%s"%res.text.split("\n")[0]
                    tmpval = res.text.replace("\r\n", "\n")
                    csv_line[headers[i]] = "%s"%tmpval.split("\n")[0]
                else:
                    # None以外にファイル名が記入されているはずなので、
                    # GPDB URLのUUIDからパスを再構成してそのファイルを入手する。（指定されたファイルが無い場合はこのカラムは可らとなる。
                    pass
            elif config[headers[i]]["filetype"] == "delete":
                #outfile.write(",")
                #csv_line += ","
                continue
            else:
                pass
        #csv_line = csv_line[:-1]
        #outfile.write("%s\n"%csv_line)
        for i in range(len(results_order)):
            if i == 0:
                outfile.write("%s"%csv_line[results_order[i]])
            else:
                outfile.write(",%s"%csv_line[results_order[i]])
        outfile.write("\n")
        #if (count % nperiod) == 0:
        #    counter_bar = counter_bar.replace("-", "*", 1)
        #    sys.stderr.write("\r%s [%d/%d]"%(counter_bar, count, len(lines)))
        #    sys.stderr.flush()
        counterBar(count, nperiod, lines)
        count += 1

    outfile.close()
    sys.stdout.write("\r%s [%d/%d]"%(counter_bar, count - 1, len(lines)))
    sys.stdout.flush()
    logout.close()
    session.close()
    print("\n%s - 内容を取り出し終了。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

def generate_json(conffile, csv_file, json_file, rename_table, workflow_id="", siteid=""):
    '''
    generete_csvで作成されたcsv_fileをconffileの設定に従い、json_fileに再構成する。
    @param conffile (string) テンプレートファイル名
    @param csv_file (string) mode:iourlで作成されたCSVファイル名
    @param json_file (string) 上記２ファイルから作成されるCSVファイル名
    @param rename_table (dict) ポート名＝パラメータ置き換えテーブル辞書
    @param workflow_id (string) テンプレートファイル内のdefaultがNoneで無い場合に使用するワークフローID
    @param siteid (string) 同、サイトID
    '''

    # セッション
    session = requests.Session()

    # テンプレートファイルの読み込み
    infile = open(conffile, "r", encoding=CHARSET_DEF)
    try:
        config = json.load(infile)
    except json.decoder.JSONDecodeError as e:
        sys.stderr.write("%sを読み込み中の例外キャッチ\n"%conffile)
        sys.stderr.write("%s\n"%e)
        sys.exit(1)
    infile.close()

    # テンプレートファイルの確認
    for item in config:
        target_dup = False
        prev_target = ""
        if ("bayes_type" in config[item]) is False:
            sys.stderr.write("ポート名(%s)に、'bayes_type'キーがありません。"%item)
            sys.stderr.flush()
            sys.exit(1)
        if ("param_name" in config[item]) is False:
            sys.stderr.write("ポート名(%s)に、'param_name'キーがありません。"%item)
            sys.stderr.flush()
            sys.exit(1)
        if config[item]["bayes_type"] == "target":        # target指定の確認
            if target_dup is True:
                sys.stderr.write("target 指定が複数ありました。このバージョンは１つのみ許容できます。\n")
                sys.stderr.write("ポート名：%s(以前のtarget指定のポート名：%s)\n"%(item, prev_target))
                sys.stderr.flush()
                sys.exit(1)
            else:
                target_dup = True
                prev_target = item
            if ("ratio" in config[item]) is False:        # targetにratioキーが無かった
                config[item]["ratio"] = ""
            else:
                if config[item]["ratio"] == "":
                    config[item]["ratio"] = 1.0
                try:                                      # ratio値の確認
                    value = float(config[item]["ratio"])
                except:
                    sys.stderr.write("target の raito 値(%s)が不正です。intかfloatを指定してください。\n"%config[item]["ratio"])
                    sys.stderr.flush()
                    sys.exit(1)
                config[item]["ratio"] = value
        elif config[item]["bayes_type"] == "params":
            pass
        else:
            sys.stderr.write("ポート名(%s)の'bayes_type'に不明なタイプ(%s)が指定されていました。"%(item, config[item]["bayes_type"]))
            sys.stderr.flush()
            sys.exit(1)
    if target_dup is False:
        sys.stderr.write("'bayes_type'にtargetの指定がありません。\n")
        sys.stderr.flush()
        sys.exit(1)

    # CSVファイルの解析
    infile = open(csv_file, "r", encoding=CHARSET_DEF)
    # 改行コードで分割して読み込むと最終行が空行となるため、読み込み方法を変更
    # lines = infile.read().split("\n")
    lines = [s.strip() for s in infile.readlines()]
    infile.close()
    headers = lines.pop(0).split(",")

    # datファイルの作成
    outfile = open(json_file, "w", encoding=CHARSET_DEF)
    count = 1
    #results_order = []
    #results_order.append("loop")
    # ===> 2021/03/02 ヘッダー処理は不要
    #outfile.write("loop,")
    #for header in config:
    #    if (header in headers) is True:
    #        print(header)
    #        if config[header]["filetype"] == "delete" or config[header]["filetype"].startswith("file"):          # ポート名に"delete"の指示があれば、使用しない。
    #            print("カラム(%s)はdelete指定またはfile指定があったので、削除します。"%header)
    #            continue
    #        if count == 1:
    #            outfile.write("%s"%header)
    #        else:
    #            outfile.write(",%s"%header)
    #        count += 1
    #        #results_order.append(header)
    #outfile.write("\n")
    # <=== 2021/03/02

    # for debug
    #outfile.close()
    #sys.exit(0)

    print("%s - URLから内容を取り出しています。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    # 初期進捗バーの作成
    counter_bar = "-"
    for i in range(79):
        counter_bar += "-"
    sys.stderr.write("\r%s"%counter_bar)
    sys.stderr.flush()
    if len(lines) > 80:
        nperiod = int(len(lines) / 80)
    else:
        nperiod = int(80 / len(lines))
        #print("lines = %d / nperiod = %d"%(len(lines), nperiod))
    #sys.exit(0)
    # デバッグログの出力
    logout = open("run_results.log", "w", encoding=CHARSET_DEF)

    count = 1
    current_runid = None
    for aline in lines:
        aline = aline.split(",")
        json_line = {"target":"", "params":{}}
        #for i in range(len(results_order)):
        #    json_line[results_order[i]] = None
        for i in range(len(aline)):
            items = aline[i].split(";")
            if headers[i] == "":
                continue
            elif headers[i] == "run_id          ":
                #json_line += "%s,"%aline[i]
                #json_line["loop"] = "%s"%aline[i]
                current_runid = aline[i]
                continue
            elif headers[i] == "loop":
                continue
            elif (";" in aline[i]) is False:
                logout.write("%s - - invalid file contents(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                continue
            item1 = items[0]
            item2 = items[1]
            if item1 == "None":              # 初期値を使う
                #json_line += "%s,"%config[headers[i]]["default"]
                json_line[headers[i]] = "%s"%config[headers[i]]["default"]
                continue
            # ===> 2021/03/02 filetypeキーは使用しないのでコメントアウトする。
            #if  config[headers[i]]["filetype"].startswith("file"):    # スカラー値ではないので、ファイルにする
            #    if ("values" in aline[i]) is False:         # URLが不完全？
            #        logout.write("%s - - invalid URL found(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
            #        logout.flush()
            #        break
            #    if config[headers[i]]["filetype"] == "file":
            #        dataout = open("%s_%s.%s"%(aline[0], headers[i], config[headers[i]]["ext"]), "w", encoding=CHARSET_DEF)
            #    else:
            #        dataout = open("%s_%s.%s"%(aline[0], headers[i], config[headers[i]]["ext"]), "wb")
            #    logout.write("%s - - getting scalar value for run_id:%s\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), current_runid))
            #    logout.flush()
            #    res = session.get(aline[i])
            #    time.sleep(0.05)
            #    if config[headers[i]]["filetype"] == "file":
            #        dataout.write(res.text)
            #    else:
            #        dataout.write(res.content)
            #    dataout.close()
            #elif config[headers[i]]["filetype"] == "delete":
            #    #outfile.write(",")
            #    #json_line += ","
            #    continue
            #else:
            #    pass
            #elif config[headers[i]]["filetype"] == "param" or config[headers[i]]["filetype"] == "target":
            if config[headers[i]]["bayes_type"] == "params" or config[headers[i]]["bayes_type"] == "target":
            # <=== 2021/03/02
                # スカラー値なのでCSVを取得した値で、構成する。
                if ("values" in aline[i]) is False:         # URLが不完全？
                    logout.write("%s - - invalid URL found(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                    logout.flush()
                    break
                    break
                logout.write("%s - - getting file contents for run_id:%s\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), current_runid))
                logout.flush()
                if config[headers[i]]["default"] == "None":  # GPDB URLに従って値を取得
                    res = session.get(aline[i])
                    if res.status_code != 200:
                        print(res.text)
                        sys.exit(1)
                    tmpval = res.text.replace("\r\n", "\n")
                    if config[headers[i]]["bayes_type"] == "target":
                        try:
                            json_line["target"] = float(tmpval.split("\n")[0]) * config[headers[i]]["ratio"]
                        except:
                            print(aline[i])
                            print(res.text)
                            sys.exit(1)
                    elif config[headers[i]]["bayes_type"] == "params":
                        json_line["params"][headers[i]] = '"%s": %s'%(config[headers[i]]["param_name"], tmpval.split("\n")[0])
                    else:
                        logout.write("ランID(%s)、ポート名(%s)のfiletype(%s)は処理できません"%(current_runid, headers[i], config[headers[i]]["bayes_type"]))
                else:
                    # None以外にファイル名が記入されているはずなので、
                    # GPDB URLのUUIDからパスを再構成してそのファイルを入手する。（指定されたファイルが無い場合はこのカラムは空となる。
                    pass
        #for i in range(len(results_order)):
        #    if i == 0:
        #        outfile.write("%s"%json_line[results_order[i]])
        #    else:
        #        outfile.write(",%s"%json_line[results_order[i]])
        line_result = ""
        for item in json_line:
            if item == "target":
                line_result = '{"%s": %f, "params": {'%(item, json_line[item])
            else:
                json_count = 1
                for key in json_line[item]:
                    #line_result += '"%s": "%s"'%(config[headers[i]]["param_name"], json_line[item][key])
                    line_result += "%s"%json_line[item][key]
                    if json_count < len(json_line[item]):
                        line_result += ", "
                    json_count += 1
        line_result += "}}"
        #outfile.write("%s\n"%str(json_line))
        outfile.write("%s\n"%line_result)
        #if (count % nperiod) == 0:
        #    counter_bar = counter_bar.replace("-", "*", 1)
        #    sys.stderr.write("\r%s [%d/%d]"%(counter_bar, count, len(lines)))
        #    sys.stderr.flush()
        counterBar(count, nperiod, lines)
        count += 1

    outfile.close()
    sys.stdout.write("\r%s [%d/%d]"%(counter_bar, count - 1, len(lines)))
    sys.stdout.flush()
    logout.close()
    session.close()
    print("\n%s - 内容を取り出し終了。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

def main():
    '''
    開始点
    '''

    token = None
    workflow_id = None
    token = None
    url = None
    siteid = None
    result = False
    load_cash = False
    run_status = ["completed"]
    command_help = False
    run_mode = None
    conf_file = None
    tablefile = None
    csv_file = None
    dat_file = None
    thread_num = 10
    run_list = None
    json_file = None
    rename_table = {}
    global STOP_FLAG

    for items in sys.argv:
        items = items.split(":")
        if len(items) != 2:
            continue

        if items[0] == "workflow_id":           # ワークフローID
            workflow_id = items[1]
        elif items[0] == "token":               # APIトークン
            token = items[1]
        elif items[0] == "misystem":            # 環境指定(開発？運用？NIMS？東大？)
            url = items[1]
        elif items[0] == "result":              # 結果取得(True/False)
            result = items[1]
        elif items[0] == "siteid":              # site id(e.g. site00002)
            siteid = items[1]
        elif items[0] == "thread":              # スレッド数
            try:
                thread_num = int(items[1])
            except:
                therad_num = 10
        elif items[0] == "usecash":             # ランリストのキャッシュを使う
            load_cash = True
        elif items[0] == "run_status":          # ランステータス
            run_status = [s.strip() for s in items[1].split(',')]
        elif items[0] == "help":                # ヘルプ
            command_help = True
        elif items[0] == "mode":                # モード指定(iourl:URL取得/file:テーブル作成)
            if items[1] == "iourl" or items[1] == "file" or items[1] == "pybayes_json":
                run_mode = items[1]
        elif items[0] == "table":               # IOURLからCSV作成用の変換テーブル指定
            tablefile = items[1]
        elif items[0] == "csv":                 # IOURLで構成される第一段階のCSVファイルの名前
            csv_file = items[1]
        elif items[0] == "dat":                 # 第二段階のdatファイルの名前
            dat_file = items[1]
        elif items[0] == "conf":                # パラメータ構成ファイル
            conf_file = items[1]
        elif items[0] == "runlist":             # 対処ラン絞り込みリスト
            run_list = items[1]
        elif items[0] == "json":                # 第二段階のjsonファイルの名前
            json_file = items[1]
        else:
            print("unknown paramter(%s)"%items[0])

    # パラメータ構成ファイルの読み込み
    config = None
    if conf_file is not None:
        sys.stderr.write("パラメータを構成ファイル(%s)から読み込みます。\n"%conf_file)
        infile = open(conf_file, "r", encoding=CHARSET_DEF)
        try:
            config = json.load(infile)
        except json.decoder.JSONDecodeError as e:
            sys.stderr.write("%sを読み込み中の例外キャッチ\n"%conf_file)
            sys.stderr.write("%s\n"%e)
            sys.exit(1)
        infile.close()
    if config is not None:
        if run_mode == "iourl":
            if ("token" in config) is True:
                token = config["token"]
            if ("misystem" in config) is True:
                url = config["misystem"]
            if ("siteid" in config) is True:
                siteid = config["siteid"]
            if ("workflow_id" in config) is True:
                workflow_id = config["workflow_id"]
            if ("csv" in config) is True:
                csv_file = config["csv"]
            if ("run_list" in config) is True:
                run_list = config["run_list"]
            if ("run_status" in config) is True:
                run_status = [s.strip() for s in config["run_status"].split(',')]
        elif run_mode == "file":
            if ("csv" in config) is True:
                csv_file = config["csv"]
            if ("table" in config) is True:
                tablefile = config["table"]
            if ("dat" in config) is True:
                dat_file = config["dat"]
            if ("workflow_id" in config) is True:
                workflow_id = config["workflow_id"]
            if ("siteid" in config) is True:
                siteid = config["siteid"]
        elif run_mode == "pybayes_json":
            if ("csv" in config) is True:
                csv_file = config["csv"]
            if ("table" in config) is True:
                tablefile = config["table"]
            if ("json" in config) is True:
                json_file = config["dat"]
            if ("workflow_id" in config) is True:
                workflow_id = config["workflow_id"]
            if ("siteid" in config) is True:
                siteid = config["siteid"]
            if ("pybayes_json_table" in config) is True:
                rename_table = config["pybayes_json_table"]
        if ("csv_file" in config) is True:
            csv_file = config["csv_file"]

    # 処理開始
    print_help = False
    if run_mode == "iourl":
        if workflow_id is None:
            print("対象のワークフローIDの指定がありません")
            print_help = True
        if url is None:
            print("対象のMIntシステムの指定がありません")
            print_help = True
        if siteid is None:
            print("siteIDの指定がありません")
            print_help = True
        if csv_file is None:
            print("CSVファイル名の指定がありません")
            print_help = True
        # ランリストの指定があった場合の確認
        if run_list is not None:
            if os.path.exists(run_list) is False:
                print("ランリストファイル(%s)はありません。"%run_list)
                print_help = True
        # token指定が無い場合ログイン情報取得
        if token is None and url is not None:
    
            ret, uid, token = getAuthInfo(url)
    
            if ret is False:
                print(uid.json())
                print("ログインに失敗しました。")
                print_help = True
        elif token is None and url is None:
            print("APIトークンとMIntシステムの指定がありません。")
            print_help = True

    elif run_mode == "file":
        if tablefile is None or csv_file is None or dat_file is None:
            print("必要なファイルが足りません。")
            print_help = True
    elif run_mode == "pybayes_json":
        if tablefile is None or csv_file is None or json_file is None:
            print("必要なファイルが足りません。")
            print_help = True
    elif command_help is True:
        print_help = True
    else:
        print("modeの指定がありません。")
        print_help = True

    if print_help is True or run_mode is None:
        print("ワークフローIDの計算結果データを取得する。")
        print("")
        print("Usage:  $ python %s workflow_id:Mxxxx token:yyyy misystem:URL mode:[iourl/file] [options]"%(sys.argv[0]))
        print("")
        print("必須パラメータ")
        print("               mode   : 動作モード。")
        print("                        iourl        : 入出力名をヘッダーとしたランIDごとのCSVファイルを作成する。")
        print("                                       各カラムは計算結果データをGPDBへのURLが格納される。")
        print("                        file         : iourlモードで作成したテーブルと別途用意した構成ファイルを使い、")
        print("                                       機械学習向けのCSVファイルを作成する。 ")
        print("                        pybayes_json : pythonのbayesian_optimization用リスタートファイルを作成する。")
        print("                csv   : iourlモードで作成されるCSVファイルの名前")
        print("                        fileモードではiourlモードで作成したCSVとして指定する。")
        print("               table  : iourlで取得したGPDB情報を変換するテーブルの指定")
        print("                        fileモードで自動的に作成されるが、fileモードでこれを指定すると自動作成しない。")
        print("           match_tabl : descriptionに記入した辞書形式のキーおよび値と一致するものを処理するためのテーブル。")
        print("                        詳細はREADME.mdを参照（expriment実装）")
        print("               conf   : いくつかのパラメータを書いておける便利な構成ファイル")
        print("                        README.mdを参照")
        print("")
        print("     mode を iourlと指定したとき")
        print("          workflow_id : Wで始まる15桁のワークフローID")
        print("               token  : 64文字のAPIトークン。指定しない場合ログイン問い合わせとなる。")
        print("             misystem : dev-u-tokyo.mintsys.jpのようなMIntシステムのURL")
        print("              siteid  : siteと＋５桁の数字。site00002など")
        print("             usecash  : 次回以降キャッシュから読み込みたい場合に指定する。")
        print("                        未指定で実行すればキャッシュは作成される。")
        print("          run_status  : CSV出力対象のランステータス。カンマ区切りで複数指定可能。")
        print("                        未指定で実行すればcompletedのみ対象とする。")
        print("")
        print("     mode を fileと指定したとき")
        print("                dat   : fileモードで作成される結果ファイル。機械学習用")
        print("     mode を pybayes_jsonと指定したとき")
        print("                json  : basian_optimization用のリロードファイル名の指定")
        print("")
        print("非必須のパラメータ")
        print("              thread  : API呼び出しの並列数（デフォルト10個）")
        print("             runlist  : modeがiourlの時に指定する。")
        print("                        workflow_execute.pyが出力するランリスト。")
        print("                        空白区切りで4カラム目にIDがあれば他はどうなっていても問題無し。")
        print("                        このランリストに該当するランのみを処理対象とする。")
        print("                        指定が無い場合は該当する全ランが対象となる。")
        sys.exit(1)

    # Thread上限は20とする。
    if thread_num >= 20:
        thread_num = 20

    if run_mode == "iourl":
        generate_csv(token, url, siteid, workflow_id, csv_file, tablefile, result, thread_num, load_cash, run_list, run_status)
    elif run_mode == "file":
        generate_dat(tablefile, csv_file, dat_file, workflow_id, siteid)
    elif run_mode == "pybayes_json":
        generate_json(tablefile, csv_file, json_file, rename_table, workflow_id, siteid)

if __name__ == '__main__':
    main()

