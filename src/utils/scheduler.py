# -*- coding: utf-8 -*-

"""
Scheduler tasks for the hive node.
"""
import logging
import traceback
import time

import pymongo
from flask_apscheduler import APScheduler

from src import hive_setting
from src.modules.ipfs.ipfs_files import IpfsFiles
from src.utils.consts import COL_IPFS_FILES, COL_IPFS_FILES_IPFS_CID, COL_IPFS_FILES_PATH, DID, APP_DID
from src.utils.db_client import cli
from src.utils.file_manager import fm
from src.utils_v1.common import get_temp_path
from src.utils_v1.constants import USER_DID, APP_ID
from src.utils_v1.did_file_info import get_save_files_path
from src.utils_v1.did_mongo_db_resource import gene_mongo_db_name

scheduler = APScheduler()


def scheduler_init(app):
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()


# TODO: remove this later.
# @scheduler.task('interval', id='task_upload_ipfs_files', minutes=10)
def task_upload_ipfs_files():
    """ Task for syncing file content to ipfs server and updating cid on metadata.
    This task only updates the IPFS CID of the file.
    TODO: Try to move this to ipfs-files module for real-time CID getting.
    """
    logging.info('[task_upload_ipfs_files] enter.')

    if not hive_setting.ENABLE_IPFS:
        logging.info('[task_upload_ipfs_files] IPFS not supported, skip.')
        return

    for db_name in cli.get_all_user_database_names():
        upload_ipfs_files_by_db(db_name)

    logging.info('[task_upload_ipfs_files] leave.')


def upload_ipfs_files_by_db(db_name):
    # find 10 docs and ordered by ascending.
    col_filter = {COL_IPFS_FILES_IPFS_CID: {'$exists': True, '$eq': None}}
    options = {'limit': 10, 'sort': [('modified', pymongo.ASCENDING), ]}
    file_docs = cli.find_many_origin(db_name, COL_IPFS_FILES, col_filter, throw_exception=False, options=options)
    logging.info(f'[task_upload_ipfs_files] get {len(file_docs) if file_docs else 0} '
                 f'{db_name} files for uploading to ipfs node')
    if not file_docs:
        return

    ipfs_files = IpfsFiles()

    for doc in file_docs:
        try:
            cid = fm.ipfs_uploading_file(doc[DID], doc[APP_DID], doc[COL_IPFS_FILES_PATH])
            ipfs_files.increase_cid_ref(cid)
            col_filter = {DID: doc[DID], APP_DID: doc[APP_DID], COL_IPFS_FILES_PATH: doc[COL_IPFS_FILES_PATH]}
            cli.update_one_origin(db_name, COL_IPFS_FILES,
                                  col_filter, {'$set': {COL_IPFS_FILES_IPFS_CID: cid}}, is_extra=True)
        except Exception as e:
            logging.error(f'[task_upload_ipfs_files] failed upload file to ipfs with exception: {str(e)}')


# TODO: update this process later, this will be implemented as other design.
# @scheduler.task('interval', id='task_adapt_local_file_to_ipfs', minutes=10)
def task_adapt_local_file_to_ipfs():
    """ Task for keeping sync with ipfs metadata.
    This do not handle the cid of the ipfs server.
    """
    logging.info('[task_adapt_local_file_to_ipfs] enter.')

    if not hive_setting.ENABLE_IPFS:
        logging.info('[task_adapt_local_file_to_ipfs] IPFS not supported, skip.')
        return

    for user in cli.get_all_user_apps():
        try:
            user_did, app_did = user[USER_DID], user[APP_ID]
            logging.info(f'[task_adapt_local_file_to_ipfs] Adapt for user({user_did}), app_did({app_did})')
            name = gene_mongo_db_name(user_did, app_did)
            files_root = get_save_files_path(user_did, app_did)
            if not files_root.exists():
                continue
            adapt_local_files_by_folder(user_did, app_did, name, files_root)
        except Exception as e:
            logging.error(f'[task_adapt_local_file_to_ipfs] Failed to handle user:'
                          f'{str(user)}, {traceback.format_exc()}, skip')

    logging.info('[task_adapt_local_file_to_ipfs] leave.')


def adapt_local_files_by_folder(user_did, app_did, database_name, files_root):
    files = fm.get_files_recursively(files_root)
    col_filter = {DID: user_did, APP_DID: app_did}
    file_docs = cli.find_many_origin(database_name, COL_IPFS_FILES, col_filter,
                                     create_on_absence=False, throw_exception=False)
    ipfs_files = IpfsFiles()

    # handle new and update
    for file in files:
        rel_path = file.relative_to(files_root).as_posix()
        matches = list(filter(lambda d: d[COL_IPFS_FILES_PATH] == rel_path, file_docs))
        if not matches:
            ipfs_files.create_file_metadata(user_did, app_did, rel_path, file)
            continue
        doc = matches[0]
        ipfs_files.update_file_metadata(user_did, app_did, rel_path, file, old_doc=doc)

    # handle delete
    rel_paths = [n.relative_to(files_root).as_posix() for n in files]
    remove_list = [d for d in file_docs if d[COL_IPFS_FILES_PATH] not in rel_paths]
    for d in remove_list:
        ipfs_files.delete_file_metadata(user_did, app_did, d[COL_IPFS_FILES_PATH], d[COL_IPFS_FILES_IPFS_CID])


@scheduler.task('interval', id='task_clean_temp_files', hours=6)
def task_clean_temp_files():
    """ Delete all temporary files created before 12 hours. """
    logging.info('[task_clean_temp_files] enter.')
    temp_path = get_temp_path()
    valid_timestamp = time.time() - 6 * 3600
    files = fm.get_files_recursively(temp_path)
    for f in files:
        if f.stat().st_mtime < valid_timestamp:
            f.unlink()
            logging.info(f'[task_clean_temp_files] Temporary file {f.as_posix()} removed.')
    logging.info('[task_clean_temp_files] leave.')


# Shutdown your cron thread if the web process is stopped
# atexit.register(lambda: scheduler.shutdown(wait=False))

if __name__ == '__main__':
    # task_upload_ipfs_files()
    # task_adapt_local_file_to_ipfs()
    task_clean_temp_files()
