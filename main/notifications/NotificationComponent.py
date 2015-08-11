# coding: utf8

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
        logging.debug('*** session attached ***')
        self.cnx = utils.database_connect()

        regs = yield self.register(self)
        print('registered {} procedures'.format(len(regs)))

        downloads_previous_list = []
        while True:
            downloads_list_to_publish = []
            # downloads = yield self.call('plow.download.downloads')
            cursor = self.cnx.cursor()

            sql = 'SELECT * FROM download WHERE status = %s'
            data = (Download.STATUS_IN_PROGRESS,)
            logging.debug('query : %s | data : (%s)' % (sql, str(Download.STATUS_IN_PROGRESS).encode('UTF-8')))

            yield cursor.execute(sql, data)

            downloads_current_list = utils.cursor_to_download_object(cursor)

            cursor.close()

            for download_current in downloads_current_list:
                previous_download = self.get_previous_download(downloads_previous_list, download_current)

                if previous_download is None or previous_download.lifecycle_update_date < download_current.lifecycle_update_date:
                    self.publish_to_download(download_current, previous_download)
                    print('Published')
                    downloads_list_to_publish.append(self.put_download_to_downloads_list_to_publish(download_current))

            if len(downloads_list_to_publish) > 0:
                logging.debug('Publish:'.format(downloads_list_to_publish))
                self.publish(u'plow.downloads.downloads', downloads_list_to_publish)

            if len(downloads_previous_list) > 0:
                downloads_previous_list_to_publish = []
                # notifie les telechargement qui ont changé de statut
                for download_previous in downloads_previous_list:
                    logging.debug('Status changing for %s' % download_previous.id)
                    logging.debug('Get download for id %s' % download_previous.id)
                    # besoin de récupérer le download pour avoir le nouveau status
                    cursor = self.cnx.cursor()
                    sql = 'SELECT * FROM download WHERE id = %s'
                    data = (download_previous.id,)
                    logging.debug('query : %s | data : (%s)' % (sql, str(download_previous.id).encode('UTF-8')))
                    cursor.execute(sql, data)
                    download_to_publish = utils.cursor_to_download_object(cursor)[0]
                    cursor.close()

                    self.publish_to_download(download_to_publish, None)
                    downloads_previous_list_to_publish.append(self.put_download_to_downloads_list_to_publish(download_to_publish))
                logging.debug('Status changing for list')
                self.publish(u'plow.downloads.downloads', downloads_previous_list_to_publish)

            downloads_previous_list = downloads_current_list
            yield sleep(2)

    def get_previous_download(self, downloads_previous_list, download_current):
        previous_download = None

        for download_previous in downloads_previous_list:
            if download_current.id == download_previous.id:
                previous_download = download_previous
                # supprime le telechargement de la liste des previous (utile pour notifier les telechargement qui ont
                # changé de statut
                downloads_previous_list.remove(previous_download)

        return previous_download

    def publish_to_download(self, download, previous_download):
        logging.debug('*** publish_to_download ***')
        last_infos_plowdown = download.infos_plowdown
        if previous_download is not None:
            #on ne récupère que les lignes qu'on avait pas avant
            last_infos_plowdown = download.infos_plowdown.replace(previous_download.infos_plowdown, '')

        to_publish = {'id': download.id,
                      'progress_file': download.progress_file,
                      'progress_part': download.progress_part,
                      'size_file_downloaded': download.size_file_downloaded,
                      'size_part_downloaded': download.size_part_downloaded,
                      'time_spent': download.time_spent,
                      'time_left': download.time_left,
                      'average_speed': download.average_speed,
                      'current_speed': download.current_speed,
                      'status': download.status,
                      'last_infos_plowdown': last_infos_plowdown
                      }
        logging.debug('Publish: %s' % format(to_publish))
        self.publish(u'plow.downloads.download.%s' % str(download.id), to_publish)

    def put_download_to_downloads_list_to_publish(self, download):
        return {'id': download.id, 'progress_file': download.progress_file,
                         'time_left': download.time_left,
                         'average_speed': download.average_speed,
                         'status': download.status}

if __name__ == '__main__':
    logging.basicConfig(filename='/var/www/main/notifications/log/log_notif.log', level=logging.DEBUG,
                        format='%(asctime)s %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logging.debug('*** Start notification server ***')

    log.startLogging(sys.stdout)
    runner = ApplicationRunner(url="ws://192.168.1.101:8181/ws", realm="realm1")
    runner.run(NotificationComponent)
