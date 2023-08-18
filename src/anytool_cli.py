#!/usr/bin/python3
import os
import logging
import time
import traceback
import json
import cmd
import argparse
import analysis
import pickle
import pandas as pd

built_in = ["imperva-ns[G]", "imperva[R]", "edgio-ns[G]", "edgio-3[R]", "edgio-4[R]", "cloudflare[G]", "akamai[G]"]


class MainCmd(cmd.Cmd):
    intro = """
----------------------------------------------------
    ___                __              __
   /   |  ____  __  __/ /_____  ____  / /
  / /| | / __ \\/ / / / __/ __ \\/ __ \\/ /
 / ___ |/ / / / /_/ / /_/ /_/ / /_/ / /
/_/  |_/_/ /_/\\__, /\\__/\\____/\\____/_/
             /____/
----------------------------------------------------
    An tool for measuring any kind of anycast deployment.
    """

    prompt = 'Anytool> '

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.test_analysis = None
        self.aliases = {'a': self.do_get_result,
                        'b': self.do_built_in,
                        'c': self.do_choose,
                        'show': self.do_show_result,
                        'save': self.do_save_result,
                        'm': self.do_map_site,
                        'r': self.do_select_unirepre,
                        'g': self.do_geo_analyze,
                        'rt': self.do_rtt_analyze}

    def do_get_result(self, arg):
        parser = argparse.ArgumentParser()
        parser.add_argument("-k", "--key", dest="key", type=list, required=False, default=[], help="which cdn, e.g. imperva")
        parser.add_argument("-n", "--name", dest="name", type=str, required=False, default="", help="which cdn, e.g. imperva")
        parser.add_argument("-t", "--target", dest="target", type=list, required=False, default=[], help="the target ip or hostname")
        parser.add_argument("-f", "--file", dest="file", type=str, required=False, default="", help="cdn site file")
        parser.add_argument("-m", "--mid", dest="mid", type=list, required=False, 
        default=[], help="measurement ID")
        try:
            args = parser.parse_args(arg.split())
            if args is None:
                return

            self.test_analysis = analysis.analysis(key_lst=args.key, target=args.target, dc_name=args.name, dc_file=args.file, mtr_lst=args.mid)

        except Exception as e:
            print(e)

    def do_built_in(self, arg):
        try:
            print("The following anycast deployments are already measured by anytool. You can use 'choose [name]' command to see the results. Note: R means regional anycast and G means global anycast")
            i = 1
            for item in built_in:
                print(f"{i}:{item}")
                i = i + 1
        except Exception as e:
            print(e)

    def do_choose(self, arg):
        parser = argparse.ArgumentParser()
        parser.add_argument("-n", "--number", dest="number", type=int, required=True, default=0, help="which built-in measurement, e.g. imperva")
        try:
            args = parser.parse_args(arg.split())
            if args is None:
                return
            if args.number > len(built_in):
                print("invalid numbers")
                return
            with open(f"../dataset/built-in/{built_in[args.number-1]}.txt") as f:
                    content = f.read()
                    required = eval(content)  # file should include required content
            self.test_analysis = analysis.analysis(dc_name=required['dc_name'],target=required['target'],mtr_lst=required['mtr_lst'])
        except Exception as e:
            print(e)

    def do_show_result(self, arg):
        try:
            if self.test_analysis is None:
                print("Please get the results first")
                return
            print(self.test_analysis.measure.measure_pd)
        except Exception as e:
            print(e)

    def do_save_result(self, arg):
        parser = argparse.ArgumentParser()
        parser.add_argument("-l", "--location", dest="location", type=str, required=True, default="../dataset/a.csv", help="where to save the result")
        try:
            args = parser.parse_args(arg.split())
            if args is None:
                return
            if self.test_analysis is None:
                print("Please get the results first")
                return
            self.test_analysis.measure.measure_pd.to_csv(args.location)
            #self.test_analysis.measure.measure_pd
        except Exception as e:
            print(e)

    def do_map_site(self, arg):
        try:
            if self.test_analysis is None:
                print("Please get the results first")
                return
            self.test_analysis.mapsite()
        except Exception as e:
            print(e)

    def do_select_unirepre(self, arg):
        try:
            if self.test_analysis is None:
                print("'analysis' first")
                return
            self.test_analysis.reprePhop()
        except Exception as e:
            print(e)

    def do_geo_analyze(self, arg):
        try:
            if self.test_analysis is None:
                print("'analysis' first")
                return
            self.test_analysis.geoanalysis()
            with open("temp.pkl", "wb") as f:
                pickle.dump(self.test_analysis, f)
        except Exception as e:
            print(e)

    def do_rtt_analyze(self, arg):
        try:
            try:
                with open("temp.pkl", "rb") as f:
                    self.test_analysis = pickle.load(f)
            except BaseException:
                pass
            if self.test_analysis is None:
                print("'analysis' first")
                return
            arg = "../test/imperva/ping_mid.txt"
            self.test_analysis.rttanalysis(arg)
        except Exception as e:
            print(e)

    def emptyline(self):
        pass

    def do_EOF(self, line):
        print("")
        return True

    def do_shell(self, line):
        "Run a shell command"
        print("running shell command:", line)
        output = os.popen(line).read()
        print(output)
        self.last_output = output

    def default(self, line):
        cmd, arg, line = self.parseline(line)
        if cmd in self.aliases:
            self.aliases[cmd](arg)
        else:
            print("*** Unknown syntax: %s" % line)


if __name__ == "__main__":
    MainCmd().cmdloop()
