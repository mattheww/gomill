import os
import random
import sys
import time

from gomill import job_manager

class Job(object):
    def __init__(self, num):
        self.num = num

    def __repr__(self):
        return "game %d" % self.num

    def run(self):
        sys.stderr.write("worker %d: %s\n" % (os.getpid(), self))
        time.sleep(random.random()*6)
        if self.num == 4:
            print int("asd")
        return "response to %s" % self

class Game_dispatcher(object):
    def __init__(self):
        self.counter = 0
        self.max = 7

    def get_job(self):
        if self.counter >= self.max:
            return job_manager.NoJobAvailable
        self.counter += 1
        return Job(self.counter)

    def process_response(self, response):
        pass

    def process_error_response(self, job, message):
        print "** Error from worker working on %s" % job
        print message


def test():
    mgr = job_manager.Multiprocessing_job_manager(3)
    #mgr = job_manager.In_process_job_manager()
    job_source = Game_dispatcher()
    mgr.start_workers()
    mgr.run_jobs(job_source)
    mgr.finish()

def test2():
    job_source = Game_dispatcher()
    job_manager.run_jobs(job_source, 3, allow_mp=True)

if __name__ == "__main__":
    test2()

