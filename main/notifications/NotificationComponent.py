__author__ = 'Vincent'

from twisted.internet.defer import inlineCallbacks, returnValue

from autobahn import wamp
import sys
from twisted.python import log
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession
from autobahn.twisted.wamp import ApplicationRunner
import logging
from bean.downloadBean import Download
import utils


class NotificationComponent(ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):
        print("session attached")
        self.cnx = utils.database_connect()

        regs = yield self.register(self)
        print('registered {} procedures'.format(len(regs)))

        while True:
            downloads = yield self.call('plow.download.downloads')

            for download in downloads:
                print('publishing {}'.format(download))
                self.publish(u'plow.download.downloads.infos_plowdown', {'infos_plowdown': download['infos_plowdown']})

            yield sleep(2)

    @wamp.register(u'plow.download.downloads')
    @inlineCallbacks
    def get_downloads(self):
        cursor = self.cnx.cursor()

        sql = 'SELECT * FROM download WHERE status = %s'
        data = (Download.STATUS_IN_PROGRESS, )
        logging.debug('query : %s | data : (%s)' % (sql, str(Download.STATUS_IN_PROGRESS).encode('UTF-8')))

        yield cursor.execute(sql, data)

        list_downloads = utils.cursor_to_download_object(cursor)

        returnValue(list_downloads)


if __name__ == '__main__':
    logging.basicConfig(filename='./log_notif.log', level=logging.DEBUG, format='%(asctime)s %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logging.debug('*** Start notification server ***')

    log.startLogging(sys.stdout)
    runner = ApplicationRunner(url="ws://127.0.0.1:8080/ws", realm="realm1")
    runner.run(NotificationComponent)
