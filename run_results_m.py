#!/usr/local/python2.7/bin/python
# -*- coding: utf-8 -*-

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

sys.path.append("/home/misystem/assets/modules/workflow_python_lib")
from workflow_runlist import *
from workflow_iourl import *


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
        self.list_num = len(self.runlist)
        self.status = {"canceled":"キャンセル", "failure":"起動失敗"}

    def run(self):
        '''
        スレッド実行
        '''

        sys.stderr.write("%s -- %03d : %10d 個のランを処理します。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, self.list_num))
        sys.stderr.flush()
        i = 1
        results = []
        for run in self.runlist:
            if (i % 500) == 0:
                sys.stderr.write("%s -- %03d : %d 個処理しました。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, i))
                sys.stderr.flush()
            i += 1

            #if run["status"] == "completed":
            if run["status"] != "canceled" and run["status"] != "failure":
                self.csv_log.write("%s -- %03d : %sのランIDを処理中\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, run["run_id"]))
                self.csv_log.flush()
                ret, ret_dict = get_runiofile(self.token, self.url, self.siteid, run["run_id"], self.result, thread_num=self.thread_num)
                if ret is False:
                    self.csv_log.write(ret_dict)
                    self.csv_log.flush()
                    continue
                results.append(ret_dict)
            else:
                print("ラン番号(%s)は実行完了していない(%s)ので、処理しません。"%(run["run_id"], self.status[run["status"]]))
                continue

        sys.stderr.write("%s -- %03d : %d 個処理終了しました。\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), self.thread_num, self.list_num))
        sys.stderr.flush()
        self.results[threading.current_thread().name] = results


def generate_csv(token, url, siteid, workflow_id, csv_file, result, thread_num, load_cash, run_list):
    '''
    まずはGPDBからファイルの実体を取得するIOURLを取得し、CSVを作成する。
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
        infile = open(run_list)
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
    csv_log = open("create_csv.log", "w")

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
        t = job_get_iourl(args=(token, url, siteid, runlist, i + 1, result, results, csv_log))
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

    print("%s - tableファイルを作成しています。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    outfile = open("table_template.tbl", "w")
    outfile.write("{\n")
    for i in range(len(headers)):
    #for item in headers:
        if headers[i] == "loop":
        #if item == "loop":
            continue
        #outfile.write('"%s":{"filetype":"csv", "default":"None", "ext":""},\n'%item)
        outfile.write('"%s":{"filetype":"csv", "default":"None", "ext":""}'%headers[i])
        if i < len(headers) - 1:
            outfile.write(",\n")
    outfile.write("\n}\n")
    outfile.close()

    print("%s - ヘッダーは以下のとおりです。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    outfile = open(csv_file, "w")
    total_file_amount = {}
    outfile.write("run_id          ,")
    for item in headers:
        outfile.write("%s,"%item)
        sys.stderr.write("%s\n"%item)
        sys.stderr.flush()
        if item != "loop":
            total_file_amount[item] = 0

    # 結果（JSON）の一時保存
    routfile = open("results_cach.dat", "w")
    json.dump(results, routfile, ensure_ascii=False, indent=4)
    routfile.close()

    print("%s - データファイル(CSV)を構築しています。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    #print("%s"%str(results))
    outfile.write("\n")
    for thread in results:
        for items in results[thread]:
            for item in items:
                for key in headers:
                    #print(item)
                    #print(str(items[item]))
                    if (key in items[item]) is True:
                        #print(key)
                        if key == "loop":
                            outfile.write("%d,"%int(item[1:]))                   # run_idを先頭に記入
                            outfile.write("%d"%items[item][key])
                        else:
                            if items[item][key][0] == "null":
                                outfile.write("null:0")
                            else:
                                outfile.write("%s;%s"%(items[item][key][0], items[item][key][1]))
                                if items[item][key][1] is None or items[item][key][1] == "None":
                                    pass
                                else:
                                    total_file_amount[key] += items[item][key][1] 
                    outfile.write(",")
    
            outfile.write("\n")

    outfile.close()
    print("%s - データファイル(CSV)を構築終了。"%datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
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

def generate_dat(conffile, csv_file, dat_file):
    '''
    generete_csvで作成されたcsv_fileをconffileの設定に従い、dat_fileに再構成する。
    '''

    # セッション
    session = requests.Session()

    # 構成ファイルの読み込み
    infile = open(conffile, "r")
    try:
        config = json.load(infile)
    except json.decoder.JSONDecodeError as e:
        sys.stderr.write("%sを読み込み中の例外キャッチ\n"%conffile)
        sys.stderr.write("%s\n"%e)
        sys.exit(1)
    infile.close()

    # CSVファイルの解析
    infile = open(csv_file, "r")
    lines = infile.read().split("\n")
    headers = lines.pop(0).split(",")

    # datファイルの作成
    outfile = open(dat_file, "w")
    for header in headers:
        if header == 'run_id          ':        # run_idは飛ばす
            continue
        if (header in config) is True:
            print(header)
            if config[header]["filetype"] == "delete" or config[header]["filetype"] == "file":          # ポート名に"delete"の指示があれば、使用しない。
                print("カラム(%s)はdelete指定またはfile指定があったので、削除します。"%header)
                continue
            outfile.write("%s,"%header)
        else:
            outfile.write("%s,"%header)
    outfile.write("\n")

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
    logout = open("run_results.log", "w")

    count = 1
    current_runid = None
    for aline in lines:
        aline = aline.split(",")
        csv_line = ""
        for i in range(len(aline)):
            items = aline[i].split(";")
            if headers[i] == "":
                continue
            elif headers[i] == "run_id          ":
                #outfile.write("%s,"%aline[i])
                csv_line += "%s,"%aline[i]
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
                #outfile.write("%s,"%config[headers[i]]["default"])
                csv_line += "%s,"%config[headers[i]]["default"]
                continue
            if config[headers[i]]["filetype"] == "file":    # スカラー値ではないので、ファイルにする
                if ("values" in aline[i]) is False:         # URLが不完全？
                    logout.write("%s - - invalid URL found(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                    logout.flush()
                    break
                dataout = open("%s_%s.%s"%(aline[0], headers[i], config[headers[i]]["ext"]), "w")
                #outfile.write("%s_%s,"%(aline[0], headers[i]))
                #csv_line += "%s_%s.%s,"%(aline[0], headers[i], config[headers[i]]["ext"])
                logout.write("%s - - getting scalar value for run_id:%s\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), current_runid))
                logout.flush()
                res = session.get(aline[i])
                #res = debug_random(-3.0, 3.0)
                time.sleep(0.05)
                dataout.write(res.text)
                dataout.close()
            elif config[headers[i]]["filetype"] == "csv":   # スカラー値なのでCSVを取得した値で、構成する。
                if ("values" in aline[i]) is False:         # URLが不完全？
                    logout.write("%s - - invalid URL found(%s) at RunID(%s); skipped\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), aline[i], current_runid))
                    logout.flush()
                    break
                    break
                logout.write("%s - - getting file contents for run_id:%s\n"%(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), current_runid))
                logout.flush()
                res = session.get(aline[i])
                #outfile.write("%s,"%res.text.split("\n")[0])
                csv_line += "%s,"%res.text.split("\n")[0]
                #res = debug_random(-3.0, 3.0)
                #time.sleep(0.1)
                #outfile.write("%s,"%res.text)
            elif config[headers[i]]["filetype"] == "delete":
                #outfile.write(",")
                #csv_line += ","
                continue
            else:
                pass
        outfile.write("%s\n"%csv_line)
        if (count % nperiod) == 0:
            counter_bar = counter_bar.replace("-", "*", 1)
            sys.stderr.write("\r%s [%d/%d]"%(counter_bar, count, len(lines)))
            sys.stderr.flush()
        count += 1

    sys.stderr.write("\r%s [%d/%d]"%(counter_bar, count - 1, len(lines)))
    sys.stderr.flush()
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
    command_help = False
    run_mode = None
    conf_file = None
    tablefile = None
    csv_file = None
    dat_file = None
    thread_num = 10
    run_list = None
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
        elif items[0] == "help":                # ヘルプ
            command_help = True
        elif items[0] == "mode":                # モード指定(iourl:URL取得/file:テーブル作成)
            if items[1] == "iourl" or items[1] == "file":
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
        else:
            print("unknown paramter(%s)"%items[0])

    # パラメータ構成ファイルの読み込み
    config = None
    if conf_file is not None:
        sys.stderr.write("パラメータを構成ファイル(%s)から読み込みます。\n"%conf_file)
        infile = open(conf_file, "r")
        try:
            config = json.load(infile)
        except json.decoder.JSONDecodeError as e:
            sys.stderr.write("%sを読み込み中の例外キャッチ\n"%conffile)
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
        elif run_mode == "file":
            if ("table" in config) is True:
                tablefile = config["table"]
            if ("dat" in config) is True:
                dat_file = config["dat"]
        if ("csv_file" in config) is True:
            csv_file = config["csv_file"]

    # 処理開始
    print_help = False
    if run_mode == "iourl":
        if workflow_id is None or url is None or siteid is None or csv_file is None:
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
            print_help = True

    elif run_mode == "file":
        if tablefile is None or csv_file is None or dat_file is None:
            print_help = True
    elif command_help is True:
        print_help = True
    else:
        print_help = True

    if print_help is True or run_mode is None:
        print("ワークフローIDの計算結果データを取得する。")
        print("")
        print("Usage:  $ python %s workflow_id:Mxxxx token:yyyy misystem:URL mode:[iourl/file] [options]"%(sys.argv[0]))
        print("")
        print("必須パラメータ")
        print("               mode   : 動作モード。")
        print("                        iourl : 入出力名をヘッダーとしたランIDごとのCSVファイルを作成する。")
        print("                                各カラムは計算結果データをGPDBへのURLが格納される。")
        print("                        file : iourlモードで作成したテーブルと別途用意した構成ファイルを使い、")
        print("                                機械学習向けのCSVファイルを作成する。 ")
        print("                csv   : iourlモードで作成されるCSVファイルの名前")
        print("                        fileモードではiourlモードで作成したCSVとして指定する。")
        print("               conf   : いくつかのパラメータを書いておける便利な構成ファイル")
        print("                        README.mdを参照")
        print("")
        print("     mode を iourlと指定したとき")
        print("          workflow_id : Wで始まる15桁のワークフローID")
        print("               token  : 64文字のAPIトークン。指定しない場合ログイン問い合わせとなる。")
        print("             misystem : dev-u-tokyo.mintsys.jpのようなMIntシステムのURL")
        print("              siteid  : siteと＋５桁の数字。site00002など")
        print("              thread  : API呼び出しの並列数（デフォルト10個）")
        print("             usecash  : 次回以降キャッシュから読み込みたい場合に指定する。")
        print("                        未指定で実行すればキャッシュは作成される。")
        print("")
        print("     mode を fileと指定したとき")
        print("               table  : iourlで取得したGPDB情報を変換するテーブルの指定")
        print("                dat   : fileモードで作成される結果ファイル。機械学習用")
        print("非必須のパラメータ")
        print("            runlist   : modeがiourlの時に指定する。")
        print("                        workflow_execute.pyが出力するランリスト。")
        print("                        空白区切りで4カラム目にIDがあれば他はどうなっていても問題無し。")
        print("                        このランリストに該当するランのみを処理対象とする。")
        print("                        指定が無い場合は該当する全ランが対象となる。")
        sys.exit(1)

    # Thread上限は20とする。
    if thread_num >= 20:
        thread_num = 20

    if run_mode == "iourl":
        generate_csv(token, url, siteid, workflow_id, csv_file, result, thread_num, load_cash, run_list)
    elif run_mode == "file":
        generate_dat(tablefile, csv_file, dat_file)

if __name__ == '__main__':
    main()

