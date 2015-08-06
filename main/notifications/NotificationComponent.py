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

        downloads_previous = []
        while True:
            downloads_list_to_publish = []
            # downloads = yield self.call('plow.download.downloads')
            cursor = self.cnx.cursor()

            sql = 'SELECT * FROM download WHERE status = %s'
            data = (Download.STATUS_IN_PROGRESS,)
            logging.debug('query : %s | data : (%s)' % (sql, str(Download.STATUS_IN_PROGRESS).encode('UTF-8')))

            yield cursor.execute(sql, data)

            downloads_list = utils.cursor_to_download_object(cursor)

            cursor.close()

            previous_download = None
            for download in downloads_list:
                for download_previous in downloads_previous:
                    if download.id == download_previous.id:
                        previous_download = download_previous

                if previous_download is None or previous_download.infos_plowdown != download.infos_plowdown:
                    self.publish(u'plow.downloads.download.%s' % str(download.id),
                                 {'id': download.id,
                                  'progress_file': download.progress_file,
                                  'progress_part': download.progress_part,
                                  'size_file_downloaded': download.size_file_downloaded,
                                  'size_part_downloaded': download.size_part_downloaded,
                                  'time_left': download.time_left,
                                  'average_speed': download.average_speed,
                                  'status': download.status,
                                  'infos_plowdown': download.infos_plowdown})
                    print('Published')

                    downloads_list_to_publish.append(
                        {'id': download.id, 'progress_file': download.progress_file, 'time_left': download.time_left,
                         'average_speed': download.average_speed})

            self.publish(u'plow.downloads.downloads', downloads_list_to_publish)
            downloads_previous = downloads_list
            yield sleep(2)

    # @wamp.register(u'plow.download.downloads')
    # @inlineCallbacks
    # def get_downloads(self):
    #     cursor = self.cnx.cursor()
    #
    #     sql = 'SELECT * FROM download WHERE status = %s'
    #     data = (Download.STATUS_IN_PROGRESS,)
    #     logging.debug('query : %s | data : (%s)' % (sql, str(Download.STATUS_IN_PROGRESS).encode('UTF-8')))
    #
    #     yield cursor.execute(sql, data)
    #
    #     list_downloads = utils.cursor_to_download_object(cursor)
    #
    #     cursor.close()
    #
    #     returnValue(list_downloads)


if __name__ == '__main__':
    logging.basicConfig(filename='./log/log_notif.log', level=logging.DEBUG, format='%(asctime)s %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logging.debug('*** Start notification server ***')

    log.startLogging(sys.stdout)
    runner = ApplicationRunner(url="ws://127.0.0.1:8080/ws", realm="realm1")
    runner.run(NotificationComponent)
