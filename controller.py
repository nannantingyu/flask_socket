# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from multiprocessing import Queue, Process
from send_message import Qmanager
from dotenv import load_dotenv
from os import environ

if __name__ == '__main__':
    myqueue = Queue()
    node = Qmanager()
    load_dotenv('.env')

    manager_proc = Process(target=node.manager_proc)
    manager_proc.start()